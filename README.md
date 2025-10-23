"# ✅ Webhook Verification and Call Log

**Date:** 2025-10-23  
**Time:** 15:33:16 – 15:34:06  
**System:** iNextLabs Cloud  
**Status:** ✅ Webhook verified | 📞 Call attempted | ❌ Connection failed after 20 seconds  

---

## 🧩 Webhook Verification

```log
✅ Webhook verified!
2025-10-23 15:33:16,804 - INFO - 127.0.0.1 - - [23/Oct/2025 15:33:16]  
"GET /webhook?hub.mode=subscribe&hub.challenge=683904941&hub.verify_token=iNextLabsCloud HTTP/1.1" 200 

📬 Incoming Webhook Events
2025-10-23 15:33:39,502 - INFO - 127.0.0.1 - - [23/Oct/2025 15:33:39]  
"POST /webhook HTTP/1.1" 200 -

🔔 Incoming Call Event

Caller: +91 73585 80180
Handler: handle_incoming_call

🚀 handle_incoming_call started  
2025-10-23 15:33:42,128 - INFO - 127.0.0.1 - - [23/Oct/2025 15:33:42]  
"GET /api/getIceToken HTTP/1.1" 404 -

🎵 Audio Setup
✅ Loaded audio: 153392 samples, 3.20 seconds  
[PC] ✅ Outbound audio track attached  
[SDP] ✅ Remote description set

⚠️ Connection Binding Errors
<details> <summary>View Error Logs</summary>
2025-10-23 15:33:43,359 - INFO - Connection(0) Could not bind to 169.254.190.94 - [WinError 10049] The requested address is not valid in its context  
2025-10-23 15:33:43,359 - INFO - Connection(0) Could not bind to 169.254.248.44 - [WinError 10049] The requested address is not valid in its context  
2025-10-23 15:33:43,360 - INFO - Connection(0) Could not bind to 169.254.48.89 - [WinError 10049] The requested address is not valid in its context  
2025-10-23 15:33:43,360 - INFO - Connection(0) Could not bind to 169.254.180.237 - [WinError 10049] The requested address is not valid in its context

</details>
📡 SDP (Session Description Protocol)
[SDP] ✅ Local description set  
[SDP] ✅ ICE gathering complete  
[SDP] ✅ Answer sanitized  
[SDP] Answer summary: 906 chars, candidates: 2

<details> <summary>View Full SDP Answer Sent to WhatsApp</summary>
v=0
o=- 3970202623 3970202623 IN IP4 0.0.0.0
s=-
t=0 0
a=group:BUNDLE audio
a=msid-semantic:WMS *
a=ice-lite
m=audio 64355 UDP/TLS/RTP/SAVPF 111
c=IN IP4 192.168.68.117
a=sendrecv
a=mid:audio
a=msid:79084c48-12b6-4ac9-ba8c-74e7657fb933 1cb5508b-87f5-435a-9455-0e11a31ad426
a=rtcp:9 IN IP4 0.0.0.0
a=rtcp-mux
a=ssrc:1273149022 cname:e4a78709-1c74-48fc-a1ed-0bd714275e80
a=rtpmap:111 opus/48000/2
a=rtcp-fb:111 transport-cc
a=fmtp:111 minptime=10;useinbandfec=1
a=candidate:472ab4c4700d37aa155912b8fdf7f3b6 1 udp 2130706431 192.168.68.117 64355 typ host
a=candidate:f8dfdc7b7d952fe51501544018317db0 1 udp 1694498815 123.176.34.233 64355 typ srflx raddr 192.168.68.117 rport 64355
a=end-of-candidates
a=ice-ufrag:uZOn
a=ice-pwd:q77ty25YUSyvY2qnZjT1R8
a=fingerprint:SHA-256 AA:73:A4:B9:B9:64:75:53:3C:37:A5:7C:54:C1:E0:DC:E2:CA:C5:A1:E0:D9:7F:68:9B:E5:93:68:8F:B4:1F:9A
a=setup:active

</details>
🔄 ICE and DTLS Handshake
✅ pre-accept sent  
✅ accept sent  
⏳ Waiting for DTLS handshake...  
[PC] ICE state changed: checking  
[PC] Connection state changed: connecting  
[PC] ICE state changed: completed  
[PC] Connection state changed: connected  
✅ DTLS complete

🎙️ Media Transmission
[TRACK] ✅ Track.start() called - media transmission ENABLED  
[CALL] ✅ Media transmission started  
[DIAG] Starting diagnostics loop...

❌ Connection Closed
[PC] ICE state changed: closed  
[PC] Connection state changed: closed  
2025-10-23 15:34:06,372 - INFO - 127.0.0.1 - - [23/Oct/2025 15:34:06] "POST /webhook HTTP/1.1" 200 -

📞 Call Summary
Parameter	Value
Status	❌ FAILED
Duration	20 seconds
Error	Task attached to a different asyncio loop
Cleanup	✅ Completed
Error closing PC: Task <Task pending name='Task-36' coro=<handle_call_event()> ...>  
got Future <Future pending> attached to a different loop  
✅ Call cleaned up