// Backend (FastAPI). Chrome/desktop can use localhost.
// Android emulator: http://10.0.2.2:8000 | Physical phone: http://<laptop-LAN-IP>:8000
const String apiBase = 'http://localhost:8000';

// go2rtc runs on the Raspberry Pi. Put the Pi's WiFi IP here once the hardware is back.
const String go2rtcBase = 'http://192.168.1.50:1984';
const String cameraStream = 'hikvision-01';