"""

capture.py → yolo_detector.py → pid_controller.py → motor_calculator.py → serial_comm.py
   ↑              ↑                   ↑                    ↑                    ↑
 Görüntü al    Nesne bul         Hata hesapla         Açı hesapla          Arduino'ya gönder

 #!!!!!!! YAML değişiklikleri direk main değişikliklerine uygulanmaz eğer main.py içinde değişiklik yaparsan yaml dosyasını güncellemen gerekir! eğer 

1. python main.py çalıştır
        │
        ▼
2. YAML dosyası OKUNUR (bir kez)
   config = yaml.safe_load(f)
        │
        ▼
3. Değerler belleğe KOPYALANIR
   self.config = {...}
        │
        ▼
4. Program çalışır (YAML artık okunmaz)
        │
        ▼
5. YAML'ı değiştirsen bile ETKİSİ YOK!
   (Çünkü bellekteki kopya kullanılıyor)

   

u an 
main.py
 sadece şunu yapıyor:

Kameradan hedefi buluyor.
Motorun gitmesi gereken yeri hesaplıyor.
serial.send_command(...) diyerek Arduino'ya "GİT" diyor.
Arduino'dan cevap (feedback) beklemiyor veya dinlemiyor.
O yüzden 
main.py
 içinde serial.on_receive = ... gibi bir satır göremezsin. Sistem şu an tek yönlü (PC -> Arduino) çalışıyor
"""


import os
import sys
import time
import yaml
import argparse
import cv2
import numpy as np
from pathlib import Path

# Proje modülleri
from camera.capture import CameraCapture
from detection.yolo_detector import YOLODetector, Detection
from control.pid_controller import DualAxisPIDController, PIDGains
from control.motor_calculator import MotorCalculator, MotorConfig, CameraConfig
from communication.serial_comm import SerialCommunicator, MotorCommand

# ──────────────────────────────────────────────────────────
# YENİ EKLEME: GUI modülleri
# (Eğer PyQt6 kurulu değilse GUI olmadan çalışmaya devam eder)
# ──────────────────────────────────────────────────────────
try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QThread, pyqtSignal, QObject
    from improved import CelikKubbeMainWindow  # improved.py aynı klasörde olmalı
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    print("[UYARI] PyQt6 veya improved.py bulunamadı. GUI olmadan çalışılıyor.")


class ObjectTracker:
    """Ana nesne takip sınıfı"""
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        """
        Args:
            config_path: Yapılandırma dosyası yolu
        """
        self.config = self._load_config(config_path)
        
        # Bileşenler
        self.camera = None
        self.detector = None
        self.pid = None
        self.motor_calc = None
        self.serial = None
        
        # Durum
        self.running = False
        self.tracking_enabled = True
        self.target_lost_time = 0
        self.last_target = None
        
        # İstatistikler
        self.frame_count = 0
        self.fps = 0
        self.last_fps_time = time.time()
        
    def _load_config(self, config_path: str) -> dict:
        """Yapılandırma dosyasını yükle"""
        config_file = Path(config_path)
        
        if not config_file.exists():
            print(f"[UYARI] Yapılandırma dosyası bulunamadı: {config_path}")
            print("[UYARI] Varsayılan değerler kullanılıyor...")
            return self._get_default_config()
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _get_default_config(self) -> dict:
        """Varsayılan yapılandırma"""
        return {
            'camera': {
                'id': 0,
                'width': 640,
                'height': 480,
                'fps': 30,
                'use_picamera': False,
                'fov_horizontal': 60.0,
                'fov_vertical': 45.0
            },
            'detection': {
                'model_path': 'yolov8n.pt',
                'confidence': 0.5,
                'device': 'auto',
                'target_classes': []
            },
            'pid': {
                'pan': {'kp': 0.15, 'ki': 0.01, 'kd': 0.08},
                'tilt': {'kp': 0.15, 'ki': 0.01, 'kd': 0.08},
                'output_min': -100.0,
                'output_max': 100.0,
                'deadband': 10
            },
            'motors': {
                'pan': {
                    'steps_per_revolution': 200,
                    'microstepping': 16,
                    'gear_ratio': 1.0,
                    'max_speed': 2000,
                    'min_angle': -180,
                    'max_angle': 180
                },
                'tilt': {
                    'steps_per_revolution': 200,
                    'microstepping': 16,
                    'gear_ratio': 1.0,
                    'max_speed': 2000,
                    'min_angle': -45,
                    'max_angle': 90
                }
            },
            'serial': {
                'port': '/dev/ttyUSB0',
                'baudrate': 115200
            },
            'tracking': {
                'target_threshold': 15,
                'lost_target_timeout': 3.0
            },
            'display': {
                'show_video': True,
                'show_crosshair': True,
                'show_info': True
            },
            'debug': {
                'print_fps': True
            }
        }
    
    def initialize(self) -> bool:
        """Tüm bileşenleri başlat"""
        print("=" * 50)
        print("Pan-Tilt Nesne Takip Sistemi Başlatılıyor...")
        print("=" * 50)
        
        # 1. Kamera
        print("\n[1/5] Kamera başlatılıyor...")
        cam_cfg = self.config['camera']
        self.camera = CameraCapture(
            camera_id=cam_cfg['id'],
            width=cam_cfg['width'],
            height=cam_cfg['height'],
            fps=cam_cfg['fps'],
            use_picamera=cam_cfg.get('use_picamera', False),
            stream_url=cam_cfg.get('stream_url', None)
        )
        
        if not self.camera.start():
            print("[HATA] Kamera başlatılamadı!")
            return False
        
        # 2. YOLO Detector
        print("\n[2/5] YOLO modeli yükleniyor...")
        det_cfg = self.config['detection']
        self.detector = YOLODetector(
            model_path=det_cfg['model_path'],
            confidence_threshold=det_cfg['confidence'],
            target_classes=det_cfg.get('target_classes', []),
            device=det_cfg.get('device', 'auto')
        )
        
        if not self.detector.load_model():
            print("[HATA] YOLO modeli yüklenemedi!")
            return False
        
        # 3. PID Kontrolcü
        print("\n[3/5] PID kontrolcü oluşturuluyor...")
        pid_cfg = self.config['pid']
        pan_gains = PIDGains(**pid_cfg['pan'])
        tilt_gains = PIDGains(**pid_cfg['tilt'])
        
        self.pid = DualAxisPIDController(
            pan_gains=pan_gains,
            tilt_gains=tilt_gains,
            output_min=pid_cfg['output_min'],
            output_max=pid_cfg['output_max'],
            deadband=pid_cfg['deadband']
        )
        print("[PID] Kontrolcü oluşturuldu")
        
        # 4. Motor Calculator
        print("\n[4/5] Motor hesaplayıcı oluşturuluyor...")
        motor_cfg = self.config['motors']
        cam_cfg = self.config['camera']
        
        pan_motor = MotorConfig(**motor_cfg['pan'])
        tilt_motor = MotorConfig(**motor_cfg['tilt'])
        camera_config = CameraConfig(
            width=cam_cfg['width'],
            height=cam_cfg['height'],
            fov_horizontal=cam_cfg['fov_horizontal'],
            fov_vertical=cam_cfg['fov_vertical']
        )
        
        self.motor_calc = MotorCalculator(
            pan_motor=pan_motor,
            tilt_motor=tilt_motor,
            camera=camera_config
        )
        
        # 5. Serial Haberleşme
        print("\n[5/5] Serial bağlantı kuruluyor...")
        serial_cfg = self.config['serial']
        self.serial = SerialCommunicator(
            port=serial_cfg['port'],
            baudrate=serial_cfg['baudrate']
        )
        
        if not self.serial.connect():
            print("[UYARI] Serial bağlantı kurulamadı!")
            print("[UYARI] Simülasyon modunda devam ediliyor...")
        else:
            self.serial.start_reading()
        
        print("\n" + "=" * 50)
        print("Sistem hazır!")
        print("=" * 50)
        
        return True
    
    def run(self):
        """Ana takip döngüsü — GUI OLMADAN çalışır (orijinal kod)"""
        self.running = True
        
        print("\nTakip başlıyor... ('q': çık, 'p': duraklat, 'h': home)")
        
        while self.running:
            ret, frame = self.camera.read()
            if not ret:
                print("[HATA] Frame alınamadı!")
                continue
            
            annotated, detections = self.detector.detect_and_draw(frame)
            frame_center = self.camera.get_center()
            target = self.detector.get_primary_target(detections)
            
            if target and self.tracking_enabled:
                self._track_target(target, frame_center)
                self.target_lost_time = 0
                self.last_target = target
            else:
                self._handle_lost_target()
            
            if self.config['display']['show_video']:
                self._draw_overlay(annotated, target, frame_center)
                cv2.imshow("Pan-Tilt Tracker", annotated)
            
            self._update_fps()
            
            key = cv2.waitKey(1) & 0xFF
            if not self._handle_key(key):
                break
        
        self.cleanup()
    
    def _track_target(self, target: Detection, frame_center: tuple):
        """Hedefi takip et"""
        error_x, error_y = self.detector.calculate_error(target, frame_center)
        
        pan_angle_error, tilt_angle_error = self.motor_calc.pixel_error_to_angle(
            error_x, error_y
        )
        
        pan_output, tilt_output = self.pid.update(pan_angle_error, tilt_angle_error)
        
        movement = self.motor_calc.calculate_movement(
            int(pan_output),
            int(tilt_output)
        )
        
        if self.serial and self.serial.is_connected():
            cmd = MotorCommand(
                pan_steps=movement['pan_units'],
                tilt_counts=movement['tilt_units'],
                pan_speed=movement['pan_speed'],
                tilt_speed=movement['tilt_speed']
            )
            self.serial.send_command(cmd)
        
        self.motor_calc.update_position(
            movement['target_pan_degrees'],
            movement['target_tilt_degrees']
        )
    
    def _handle_lost_target(self):
        """Hedef kaybolduğunda"""
        if self.last_target:
            self.target_lost_time += 1.0 / self.config['camera']['fps']
            
            timeout = self.config['tracking'].get('lost_target_timeout', 3.0)
            if self.target_lost_time > timeout:
                self.last_target = None
                self.pid.reset()
    
    def _draw_overlay(self, frame: np.ndarray, target: Detection, center: tuple):
        """Görselleştirme overlay'i çiz"""
        h, w = frame.shape[:2]
        
        if self.config['display'].get('show_crosshair', True):
            cv2.line(frame, (center[0] - 30, center[1]), (center[0] - 10, center[1]), (0, 255, 0), 2)
            cv2.line(frame, (center[0] + 10, center[1]), (center[0] + 30, center[1]), (0, 255, 0), 2)
            cv2.line(frame, (center[0], center[1] - 30), (center[0], center[1] - 10), (0, 255, 0), 2)
            cv2.line(frame, (center[0], center[1] + 10), (center[0], center[1] + 30), (0, 255, 0), 2)
            cv2.circle(frame, center, 5, (0, 255, 0), 1)
        
        if self.config['display'].get('show_info', True):
            info_y = 30
            line_height = 25
            
            cv2.putText(frame, f"FPS: {self.fps:.1f}", (10, info_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            info_y += line_height
            
            status = "TRACKING" if target else "SEARCHING"
            color = (0, 255, 0) if target else (0, 165, 255)
            cv2.putText(frame, f"Status: {status}", (10, info_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            info_y += line_height
            
            pan = self.motor_calc.current_pan_angle
            tilt = self.motor_calc.current_tilt_angle
            cv2.putText(frame, f"Pan: {pan:.1f}  Tilt: {tilt:.1f}", (10, info_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            info_y += line_height
            
            if target:
                error_x, error_y = self.detector.calculate_error(target, center)
                cv2.putText(frame, f"Error: X={error_x:+d} Y={error_y:+d}", (10, info_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                cv2.line(frame, center, target.center, (255, 0, 255), 1)
    
    def _update_fps(self):
        """FPS hesapla"""
        self.frame_count += 1
        current_time = time.time()
        elapsed = current_time - self.last_fps_time
        
        if elapsed >= 1.0:
            self.fps = self.frame_count / elapsed
            self.frame_count = 0
            self.last_fps_time = current_time
            
            if self.config['debug'].get('print_fps', True):
                print(f"\rFPS: {self.fps:.1f}", end="", flush=True)
    
    
    def _handle_key(self, key: int) -> bool:
        """Klavye girdisini işle"""
        if key == ord('q'):
            print("\nÇıkış yapılıyor...")
            return False
        elif key == ord('p'):
            self.tracking_enabled = not self.tracking_enabled
            status = "AKTIF" if self.tracking_enabled else "DURAKLATILDI"
            print(f"\nTakip: {status}")
        elif key == ord('h'):
            print("\nHome pozisyonuna gidiliyor...")
            if self.serial and self.serial.is_connected():
                self.serial.send_home()
            self.motor_calc.reset_position()
            self.pid.reset()
        elif key == ord('c'):
            print("\nKalibrasyon...")
            if self.serial and self.serial.is_connected():
                self.serial.send_calibrate()
            self.motor_calc.reset_position()
        elif key == ord('s'):
            print("\nDurdur!")
            if self.serial and self.serial.is_connected():
                self.serial.send_stop()
        
        return True
    
    def cleanup(self):
        """Temizlik"""
        print("\nSistem kapatılıyor...")
        
        if self.camera:
            self.camera.stop()
        
        if self.serial:
            self.serial.disconnect()
        
        cv2.destroyAllWindows()
        print("Sistem kapatıldı.")


# ══════════════════════════════════════════════════════════
# YENİ EKLEME: GUI için Worker sınıfı
# ObjectTracker sınıfı hiç değişmedi.
# Bu sınıf kamera döngüsünü ayrı bir thread'de çalıştırır
# ki GUI penceresi donmasın.
# ══════════════════════════════════════════════════════════
class TrackerWorker(QObject if GUI_AVAILABLE else object):
    """
    Kamera döngüsünü arka planda çalıştırır.
    GUI thread'i ile sinyal/slot sistemiyle haberleşir.

    Nasıl çalışır:
        main thread  →  GUI penceresi (PyQt6)
        worker thread →  Kamera + YOLO + PID + Serial

    İkisi birbirini bloklamaz.
    """
    if GUI_AVAILABLE:
        # GUI'ye gönderilecek veriler (sinyal = "hazır olunca şunu çağır")
        frame_ready     = pyqtSignal(object, list, float)  # frame, tespitler, fps
        detection_ready = pyqtSignal(object)               # birincil hedef
        position_ready  = pyqtSignal(float, float)         # pan açısı, tilt açısı

    def __init__(self, tracker: ObjectTracker):
        if GUI_AVAILABLE:
            super().__init__()
        self.tracker = tracker
        self.running = False

    def run(self):
        """
        Bu fonksiyon ayrı bir thread'de çalışır.
        Orijinal tracker.run() ile aynı işi yapar,
        fakat sonuçları cv2.imshow yerine GUI sinyalleriyle gönderir.
        """
        self.running = True
        self.tracker.running = True

        while self.running:
            # ── Orijinal döngü mantığı (değişmedi) ──
            ret, frame = self.tracker.camera.read()
            if not ret:
                time.sleep(0.01)  # CPU'yu boşuna yormamak için kısa bekleme
                continue

            annotated, detections = self.tracker.detector.detect_and_draw(frame)
            frame_center = self.tracker.camera.get_center()
            target = self.tracker.detector.get_primary_target(detections)

            if target and self.tracker.tracking_enabled:
                self.tracker._track_target(target, frame_center)
                self.tracker.target_lost_time = 0
                self.tracker.last_target = target
            else:
                self.tracker._handle_lost_target()

            self.tracker._update_fps()

            # ── GUI'ye veri gönder ──
            # Detection nesnelerini dict'e çevir (PyQt sinyali dict alır)
            det_dicts = []
            for d in detections:
                det_dicts.append({
                    'class_name': getattr(d, 'class_name', 'unknown'),
                    'confidence': getattr(d, 'confidence', 0.0),
                    'bbox':       getattr(d, 'bbox', (0, 0, 0, 0)),
                    'is_friend':  getattr(d, 'class_name', '') == 'friend'
                })

            primary_dict = None
            if target:
                primary_dict = {
                    'class_name': getattr(target, 'class_name', 'unknown'),
                    'confidence': getattr(target, 'confidence', 0.0),
                    'bbox':       getattr(target, 'bbox', (0, 0, 0, 0)),
                    'is_friend':  getattr(target, 'class_name', '') == 'friend'
                }

            if GUI_AVAILABLE:
                self.frame_ready.emit(annotated, det_dicts, self.tracker.fps)
                self.detection_ready.emit(primary_dict)
                self.position_ready.emit(
                    self.tracker.motor_calc.current_pan_angle,
                    self.tracker.motor_calc.current_tilt_angle
                )

    def stop(self):
        self.running = False
        self.tracker.running = False


# ══════════════════════════════════════════════════════════
# main() — iki mod:
#   python main.py          → GUI ile başlar
#   python main.py --no-gui → Eski saf terminal modu
# ══════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="Pan-Tilt Nesne Takip Sistemi")
    parser.add_argument(
        "-c", "--config",
        default="config/settings.yaml",
        help="Yapılandırma dosyası yolu"
    )
    parser.add_argument(
        "--no-serial",
        action="store_true",
        help="Serial bağlantı olmadan çalış (simülasyon)"
    )
    # YENİ: --no-gui bayrağı — eski terminal modunu korur
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="GUI olmadan çalış (sadece terminal + OpenCV penceresi)"
    )

    args = parser.parse_args()

    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    tracker = ObjectTracker(config_path=args.config)

    if not tracker.initialize():
        print("[HATA] Sistem başlatılamadı!")
        sys.exit(1)

    # ── GUI MODU ──────────────────────────────────────────
    if GUI_AVAILABLE and not args.no_gui:
        app = QApplication(sys.argv)

        # GUI penceresini aç
        window = CelikKubbeMainWindow()
        window.showMaximized()

        # Serial bağlıysa GUI'ye bildir (üst köşedeki bağlantı göstergesi)
        if tracker.serial and tracker.serial.is_connected():
            window.set_serial_communicator(tracker.serial)

        # Worker'ı ayrı thread'e taşı
        worker = TrackerWorker(tracker)
        thread = QThread()
        worker.moveToThread(thread)

        # Worker sinyalleri → GUI güncellemeleri
        worker.frame_ready.connect(window.update_camera_frame)
        worker.detection_ready.connect(window.update_detection)
        worker.position_ready.connect(window.update_motor_position)

        # Thread başladığında worker.run() çağrılsın
        thread.started.connect(worker.run)

        # GUI butonları → Serial komutlar
        # (tracker.serial None olabilir, o yüzden lambda içinde kontrol)
        def emergency_serial_stop():
            if tracker.serial and tracker.serial.is_connected():
                tracker.serial.send_stop()
        window.btn_emergency.clicked.connect(emergency_serial_stop)

        # Uygulama kapanırken temizlik
        def on_quit():
            worker.stop()
            thread.quit()
            thread.wait(3000)   # max 3 sn bekle
            tracker.cleanup()

        app.aboutToQuit.connect(on_quit)

        # Thread'i başlat, sonra Qt döngüsüne gir
        thread.start()
        sys.exit(app.exec())

    # ── TERMİNAL MODU (orijinal kod, hiç değişmedi) ──────
    else:
        if not GUI_AVAILABLE and not args.no_gui:
            print("[BİLGİ] PyQt6 bulunamadı, terminal modunda çalışılıyor.")
        try:
            tracker.run()
        except KeyboardInterrupt:
            print("\nCtrl+C ile durduruldu")
            tracker.cleanup()


if __name__ == "__main__":
    main()