PS C:\Users\Lap1578\Documents\iNextLabs\R&D\whatsapp> python .\app_v4.py

======================================================================
🚀 WhatsApp Voice Agent Server (aiortc + Whisper)
======================================================================
📞 Phone Number: +15551441906
📱 Phone ID: 518638374672395
🏢 WABA ID: 553133154547046
🎵 Audio File: ./sound.mp3 (exists=True)
======================================================================
✅ Ready to receive calls!
======================================================================

 * Serving Flask app 'app_v4'
 * Debug mode: off
2025-10-17 11:41:32,406 - INFO - WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.0.105:5000
2025-10-17 11:41:32,407 - INFO - Press CTRL+C to quit
✅ Webhook verified!
2025-10-17 11:41:38,485 - INFO - 127.0.0.1 - - [17/Oct/2025 11:41:38] "GET /webhook?hub.mode=subscribe&hub.challenge=1158863600&hub.verify_token=iNextLabsCloud HTTP/1.1" 200 -

📩 Webhook received:
{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "id": "553133154547046",
      "changes": [
        {
          "value": {
            "messaging_product": "whatsapp",
            "metadata": {
              "display_phone_number": "15551441906",
              "phone_number_id": "518638374672395"
            },
            "contacts": [
              {
                "profile": {
                  "name": "917358580180"
                },
                "wa_id": "917358580180"
              }
            ],
            "calls": [
              {
                "id": "wacid.HBgMOTE3MzU4NTgwMTgwFQIAEhggQUNEODk3OUQ3NzI4MjZBRTZFNEE2MzU3NDEzNDg4RUUcGAsxNTU1MTQ0MTkwNhUCABUKAA==",
                "from": "917358580180",
                "to": "15551441906",
                "event": "connect",
                "timestamp": "1760681506",
                "direction": "USER_INITIATED",
                "session": {
                  "sdp": "v=0\r\no=- 1760681506762 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\na=group:BUNDLE audio\r\na=msid-semantic: WMS c3867497-e6f7-4408-82b7-80dbd11b94cf\r\na=ice-lite\r\nm=audio 3484 UDP/TLS/RTP/SAVPF 111 126\r\nc=IN IP4 57.144.215.49\r\na=rtcp:9 IN IP4 0.0.0.0\r\na=candidate:3935165743 1 udp 2122260223 57.144.215.49 3484 typ host generation 0 network-cost 50\r\na=candidate:2617197009 1 udp 2122262783 2a03:2880:f36b:131:face:b00c:0:699c 3484 typ host generation 0 network-cost 50\r\na=ice-ufrag:AeinEGDfvqBctbtM\r\na=ice-pwd:F6/jjqL0/8/Dzluc0IoZEQ==\r\na=fingerprint:sha-256 A2:EC:E2:C4:E4:FE:75:63:39:0D:77:45:DF:70:64:BC:F9:96:73:DE:F4:92:E5:78:D0:5B:1F:8F:E7:46:D3:C6\r\na=setup:actpass\r\na=mid:audio\r\na=sendrecv\r\na=msid:c3867497-e6f7-4408-82b7-80dbd11b94cf WhatsAppTrack1\r\na=rtcp-mux\r\na=rtpmap:111 opus/48000/2\r\na=rtcp-fb:111 transport-cc\r\na=fmtp:111 maxaveragebitrate=20000;maxplaybackrate=16000;minptime=20;sprop-maxcapturerate=16000;useinbandfec=1\r\na=rtpmap:126 telephone-event/8000\r\na=maxptime:20\r\na=ptime:20\r\na=ssrc:1047224411 cname:WhatsAppAudioStream1\r\n",
                  "sdp_type": "offer"
                }
              }
            ]
          },
          "field": "calls"
        }
      ]
    }
  ]
}
2025-10-17 11:41:48,749 - INFO - 127.0.0.1 - - [17/Oct/2025 11:41:48] "POST /webhook HTTP/1.1" 200 -

============================================================
🔔 INCOMING CALL!
   From: 917358580180 (917358580180)
   To: 15551441906
   Call ID: wacid.HBgMOTE3MzU4NTgwMTgwFQIAEhggQUNEODk3OUQ3NzI4MjZBRTZFNEE2MzU3NDEzNDg4RUUcGAsxNTU1MTQ0MTkwNhUCABUKAA==
============================================================
🚀 Setting up WebRTC connection...
✅ Loaded audio: 153392 samples, 3.20 seconds
✅ Remote description set
🎤 Receiving audio track from caller
2025-10-17 11:41:52,488 - INFO - Connection(0) Could not bind to 169.254.190.94 - [WinError 10049] The requested address is not valid in its context
2025-10-17 11:41:52,489 - INFO - Connection(0) Could not bind to 169.254.248.44 - [WinError 10049] The requested address is not valid in its context
2025-10-17 11:41:52,490 - INFO - Connection(0) Could not bind to 169.254.48.89 - [WinError 10049] The requested address is not valid in its context
2025-10-17 11:41:52,490 - INFO - Connection(0) Could not bind to 169.254.180.237 - [WinError 10049] The requested address is not valid in its context
✅ Local description set
✅ ICE gathering complete
✅ SDP answer sanitized v=0
o=- 3969670312 3969670312 IN IP4 0.0.0.0
s=-
t=0 0
a=group:BUNDLE audio
a=msid-semantic:WMS *
m=audio 51420 UDP/TLS/RTP/SAVPF 111
c=IN IP4 192.168.0.105
a=sendrecv
a=mid:audio
a=msid:af87c5bc-d802-4572-9423-90b4f778b127 780da3b0-c136-411a-a62a-4be38cf71504
a=rtcp:9 IN IP4 0.0.0.0
a=rtcp-mux
a=ssrc:871350736 cname:571588de-f844-4e01-8bef-e64c539ea7fa
a=rtpmap:111 opus/48000/2
a=candidate:81e4055b388bb46e1abb9c8a0f6f87ce 1 udp 2130706431 192.168.0.105 51420 typ host
a=candidate:ba07806f1ab850f35970a5643d51e347 1 udp 1694498815 49.204.143.120 7371 typ srflx raddr 192.168.0.105 rport 51420     
a=end-of-candidates
a=ice-ufrag:TJvS
a=ice-pwd:KTrAGZGgLLknVI4GLfjXFp
a=fingerprint:SHA-256 5C:8E:0A:DD:2B:2B:5E:AC:6C:13:71:2E:C8:E4:0A:B5:F5:2C:7D:D7:38:97:0A:B2:4F:F5:14:8E:4A:10:22:CE
a=setup:active

✅ Call pre-accepted by WhatsApp
✅ Call accepted by WhatsApp
🔊 Streaming started
2025-10-17 11:41:53,674 - INFO - Connection(0) Check CandidatePair(('192.168.0.105', 51420) -> ('57.144.215.49', 3484)) State.FROZEN -> State.WAITING

📩 Webhook received:
{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "id": "553133154547046",
      "changes": [
        {
          "value": {
            "messaging_product": "whatsapp",
            "metadata": {
              "display_phone_number": "15551441906",
              "phone_number_id": "518638374672395"
            },
            "contacts": [
              {
                "profile": {
                  "name": "917358580180"
                },
                "wa_id": "917358580180"
              }
            ],
            "calls": [
              {
                "id": "wacid.HBgMOTE3MzU4NTgwMTgwFQIAEhggQUNEODk3OUQ3NzI4MjZBRTZFNEE2MzU3NDEzNDg4RUUcGAsxNTU1MTQ0MTkwNhUCABUKAA==",
                "from": "917358580180",
                "to": "15551441906",
                "event": "terminate",
                "timestamp": "1760681533",
                "direction": "USER_INITIATED",
                "start_time": "1760681513",
                "end_time": "1760681533",
                "duration": 20,
                "status": "FAILED",
                "errors": [
                  {
                    "code": 138021,
                    "title": "WhatsApp client terminated the call due to not receiving any media for a long time. Please try again",
                    "message": "WhatsApp client terminated the call due to not receiving any media for a long time. Please try again",
                    "error_data": {
                      "details": "WhatsApp client terminated the call due to not receiving any media for a long time."
                    }
                  }
                ]
              }
            ],
            "errors": [
              {
                "code": 138021,
                "title": "WhatsApp client terminated the call due to not receiving any media for a long time. Please try again",
                "message": "WhatsApp client terminated the call due to not receiving any media for a long time. Please try again",
                "error_data": {
                  "details": "WhatsApp client terminated the call due to not receiving any media for a long time."
                }
              }
            ]
          },
          "field": "calls"
        }
      ]
    }
  ]
}
2025-10-17 11:42:15,463 - INFO - 127.0.0.1 - - [17/Oct/2025 11:42:15] "POST /webhook HTTP/1.1" 200 -

📞 Call ended: wacid.HBgMOTE3MzU4NTgwMTgwFQIAEhggQUNEODk3OUQ3NzI4MjZBRTZFNEE2MzU3NDEzNDg4RUUcGAsxNTU1MTQ0MTkwNhUCABUKAA==       
   Status: FAILED, Duration: 20s
Error closing PC: Event loop is closed
✅ Call wacid.HBgMOTE3MzU4NTgwMTgwFQIAEhggQUNEODk3OUQ3NzI4MjZBRTZFNEE2MzU3NDEzNDg4RUUcGAsxNTU1MTQ0MTkwNhUCABUKAA== cleaned up   
🧊 ICE state: closed
🔗 Peer state: closed