from flask import Flask, request, jsonify
import asyncio, json, os, logging, re, secrets
from threading import Thread
import requests
import numpy as np
import librosa
import whisper
from fractions import Fraction
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer, MediaStreamTrack
from av import AudioFrame

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────
WABA_ID = "WABA"
PHONE_ID = "PHONE_ID"
PHONE_NUMBER = "NUMBER"
ACCESS_TOKEN = "ACCESSTOKEN"  # <<<<<< put your token here

GRAPH_API_BASE = "https://graph.facebook.com/v14.0"
CALLS_ENDPOINT = f"{GRAPH_API_BASE}/{PHONE_ID}/calls"

AUDIO_FILE = "./sound.mp3"   # file we will stream to the user (looped)
STUN_SERVERS = ["stun:stun.l.google.com:19302"]

# ──────────────────────────────────────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("wa-voice")

app = Flask(__name__)
active_calls = {}  # call_id -> dict(pc, track, stt, ...)

# ──────────────────────────────────────────────────────────────────────────────
# AUDIO OUT: simple looped PCM16 @ 48kHz, 20ms frames
# ──────────────────────────────────────────────────────────────────────────────
class LoopingAudioTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self, path: str, sample_rate: int = 48000):
        super().__init__()
        self.sample_rate = sample_rate
        self.samples_per_frame = 960  # 20 ms @ 48k
        self._enabled = False
        self._cursor = 0
        # load mono file, resample to 48k, int16
        y, _ = librosa.load(path, sr=self.sample_rate, mono=True)
        y = np.clip(y, -1.0, 1.0)
        self._audio = (y * 32767.0).astype(np.int16)
        dur = len(self._audio) / self.sample_rate
        print(f"✅ Loaded audio: {len(self._audio)} samples, {dur:.2f} seconds")

    def start(self):
        self._enabled = True

    async def recv(self):
        await asyncio.sleep(0.02)
        if not self._enabled:
            chunk = np.zeros(self.samples_per_frame, dtype=np.int16)
            pts = 0
        else:
            start = self._cursor
            end = start + self.samples_per_frame
            if end <= len(self._audio):
                chunk = self._audio[start:end]
                self._cursor = end
            else:
                first = self._audio[start:]
                remain = end - len(self._audio)
                second = self._audio[:remain]
                chunk = np.concatenate([first, second])
                self._cursor = remain
            pts = start
        frame = AudioFrame.from_ndarray(chunk.reshape(1, -1), format="s16", layout="mono")
        frame.sample_rate = self.sample_rate
        frame.time_base = Fraction(1, self.sample_rate)
        frame.pts = int(pts)
        return frame

# ──────────────────────────────────────────────────────────────────────────────
# STT: Whisper translate-to-English (rolling)
# ──────────────────────────────────────────────────────────────────────────────
def resample_48k_to_16k_mono(pcm16_48k_mono: np.ndarray) -> np.ndarray:
    if pcm16_48k_mono.size == 0:
        return pcm16_48k_mono
    x = pcm16_48k_mono.astype(np.float32) / 32768.0
    y = librosa.resample(x, orig_sr=48000, target_sr=16000, res_type="kaiser_fast")
    y = np.clip(y, -1.0, 1.0)
    return (y * 32767.0).astype(np.int16)

class WhisperTranslateWorker:
    """
    Collects 16kHz mono PCM16 and periodically runs Whisper with task='translate'.
    """
    def __init__(self, model_name="base", target_sr=16000, window_sec=7.0, hop_sec=2.0):
        self.model = whisper.load_model(model_name)
        self.target_sr = target_sr
        self.window_sec = window_sec
        self.hop_sec = hop_sec
        self.buffer = np.empty(0, dtype=np.int16)
        self._running = True

    def add_pcm16(self, pcm16_16k: np.ndarray):
        if pcm16_16k.size:
            if pcm16_16k.dtype != np.int16:
                pcm16_16k = pcm16_16k.astype(np.int16)
            self.buffer = np.concatenate([self.buffer, pcm16_16k])

    def stop(self):
        self._running = False

    async def loop(self, call_id: str):
        while self._running:
            await asyncio.sleep(self.hop_sec)
            if self.buffer.size < int(1.0 * self.target_sr):
                continue
            buf = self.buffer[-int(self.window_sec * self.target_sr):]
            audio_f32 = buf.astype(np.float32) / 32768.0
            try:
                result = self.model.transcribe(audio_f32, task="translate", language=None, fp16=False)
                text = (result.get("text") or "").strip()
                if text:
                    print(f"[STT:{call_id}] {text}")
            except Exception as e:
                print(f"[STT:{call_id}] whisper error: {e}")

# ──────────────────────────────────────────────────────────────────────────────
# SDP helpers: ONLY the safe tweaks
# ──────────────────────────────────────────────────────────────────────────────
def sanitize_sdp_for_whatsapp(sdp: str) -> str:
    """
    WhatsApp is picky:
      - fingerprint algo MUST be uppercased: a=fingerprint:SHA-256
      - remove any sha-384/sha-512 lines
      - CRLF line endings
    Do NOT touch the actual fingerprint value or other DTLS/ICE lines.
    """
    s = sdp
    s = s.replace("\r\n", "\n").replace("\n", "\r\n")
    s = re.sub(r"^a=fingerprint:sha-256", "a=fingerprint:SHA-256", s, flags=re.MULTILINE)
    s = re.sub(r"^a=fingerprint:sha-384.*\r?\n", "", s, flags=re.MULTILINE)
    s = re.sub(r"^a=fingerprint:sha-512.*\r?\n", "", s, flags=re.MULTILINE)
    if not s.endswith("\r\n"):
        s += "\r\n"
    return s

async def wait_for_ice_gathering_complete(pc: RTCPeerConnection, timeout=3.5):
    if pc.iceGatheringState == "complete":
        return
    loop = asyncio.get_event_loop()
    fut = loop.create_future()

    @pc.on("icegatheringstatechange")
    def _on_gather():
        if pc.iceGatheringState == "complete" and not fut.done():
            fut.set_result(True)
    try:
        await asyncio.wait_for(fut, timeout)
    except asyncio.TimeoutError:
        pass

# ──────────────────────────────────────────────────────────────────────────────
# Graph API: pre-accept / accept
# ──────────────────────────────────────────────────────────────────────────────
def _auth_headers():
    return {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}

async def send_pre_accept(call_id: str, sdp_answer: str) -> bool:
    payload = {
        "messaging_product": "whatsapp",
        "call_id": call_id,
        "action": "pre_accept",
        "session": {"sdp_type": "answer", "sdp": sdp_answer},
    }
    try:
        r = requests.post(CALLS_ENDPOINT, json=payload, headers=_auth_headers(), timeout=10)
        if r.status_code == 200:
            print("✅ Call pre-accepted by WhatsApp")
            return True
        print(f"❌ pre_accept {r.status_code} {r.text}")
        return False
    except Exception as e:
        print(f"❌ pre_accept exception: {e}")
        return False

async def send_accept(call_id: str, sdp_answer: str) -> bool:
    payload = {
        "messaging_product": "whatsapp",
        "call_id": call_id,
        "action": "accept",
        "session": {"sdp_type": "answer", "sdp": sdp_answer},
    }
    try:
        r = requests.post(CALLS_ENDPOINT, json=payload, headers=_auth_headers(), timeout=10)
        if r.status_code == 200:
            print("✅ Call accepted by WhatsApp")
            return True
        print(f"❌ accept {r.status_code} {r.text}")
        return False
    except Exception as e:
        print(f"❌ accept exception: {e}")
        return False

# ──────────────────────────────────────────────────────────────────────────────
# Diagnostics
# ──────────────────────────────────────────────────────────────────────────────
async def log_diagnostics(pc: RTCPeerConnection, call_id: str):
    last = 0
    while pc.connectionState not in ("failed", "closed"):
        stats = await pc.getStats()
        outs = [s for s in stats.values()
                if getattr(s, "type", "") == "outbound-rtp"
                and getattr(s, "kind", "") == "audio"]
        if outs:
            s = outs[0]
            print(f"[diag:{call_id}] bytesSent={s.bytesSent} packetsSent={s.packetsSent}")
            if s.bytesSent == last:
                print(f"[diag:{call_id}] WARNING: no growth — check firewall / DTLS / track")
            last = s.bytesSent

        pairs = [s for s in stats.values()
                 if getattr(s, "type", "") == "candidate-pair"
                 and getattr(s, "state", "") == "succeeded"
                 and getattr(s, "nominated", False)]
        if pairs:
            cp = pairs[0]
            lc = stats.get(getattr(cp, "localCandidateId", ""))
            rc = stats.get(getattr(cp, "remoteCandidateId", ""))
            if lc and rc:
                print(f"[diag:{call_id}] selected {lc.address}:{lc.port} -> {rc.address}:{rc.port} ({lc.protocol})")
        await asyncio.sleep(1.0)

# ──────────────────────────────────────────────────────────────────────────────
# Call handling
# ──────────────────────────────────────────────────────────────────────────────
async def handle_incoming_call(call_id: str, sdp_offer: str, caller_number: str, caller_name: str):
    print("🚀 Setting up WebRTC connection...")

    if not os.path.exists(AUDIO_FILE):
        print(f"❌ Audio file not found: {AUDIO_FILE}")
        return

    pc = RTCPeerConnection(RTCConfiguration(iceServers=[RTCIceServer(urls=STUN_SERVERS)]))

    @pc.on("connectionstatechange")
    async def _on_conn():
        print(f"🔗 Peer state: {pc.connectionState}")

    @pc.on("iceconnectionstatechange")
    async def _on_ice():
        print(f"🧊 ICE state: {pc.iceConnectionState}")

    # OUTBOUND: attach our looped audio BEFORE setting the remote description
    out_track = LoopingAudioTrack(AUDIO_FILE)
    pc.addTrack(out_track)  # keep it simple; binds the m=audio correctly

    # INBOUND: receive caller audio and feed Whisper
    stt_worker = WhisperTranslateWorker(model_name="base")

    @pc.on("track")
    async def _on_track(in_track):
        print(f"🎤 Receiving {in_track.kind} track from caller")
        if in_track.kind != "audio":
            return

        async def reader():
            while True:
                try:
                    frame = await in_track.recv()
                except Exception:
                    break
                pcm = frame.to_ndarray(format="s16")  # (C, S) or (S,)
                if pcm.ndim == 2 and pcm.shape[0] > 1:
                    pcm = pcm.mean(axis=0).astype(np.int16)
                elif pcm.ndim == 2:
                    pcm = pcm[0]
                else:
                    pcm = pcm.astype(np.int16)
                pcm16k = resample_48k_to_16k_mono(pcm)
                stt_worker.add_pcm16(pcm16k)

        asyncio.create_task(reader())
        asyncio.create_task(stt_worker.loop(call_id))

    # SDP: set offer, create/set answer, sanitize, send to WhatsApp
    try:
        await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp_offer, type="offer"))
        print("✅ Remote description set")

        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        print("✅ Local description set")

        await wait_for_ice_gathering_complete(pc, timeout=3.5)
        print("✅ ICE gathering complete")

        sdp_answer = sanitize_sdp_for_whatsapp(pc.localDescription.sdp)
        print("✅ SDP answer sanitized",sdp_answer)
        # If you can't perfectly control media start timing, you can skip pre_accept and just accept.
        if not await send_pre_accept(call_id, sdp_answer):
            await pc.close(); return
        if not await send_accept(call_id, sdp_answer):
            await pc.close(); return

        # Start sending media only after accept
        out_track.start()
        print("🔊 Streaming started")

        asyncio.create_task(log_diagnostics(pc, call_id))

        active_calls[call_id] = {
            "pc": pc,
            "track": out_track,
            "stt": stt_worker,
            "caller_number": caller_number,
            "caller_name": caller_name,
        }

    except Exception as e:
        print(f"❌ Error in handle_incoming_call: {e}")
        import traceback; traceback.print_exc()
        await pc.close()

async def cleanup_call(call_id: str):
    data = active_calls.pop(call_id, None)
    if not data:
        return
    try:
        stt = data.get("stt")
        if stt:
            stt.stop()
        pc = data.get("pc")
        if pc:
            await pc.close()
    except Exception as e:
        print(f"Error closing PC: {e}")
    print(f"✅ Call {call_id} cleaned up")

# ──────────────────────────────────────────────────────────────────────────────
# Webhook
# ──────────────────────────────────────────────────────────────────────────────
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        verify_token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if verify_token == "iNextLabsCloud":
            print("✅ Webhook verified!")
            return challenge, 200
        return "Invalid verification token", 403

    # POST
    data = request.json
    print("\n📩 Webhook received:")
    print(json.dumps(data, indent=2))

    if data.get("object") == "whatsapp_business_account":
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") == "calls":
                    Thread(target=handle_call_event_sync, args=(change["value"],), daemon=True).start()
    return jsonify({"status": "ok"}), 200

def handle_call_event_sync(value):
    asyncio.run(handle_call_event(value))

async def handle_call_event(value):
    calls = value.get("calls", [])
    for call in calls:
        event = call.get("event")
        call_id = call.get("id")

        if event == "connect":
            caller_number = call.get("from")
            business_number = call.get("to")
            sdp_offer = (call.get("session") or {}).get("sdp", "")

            contacts = value.get("contacts", [])
            caller_name = contacts[0].get("profile", {}).get("name", "Unknown") if contacts else "Unknown"

            print("\n" + "="*60)
            print("🔔 INCOMING CALL!")
            print(f"   From: {caller_name} ({caller_number})")
            print(f"   To: {business_number}")
            print(f"   Call ID: {call_id}")
            print("="*60)

            await handle_incoming_call(call_id, sdp_offer, caller_number, caller_name)

        elif event == "terminate":
            status = call.get("status")
            duration = call.get("duration", 0)
            print(f"\n📞 Call ended: {call_id}")
            print(f"   Status: {status}, Duration: {duration}s")
            await cleanup_call(call_id)

# ──────────────────────────────────────────────────────────────────────────────
# Utility
# ──────────────────────────────────────────────────────────────────────────────
@app.route("/test", methods=["GET"])
def test():
    return jsonify({
        "status": "ok",
        "phone_number": PHONE_NUMBER,
        "phone_id": PHONE_ID,
        "active_calls": list(active_calls.keys()),
        "audio_file": AUDIO_FILE,
        "audio_exists": os.path.exists(AUDIO_FILE),
    })

# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 WhatsApp Voice Agent Server (aiortc + Whisper)")
    print("="*70)
    print(f"📞 Phone Number: +{PHONE_NUMBER}")
    print(f"📱 Phone ID: {PHONE_ID}")
    print(f"🏢 WABA ID: {WABA_ID}")
    print(f"🎵 Audio File: {AUDIO_FILE} (exists={os.path.exists(AUDIO_FILE)})")
    print("="*70)
    print("✅ Ready to receive calls!")
    print("="*70 + "\n")

    if not os.path.exists(AUDIO_FILE):
        print("⚠️  WARNING: './sound.mp3' not found — no audio will be sent.\n")

    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
