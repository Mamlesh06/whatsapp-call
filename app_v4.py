from flask import Flask, request, jsonify
import asyncio, json, os, logging, re
from threading import Thread
import requests
import numpy as np
import librosa
import whisper
from fractions import Fraction
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer, MediaStreamTrack
from av import AudioFrame

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("wa-voice")
app = Flask(__name__)
active_calls = {}

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────
WABA_ID = "553133154547046"
PHONE_ID = "518638374672395"
PHONE_NUMBER = "15551441906"
ACCESS_TOKEN = "EAAhEqQy6qI0BO7QZC8qNAu1zUmyDu7aRZCceSngf7i9q6HAfXoDdN3yhqSjhWGRtMhtT4W7nKRwFURsbgzdaBwiu5ukeepfSh9MfZCP8APfhWZBNzVVYg9ZBJhGkElCC8DB6Q8l0d6ZCSjAuhqadkuwwMc38Q8xspa1ZCvZCk0vAvQGQh1RXDUVtVZBnMCaCGCodKDgZDZD"
GRAPH_API_BASE = "https://graph.facebook.com/v14.0"
CALLS_ENDPOINT = f"{GRAPH_API_BASE}/{PHONE_ID}/calls"
AUDIO_FILE = "./sound.mp3"
STUN_SERVERS = ["stun:stun.l.google.com:19302"]

# ──────────────────────────────────────────────────────────────────────────────
# DEBUG AUDIO TRACK WITH LOGGING
# ──────────────────────────────────────────────────────────────────────────────
class LoopingAudioTrack(MediaStreamTrack):
    kind = "audio"
    def __init__(self, path: str, sample_rate: int = 48000):
        super().__init__()
        self.sample_rate = sample_rate
        self.samples_per_frame = 960
        self._enabled = False
        self._cursor = 0
        self._frame_count = 0
        self._bytes_sent = 0
        
        y, _ = librosa.load(path, sr=self.sample_rate, mono=True)
        y = np.clip(y, -1.0, 1.0)
        self._audio = (y * 32767.0).astype(np.int16)
        dur = len(self._audio) / self.sample_rate
        print(f"✅ Loaded audio: {len(self._audio)} samples, {dur:.2f} seconds")
    
    def start(self):
        self._enabled = True
        print("[TRACK] ✅ Track.start() called - media transmission ENABLED")
    
    async def recv(self):
        self._frame_count += 1
        self._bytes_sent += self.samples_per_frame * 2  # 2 bytes per sample
        
        # Log every 25 frames (~0.5 sec at 50 FPS)
        if self._frame_count % 25 == 1:
            print(f"[TRACK] Frame #{self._frame_count}, enabled={self._enabled}, bytes_sent={self._bytes_sent}, cursor={self._cursor}")
        
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
# SIMPLIFIED SDP - NO OPUS PARAM MODIFICATION FOR NOW
# ──────────────────────────────────────────────────────────────────────────────
def sanitize_sdp_for_whatsapp(sdp: str) -> str:
    """Add missing Meta-required attributes and sanitize"""
    lines = sdp.split("\r\n")
    new_lines = []
    
    # Normalize line endings first
    sdp = sdp.replace("\r\n", "\n").replace("\n", "\r\n")
    lines = sdp.split("\r\n")
    new_lines = []
    
    in_audio_section = False
    added_ice_lite = False
    added_rtcp_fb = False
    added_fmtp = False
    
    for i, line in enumerate(lines):
        # Add a=ice-lite right after session attributes, before m=audio
        if line.startswith("m=audio") and not added_ice_lite:
            new_lines.append("a=ice-lite")
            added_ice_lite = True
            in_audio_section = True
        
        # Add codec parameters after rtpmap line
        if in_audio_section and "a=rtpmap:111 opus/48000/2" in line:
            new_lines.append(line)
            # Add rtcp-fb if not already there
            if not added_rtcp_fb:
                new_lines.append("a=rtcp-fb:111 transport-cc")
                added_rtcp_fb = True
            # Add fmtp if not already there
            if not added_fmtp:
                new_lines.append("a=fmtp:111 minptime=10;useinbandfec=1")
                added_fmtp = True
            continue
        
        # Fix fingerprint to uppercase SHA-256
        if "a=fingerprint:sha-256" in line.lower():
            line = re.sub(r"a=fingerprint:sha-256", "a=fingerprint:SHA-256", line, flags=re.IGNORECASE)
        
        # Remove sha-384 and sha-512 fingerprints
        if "a=fingerprint:sha-384" in line.lower() or "a=fingerprint:sha-512" in line.lower():
            continue
        
        new_lines.append(line)
    
    result = "\r\n".join(new_lines)
    if not result.endswith("\r\n"):
        result += "\r\n"
    
    return result

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

async def wait_for_dtls_connected(pc: RTCPeerConnection, timeout=10.0):
    print("⏳ Waiting for DTLS handshake...")
    start_time = asyncio.get_event_loop().time()
    while True:
        if pc.connectionState == "connected":
            print("✅ DTLS complete")
            return True
        if pc.connectionState == "failed":
            print("❌ DTLS failed")
            return False
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > timeout:
            print(f"⚠️ DTLS timeout ({timeout}s)")
            return False
        await asyncio.sleep(0.1)

# ──────────────────────────────────────────────────────────────────────────────
# GRAPH API
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
            print("✅ pre-accept sent")
            return True
        print(f"❌ pre-accept failed: {r.status_code}")
        return False
    except Exception as e:
        print(f"❌ pre-accept error: {e}")
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
            print("✅ accept sent")
            return True
        print(f"❌ accept failed: {r.status_code}")
        return False
    except Exception as e:
        print(f"❌ accept error: {e}")
        return False

# ──────────────────────────────────────────────────────────────────────────────
# DIAGNOSTICS WITH DETAILED LOGGING
# ──────────────────────────────────────────────────────────────────────────────
async def log_diagnostics(pc: RTCPeerConnection, call_id: str, out_track):
    print("[DIAG] Starting diagnostics loop...")
    last_bytes = 0
    check_count = 0
    
    while pc.connectionState not in ("failed", "closed"):
        check_count += 1
        try:
            stats = await pc.getStats()
            
            # Check outbound RTP
            outs = [s for s in stats.values()
                    if getattr(s, "type", "") == "outbound-rtp"
                    and getattr(s, "kind", "") == "audio"]
            
            if outs:
                s = outs[0]
                bytes_sent = getattr(s, "bytesSent", 0)
                packets_sent = getattr(s, "packetsSent", 0)
                print(f"[DIAG #{check_count}] bytesSent={bytes_sent} packetsSent={packets_sent} track.bytes={out_track._bytes_sent}")
                
                if bytes_sent == last_bytes:
                    print(f"[DIAG #{check_count}] ⚠️ WARNING: No RTP packets sent!")
                last_bytes = bytes_sent
            else:
                print(f"[DIAG #{check_count}] ❌ No outbound-rtp stats found!")
            
            # Check ICE
            pairs = [s for s in stats.values()
                     if getattr(s, "type", "") == "candidate-pair"
                     and getattr(s, "state", "") == "succeeded"
                     and getattr(s, "nominated", False)]
            if pairs:
                cp = pairs[0]
                print(f"[DIAG #{check_count}] ICE pair active: {getattr(cp, 'localCandidateId', 'N/A')} -> {getattr(cp, 'remoteCandidateId', 'N/A')}")
        
        except Exception as e:
            print(f"[DIAG #{check_count}] Error getting stats: {e}")
        
        await asyncio.sleep(1.0)
    
    print(f"[DIAG] Diagnostics ended. Connection state: {pc.connectionState}")

# ──────────────────────────────────────────────────────────────────────────────
# CALL HANDLING
# ──────────────────────────────────────────────────────────────────────────────
async def handle_incoming_call(call_id: str, sdp_offer: str, caller_number: str, caller_name: str):
    print("🚀 handle_incoming_call started")
    
    if not os.path.exists(AUDIO_FILE):
        print(f"❌ Audio file not found: {AUDIO_FILE}")
        return
    
    pc = RTCPeerConnection(RTCConfiguration(iceServers=[RTCIceServer(urls=STUN_SERVERS)]))
    
    @pc.on("connectionstatechange")
    async def _on_conn():
        print(f"[PC] Connection state changed: {pc.connectionState}")
    
    @pc.on("iceconnectionstatechange")
    async def _on_ice():
        print(f"[PC] ICE state changed: {pc.iceConnectionState}")
    
    # Attach outbound audio
    out_track = LoopingAudioTrack(AUDIO_FILE)
    pc.addTrack(out_track)
    print("[PC] ✅ Outbound audio track attached")
    
    # Attach inbound audio handler
    @pc.on("track")
    async def _on_track(in_track):
        print(f"[PC] 📥 Inbound track received: {in_track.kind}")
        if in_track.kind != "audio":
            return
        async def reader():
            frame_count = 0
            while True:
                try:
                    frame = await in_track.recv()
                    frame_count += 1
                    if frame_count % 50 == 1:
                        print(f"[INBOUND] Received frame #{frame_count}")
                except Exception as e:
                    print(f"[INBOUND] Reader stopped: {e}")
                    break
        asyncio.create_task(reader())
    
    # SDP negotiation
    try:
        await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp_offer, type="offer"))
        print("[SDP] ✅ Remote description set")
        
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        print("[SDP] ✅ Local description set")
        
        await wait_for_ice_gathering_complete(pc, timeout=3.5)
        print("[SDP] ✅ ICE gathering complete")
        
        sdp_answer = sanitize_sdp_for_whatsapp(pc.localDescription.sdp)
        print("[SDP] ✅ Answer sanitized")
        print(f"[SDP] Answer summary: {len(sdp_answer)} chars, candidates: {sdp_answer.count('a=candidate')}")
        
        # Print the final SDP being sent to WhatsApp
        print("\n" + "="*80)
        print("📤 FINAL SDP ANSWER BEING SENT TO WHATSAPP:")
        print("="*80)
        print(sdp_answer)
        print("="*80 + "\n")
        
        # Send accept
        if not await send_pre_accept(call_id, sdp_answer):
            await pc.close()
            return
        
        if not await send_accept(call_id, sdp_answer):
            await pc.close()
            return
        
        print("[CALL] Waiting for DTLS...")
        if not await wait_for_dtls_connected(pc, timeout=10.0):
            print("[CALL] ⚠️ DTLS handshake timeout")
        
        print("[CALL] Starting media transmission...")
        out_track.start()
        print("[CALL] ✅ Media transmission started")
        
        # Start diagnostics
        asyncio.create_task(log_diagnostics(pc, call_id, out_track))
        
        active_calls[call_id] = {
            "pc": pc,
            "track": out_track,
            "caller_number": caller_number,
            "caller_name": caller_name,
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        await pc.close()

async def cleanup_call(call_id: str):
    data = active_calls.pop(call_id, None)
    if not data:
        return
    try:
        pc = data.get("pc")
        if pc:
            await pc.close()
    except Exception as e:
        print(f"Error closing PC: {e}")
    print(f"✅ Call cleaned up")

# ──────────────────────────────────────────────────────────────────────────────
# WEBHOOK
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
    
    data = request.json
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
            sdp_offer = (call.get("session") or {}).get("sdp", "")
            contacts = value.get("contacts", [])
            caller_name = contacts[0].get("profile", {}).get("name", "Unknown") if contacts else "Unknown"
            print(f"\n🔔 INCOMING CALL from {caller_name}")
            await handle_incoming_call(call_id, sdp_offer, caller_number, caller_name)
        elif event == "terminate":
            status = call.get("status")
            duration = call.get("duration", 0)
            print(f"\n📞 Call ended: {status}, duration: {duration}s")
            await cleanup_call(call_id)

@app.route("/test", methods=["GET"])
def test():
    return jsonify({"status": "ok", "phone_number": PHONE_NUMBER, "active_calls": list(active_calls.keys())})

# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 WhatsApp Voice Agent (DEBUG MODE)")
    print("="*70)
    print(f"📞 Phone: +{PHONE_NUMBER}")
    print(f"📁 Audio: {AUDIO_FILE} (exists={os.path.exists(AUDIO_FILE)})")
    print("="*70 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)