"""
Raspberry Pi Kamera Stream Server

Bu dosya RASPBERRY PI üzerinde çalıştırılır!
PC'de değil, RPi'de çalıştırmanız gerekiyor.

Amaç:
    RPi kamerasından görüntü alıp, HTTP üzerinden PC'ye stream etmek.
    PC tarafında capture.py bu stream'i alır ve işler.

Gereksinimler (RPi üzerinde):
    pip install flask picamera2 opencv-python

Kullanım:
    # RPi'de:
    python rpi_streamer.py
    
    # PC'de (capture.py veya test):
    stream_url = "http://RPI_IP_ADRESI:8080/video"

Alternatif Yöntemler (Yorum satırlarında):
    1. Flask + PiCamera2 (Bu dosya) - En kolay
    2. mjpg-streamer (Bash script) - Daha performanslı
    3. GStreamer (Pipeline) - En düşük gecikme
    4. RTSP Server - Profesyonel

# =============================================================================
# ALTERNATİF 1: MJPG-STREAMER (BASH)
# =============================================================================
# Kurulum (bir kere):
#     sudo apt update
#     sudo apt install mjpg-streamer
#
# Çalıştırma:
#     mjpg_streamer \
#         -i "input_raspicam.so -fps 30 -x 640 -y 480" \
#         -o "output_http.so -p 8080 -w /usr/share/mjpg-streamer/www"
#
# PC'de erişim:
#     http://RPI_IP:8080/?action=stream
#
# =============================================================================

# =============================================================================
# ALTERNATİF 2: GSTREAMER (EN DÜŞÜK GECİKME)
# =============================================================================
# Kurulum:
#     sudo apt install gstreamer1.0-tools gstreamer1.0-plugins-good
#
# RPi tarafı (göndermek):
#     gst-launch-1.0 libcamerasrc ! \
#         video/x-raw,width=640,height=480,framerate=30/1 ! \
#         videoconvert ! \
#         jpegenc ! \
#         tcpserversink host=0.0.0.0 port=5000
#
# PC tarafı (almak için OpenCV):
#     cap = cv2.VideoCapture("tcp://RPI_IP:5000")
#
# =============================================================================

# =============================================================================
# ALTERNATİF 3: RTSP SERVER
# =============================================================================
# Kurulum:
#     pip install aiortsp
#     # veya
#     sudo apt install vlc
#
# VLC ile:
#     cvlc v4l2:///dev/video0 --sout '#transcode{vcodec=h264}:rtp{sdp=rtsp://:8554/stream}'
#
# PC'de:
#     cap = cv2.VideoCapture("rtsp://RPI_IP:8554/stream")
#
# =============================================================================
"""

import cv2
import time
import threading
from flask import Flask, Response, render_template_string

# Flask uygulaması
app = Flask(__name__)

# Global değişkenler
output_frame = None
frame_lock = threading.Lock()

# Yapılandırma
CONFIG = {
    "width": 640,
    "height": 480,
    "fps": 30,
    "quality": 80,  # JPEG kalitesi (1-100)
    "port": 8080
}


def camera_thread():
    """
    Kamera thread'i - sürekli frame yakalar
    
    Bu fonksiyon ayrı bir thread'de çalışır.
    Frame'leri global output_frame değişkenine yazar.
    """
    global output_frame
    
    try:
        from picamera2 import Picamera2
        
        print("[KAMERA] PiCamera2 başlatılıyor...")
        
        picam2 = Picamera2()
        config = picam2.create_video_configuration(
            main={"size": (CONFIG["width"], CONFIG["height"]), "format": "RGB888"}
        )
        picam2.configure(config)
        picam2.start()
        
        print(f"[KAMERA] Aktif: {CONFIG['width']}x{CONFIG['height']} @ {CONFIG['fps']} FPS")
        
        while True:
            # Frame yakala
            frame = picam2.capture_array()
            
            # RGB -> BGR (OpenCV için)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Thread-safe güncelleme
            with frame_lock:
                output_frame = frame.copy()
            
            # FPS kontrolü
            time.sleep(1.0 / CONFIG["fps"])
            
    except ImportError:
        print("[HATA] picamera2 bulunamadı!")
        print("[HATA] Bu script Raspberry Pi üzerinde çalışmalı!")
        print("[HATA] Kurulum: pip install picamera2")
        
        # Fallback: USB kamera dene
        print("\n[BİLGİ] USB kamera deneniyor...")
        fallback_camera()
        
    except Exception as e:
        print(f"[HATA] Kamera hatası: {e}")


def fallback_camera():
    """
    PiCamera yoksa USB kamera kullan (test için)
    """
    global output_frame
    
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("[HATA] Hiçbir kamera bulunamadı!")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CONFIG["width"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CONFIG["height"])
    
    print("[KAMERA] USB kamera aktif (fallback)")
    
    while True:
        ret, frame = cap.read()
        
        if ret:
            with frame_lock:
                output_frame = frame.copy()
        
        time.sleep(1.0 / CONFIG["fps"])


def generate_frames():
    """
    Frame generator - HTTP streaming için
    
    Bu fonksiyon MJPEG formatında sürekli frame üretir.
    Her frame JPEG olarak encode edilir ve boundary ile ayrılır.
    """
    global output_frame
    
    while True:
        # Frame hazır olana kadar bekle
        if output_frame is None:
            time.sleep(0.1)
            continue
        
        # Thread-safe okuma
        with frame_lock:
            frame = output_frame.copy()
        
        # JPEG encode
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), CONFIG["quality"]]
        ret, buffer = cv2.imencode('.jpg', frame, encode_param)
        
        if not ret:
            continue
        
        # MJPEG frame formatı
        # Her frame "--frame" boundary ile ayrılır
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')


# =============================================================================
# HTTP ROUTES
# =============================================================================

@app.route('/')
def index():
    """Ana sayfa - basit HTML player"""
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>RPi Kamera Stream</title>
        <style>
            body { 
                font-family: Arial; 
                background: #1a1a1a; 
                color: white;
                text-align: center;
                padding: 20px;
            }
            h1 { color: #4CAF50; }
            img { 
                border: 2px solid #4CAF50;
                border-radius: 10px;
            }
            .info {
                margin-top: 20px;
                padding: 10px;
                background: #333;
                border-radius: 5px;
                display: inline-block;
            }
        </style>
    </head>
    <body>
        <h1>🎥 Raspberry Pi Kamera Stream</h1>
        <img src="/video" width="{{ width }}" height="{{ height }}">
        <div class="info">
            <p>Çözünürlük: {{ width }}x{{ height }}</p>
            <p>Stream URL: <code>http://&lt;IP&gt;:{{ port }}/video</code></p>
        </div>
    </body>
    </html>
    ''', width=CONFIG["width"], height=CONFIG["height"], port=CONFIG["port"])


@app.route('/video')
def video_feed():
    """
    Video stream endpoint
    
    Bu URL'i capture.py'de stream_url olarak kullanın:
        stream_url = "http://RPI_IP:8080/video"
    """
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/snapshot')
def snapshot():
    """Tek frame döndür (JPG)"""
    global output_frame
    
    if output_frame is None:
        return "Kamera hazır değil", 503
    
    with frame_lock:
        frame = output_frame.copy()
    
    ret, buffer = cv2.imencode('.jpg', frame)
    return Response(buffer.tobytes(), mimetype='image/jpeg')


@app.route('/status')
def status():
    """Sunucu durumu"""
    return {
        "status": "running",
        "width": CONFIG["width"],
        "height": CONFIG["height"],
        "fps": CONFIG["fps"],
        "quality": CONFIG["quality"]
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="RPi Kamera Stream Server")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port")
    parser.add_argument("--width", type=int, default=640, help="Görüntü genişliği")
    parser.add_argument("--height", type=int, default=480, help="Görüntü yüksekliği")
    parser.add_argument("--fps", type=int, default=30, help="Frame rate")
    parser.add_argument("--quality", type=int, default=80, help="JPEG kalitesi (1-100)")
    args = parser.parse_args()
    
    # Yapılandırmayı güncelle
    CONFIG["port"] = args.port
    CONFIG["width"] = args.width
    CONFIG["height"] = args.height
    CONFIG["fps"] = args.fps
    CONFIG["quality"] = args.quality
    
    print("=" * 50)
    print("  Raspberry Pi Kamera Stream Server")
    print("=" * 50)
    print(f"  Çözünürlük: {CONFIG['width']}x{CONFIG['height']}")
    print(f"  FPS: {CONFIG['fps']}")
    print(f"  Port: {CONFIG['port']}")
    print(f"  Kalite: {CONFIG['quality']}%")
    print("=" * 50)
    print()
    print("  PC'de kullanım:")
    print(f"    stream_url = \"http://<RPI_IP>:{CONFIG['port']}/video\"")
    print()
    print("  Tarayıcıda görüntüleme:")
    print(f"    http://<RPI_IP>:{CONFIG['port']}/")
    print()
    print("=" * 50)
    
    # Kamera thread'ini başlat
    cam_thread = threading.Thread(target=camera_thread, daemon=True)
    cam_thread.start()
    
    # 1 saniye bekle (kamera başlaması için)
    time.sleep(1)
    
    # Flask sunucusunu başlat
    # host='0.0.0.0' = tüm ağ arayüzlerinden erişilebilir
    app.run(host='0.0.0.0', port=CONFIG["port"], threaded=True)
