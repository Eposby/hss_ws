"""
Kamera Yakalama Modülü
USB, Raspberry Pi kamera ve Network Stream desteği

Desteklenen kaynaklar:
1. USB Kamera: Doğrudan PC'ye bağlı kamera
2. PiCamera: Raspberry Pi üzerinde çalışırken (picamera2 gerekli)
3. Network Stream: RPi'den HTTP/RTSP stream (uzaktan görüntü alma)

Kullanım Senaryoları:
- USB: camera_id=0, stream_url=None 
ls -l /dev/video*
mert@mert:~/hss_ws$ cd /home/mert/hss_ws/src/prototip
mert@mert:~/hss_ws/src/prototip$ ls -l /dev/video*
crw-rw----+ 1 root video 81, 0 Feb 19 08:56 /dev/video0
crw-rw----+ 1 root video 81, 1 Feb 19 08:56 /dev/video1
mert@mert:~/hss_ws/src/prototip$ 


- PiCamera (RPi üzerinde): use_picamera=True
- Network (RPi'den PC'ye): stream_url="http://192.168.1.100:8080/video"


Seçenek A: Router üzerinden (her ikisi de router'a bağlı)
Seçenek B: Direkt bağlantı (RPi ↔ PC kablo ile)


Sadece Test Kodunu (
capture.py
) Çalıştırırken: Bu dosya tek başına çalışırken ayar dosyasına bakmaz. Test ederken kamerayı seçmek için komut satırından belirtmeniz gerekir: python src/prototip/camera/capture.py --camera 1 (2. kamera için) python src/prototip/camera/capture.py --camera 0 (1. kamera için - varsayılan)



# RPi'de IP adresini öğren:
hostname -I
# Örnek çıktı: 192.168.1.100

# veya direkt bağlantı için statik IP:
sudo nano /etc/dhcpcd.conf
# Ekle:
# interface eth0
# static ip_address=192.168.1.100/24



cd /prototip/camera
python rpi_streamer.py --port 8080

camera:
  stream_url: "http://192.168.1.100:8080/video"  # RPi'nin IP adresi


cd /home/mert/hss_ws/src/prototip/camera
python capture.py --stream "http://192.168.1.100:8080/video"




2. Komut Satırı ile Kontrol Etme (RPi üzerinde)
Kameranız bağlıysa, Raspberry Pi terminalinde şu komutu çalıştırarak modelini öğrenebilirsiniz:


libcamera-hello --list-cameras

Çıktıda imx219 (v2), imx708 (v3), imx477 (HQ) gibi sensör isimlerini görürsünüz.

"""

import numpy as np
import cv2
import time
from typing import Optional, Tuple, Union

"""
Tip	Anlamı	Örnek
Optional[X]	X tipi veya None olabilir	Optional[str] = 
str
 veya None

Tuple[X, Y]	(X, Y) formatında tuple	Tuple[int, int] = 
(320, 240)

Union[X, Y]	X veya Y tipinde olabilir	Union[int, str] = 0 veya "video.mp4"

"""


# # 1. Optional - None olabilir
# def __init__(self, stream_url: str = None):
#     #              ↑ stream_url ya str ya da None

# # Daha doğru yazımı:
# def __init__(self, stream_url: Optional[str] = None):
#     #              ↑ Açıkça "str veya None" diyor


# # 2. Tuple - Birden fazla değer döndürme
# def read(self) -> Tuple[bool, Optional[np.ndarray]]:
#     #           ↑ (True, frame) veya (False, None) döner
#     return True, frame   # Tuple[bool, ndarray]
#     return False, None   # Tuple[bool, None]


# # 3. Union - Birden fazla tip kabul etme  
# def __init__(self, camera_id: Union[int, str] = 0):
#     #                         ↑ int (kamera ID) veya str (dosya yolu)
#     # camera_id = 0           → USB kamera
#     # camera_id = "video.mp4" → Video dosyası



class CameraCapture:
    """
    Çoklu kaynak destekli kamera yakalama sınıfı
    
    Öncelik sırası:
    1. stream_url varsa → Network stream kullan
    2. use_picamera=True ise → PiCamera kullan
    3. Varsayılan → USB kamera kullan
    """
    # buradaki değerler default değerlerdir. Eğer başka değerler verilmezse bu değerler kullanılır.
    def __init__(
        self,
        camera_id: Union[int, str] = 0,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        use_picamera: bool = False,
        stream_url: str = None
    ):
        """
        Kamera yakalama sınıfı constructor
        
        Args:
            camera_id: USB kamera ID (0, 1, 2...) veya video dosya yolu ("video.mp4")
            width: Görüntü genişliği (piksel)
            height: Görüntü yüksekliği (piksel)
            fps: Hedef frame rate (saniyede kare)
            use_picamera: True ise Raspberry Pi kamera kullan (RPi üzerinde çalışırken)
            stream_url: Network stream URL'i (örn: "http://192.168.1.100:8080/video")
                       Bu parametre verilirse diğerleri göz ardı edilir
        
        Örnekler:
            # USB kamera
            cam = CameraCapture(camera_id=0)
            
            # Video dosyası
            cam = CameraCapture(camera_id="test_video.mp4")
            
            # RPi'den network stream
            cam = CameraCapture(stream_url="http://192.168.1.100:8080/video")
            
            # RPi üzerinde PiCamera
            cam = CameraCapture(use_picamera=True)
        """
        # Temel parametreler
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps
        self.use_picamera = use_picamera
        self.stream_url = stream_url
        
        # Kamera objeleri (başlatılınca doldurulur)
        self.cap = None          # OpenCV VideoCapture objesi
        self.picamera = None     # Picamera2 objesi
        
        # FPS kontrolü için zamanlama
        self.last_frame_time = 0
        self.frame_interval = 1.0 / fps  # Her frame arası bekleme süresi
        
        # Bağlantı durumu
        # success bir fonksiyona atanmazsa geriye false döner start fonksiyonuna bak
        self.is_running = False
        self.source_type = None  # "usb", "picamera", "stream"
        
    def start(self) -> bool:
        """
        Kamerayı başlat
        
        Returns:
            bool: Başarılı ise True, değilse False
        
        Öncelik sırası:
        1. stream_url varsa → Network stream
        2. use_picamera=True → PiCamera
        3. Varsayılan → USB/Video dosyası

        bu kısım birden fazla durum için oluşturuldu eğer kamera değişirse sadece durum değiştirilecek
        """
        if self.stream_url:
            success = self._start_network_stream()
            if success:
                self.source_type = "stream"
        elif self.use_picamera:
            success = self._start_picamera()
            if success:
                self.source_type = "picamera"
        else:
            success = self._start_usb_camera()
            if success:
                self.source_type = "usb"
        
        self.is_running = success
        return success
    
    def _start_network_stream(self) -> bool:
        """
        Network stream'den görüntü al
        
        HTTP MJPEG, RTSP veya diğer stream protokollerini destekler.
        OpenCV otomatik olarak protokolü algılar.
        
        Desteklenen URL formatları:
        - HTTP MJPEG: http://ip:port/video
        - RTSP: rtsp://ip:port/stream
        - GStreamer: gst-pipeline...
        
        Returns:
            bool: Bağlantı başarılı ise True
        """
        print(f"[KAMERA] Network stream'e bağlanılıyor: {self.stream_url}")
        
        # OpenCV VideoCapture URL'leri destekler
        self.cap = cv2.VideoCapture(self.stream_url)
        # rpi'de stream server çalışıyor mu? IP adresi ve port doğru mu? kontrol et 
        if not self.cap.isOpened():
            print(f"Stream açılamadı: {self.stream_url}")
            return False
        
        # Buffer boyutunu küçült - gecikmeyi azaltır
        # Network stream'lerde buffer büyükse eski frame'ler birikir
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Stream bilgilerini al (varsa)
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Çözünürlüğü güncelle (stream'den gelen değerler)
        if actual_width > 0 and actual_height > 0:
            self.width = actual_width
            self.height = actual_height
        
        print(f"[KAMERA] Network stream bağlandı: {self.width}x{self.height}")
        return True
    

    def _start_usb_camera(self) -> bool:
        """
        USB kamera veya video dosyasını başlat
        
        camera_id:
        - int (0, 1, 2...): USB kamera indeksi
        - str ("video.mp4"): Video dosya yolu
        
        Returns:
            bool: Başarılı ise True
        """
        # Video dosyası mı yoksa kamera mı?
        # Bu fonksiyon, bir değişkenin belirli bir tipte olup olmadığını kontrol eder.

        # Sayı mı?
        # isinstance(5, int)           # True
        # isinstance("5", int)         # False

        # # String mi?
        # isinstance("video.mp4", str) # True
        # isinstance(0, str)           # False

        # # Liste mi?
        # isinstance([1,2,3], list)    # True


        if isinstance(self.camera_id, str):
            print(f"[KAMERA] Video dosyası açılıyor: {self.camera_id}")
        else:
            print(f"[KAMERA] USB kamera açılıyor: {self.camera_id}")
        
        # VideoCapture hem int (kamera) hem str (dosya) kabul eder
        self.cap = cv2.VideoCapture(self.camera_id)
        
        if not self.cap.isOpened():
            print(f" Kaynak açılamadı: {self.camera_id}")
            return False
        
        # Kamera ayarları (video dosyası için etkisiz olabilir)

        # set
        #  (İstek Gönderme):
        # Siz: "Kamerayı 1920x1080 çözünürlüğe ayarla." (self.cap.set(...))
        # Kamera Sürücüsü: "Bakayım... Benim donanımım maksimum 1280x720 destekliyor veya o anki USB bant genişliği sadece 640x480'e izin veriyor."
        # Sonuç: Sürücü, sizin isteğinize en yakın yapabildiği ayarı sessizce uygular (örneğin 1280x720 yapar). Size hata vermez, sadece yapabildiğini yapar.
        # get
        #  (Gerçeği Öğrenme):
        # Siz: "Peki, şu an ayarların ne durumda?" (self.cap.get(...))
        # Kamera Sürücüsü: "Şu an 1280x720 çalışıyorum."
        # Siz: "Tamam, o zaman ben de hesaplamalarımı (ekran merkezi, hedef takibi vb.) bu gerçek değere göre güncelleyeyim." (self.width = actual_width)
        # Neden Önemli? Eğer 
        # get
        #  yapıp kontrol etmeseydiniz:

        # Siz kodunuzda width = 1920 sanardınız.
        # Kamera aslında 1280 gönderiyor olurdu.
        # Hesapladığınız ekran merkezi (1920/2 = 960) yanlış olurdu (doğrusu 1280/2 = 640).
        # Sonuç olarak robotunuz/sisteminiz hedefin yerini yanlış hesaplayıp yanlış yere bakardı.
        # Bu yüzden donanımla çalışırken kural şudur: "İsteğini söyle, ama donanımın ne yaptığını her zaman teyit et."
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        
        # Buffer boyutunu küçült (gecikmeyi azaltır)
        # Gerçek kameralarda önemli, video dosyalarında etkisiz
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Gerçek değerleri al (kamera desteklemeyebilir)
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        # Sınıf değişkenlerini güncelle
        self.width = actual_width
        self.height = actual_height
        
        print(f"[KAMERA] Kaynak başlatıldı: {actual_width}x{actual_height} @ {actual_fps:.1f} FPS")
        return True
    
    def _start_picamera(self) -> bool:
        """
        Raspberry Pi kamerayı başlat
        
        NOT: Bu metod sadece Raspberry Pi üzerinde çalışır!
        PC'den RPi kameraya erişmek için network stream kullanın.
        
        Gereksinimler:
        - Raspberry Pi (3, 4, veya 5)
        - picamera2 kütüphanesi: pip install picamera2
        - Kamera modülü takılı ve etkin
        
        Returns:
            bool: Başarılı ise True
        """
        try:
            # picamera2 sadece RPi'de çalışır
            from picamera2 import Picamera2
            
            print("[KAMERA] PiCamera başlatılıyor...")
            
            self.picamera = Picamera2()
            
            # Kamera yapılandırması
            config = self.picamera.create_preview_configuration(
                main={
                    "size": (self.width, self.height),
                    "format": "RGB888"  # 8-bit RGB format
                }
            )
            self.picamera.configure(config)
            self.picamera.start()
            
            print(f"[KAMERA] PiCamera başlatıldı: {self.width}x{self.height}")
            return True
            
        except ImportError:
            print("[HATA] picamera2 kütüphanesi bulunamadı!")
            print("[İPUCU] Kurulum: pip install picamera2")
            print("[İPUCU] Bu kod Raspberry Pi üzerinde mi çalışıyor?")
            return False
        except Exception as e:
            print(f"[HATA] PiCamera başlatılamadı: {e}")
            return False
    
    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Kameradan tek frame oku
        
        Returns:
            Tuple[bool, Optional[np.ndarray]]: 
                - (True, frame): Başarılı okuma, frame numpy array (BGR format)
                - (False, None): Okuma başarısız
        
        Not: OpenCV BGR renk formatı kullanır (Blue-Green-Red)
             Görselleştirme için uygundur, ama bazı kütüphaneler RGB bekler
        """
        # PiCamera kullanılıyorsa
        if self.use_picamera and self.picamera:
            try:
                # PiCamera RGB formatında döndürür
                frame = self.picamera.capture_array()
                
                # RGB -> BGR dönüşümü (OpenCV BGR kullanır)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                return True, frame
            except Exception as e:
                print(f"[HATA] PiCamera frame okunamadı: {e}")
                return False, None
        
        # USB kamera veya Network stream
        elif self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            
            # Video dosyası sonuna gelindiyse
            # usb kamera olunca ret False döner
            if not ret and isinstance(self.camera_id, str):
                print("[BİLGİ] Video dosyası sona erdi")
            
            return ret, frame
        
        # Hiçbir kaynak aktif değil
        return False, None
    
    def read_with_fps_limit(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        FPS limiti ile frame oku
        
        Bu metod, belirlenen FPS'i aşmamak için gerekirse bekler.
        Gerçek zamanlı uygulamalarda CPU kullanımını azaltır.
        
        Örnek:
            fps=30 ise, her frame arası en az 33.3ms olur
            Eğer işlem 10ms sürerse, 23.3ms bekler
        
        Returns:
            Tuple[bool, Optional[np.ndarray]]: read() ile aynı format
        """
        current_time = time.time()
        elapsed = current_time - self.last_frame_time
        
        # Hedef FPS'e ulaşmak için bekle
        if elapsed < self.frame_interval:
            sleep_time = self.frame_interval - elapsed
            time.sleep(sleep_time)
        
        # Zamanı kaydet
        self.last_frame_time = time.time()
        
        return self.read()
    
    def get_center(self) -> Tuple[int, int]:
        """
        Görüntü merkezini döndür
        
        Bu değer, hedef takip sisteminde referans noktası olarak kullanılır.
        Hedefin merkeze olan uzaklığı (error) hesaplanır.
        
        Returns:
            Tuple[int, int]: (center_x, center_y) piksel koordinatları

            # main.py satır 232
            frame_center = self.camera.get_center()  # Hedef takibi için merkez noktası
        """
        return self.width // 2, self.height // 2
    


    # burası dümenden silinebilir 
    def get_frame_size(self) -> Tuple[int, int]:
        """
        Frame boyutunu döndür
        
        Returns:
            Tuple[int, int]: (width, height)
        """
        return self.width, self.height
    


    # burası dümenden silinebilir 
    def get_source_info(self) -> dict:
        """
        Kaynak bilgilerini döndür
        
        Returns:
            dict: Kaynak tipi, boyut, FPS bilgileri
        """
        return {
            "source_type": self.source_type,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "is_running": self.is_running,
            "stream_url": self.stream_url,
            "camera_id": self.camera_id
        }
    

    def stop(self):
        """
        Kamerayı durdur ve kaynakları serbest bırak
        
        Bu metod mutlaka çağrılmalı, yoksa:
        - Kamera başka uygulamalar tarafından kullanılamaz
        - Bellek sızıntısı olabilir
        """
        if self.cap:
            self.cap.release()
            self.cap = None
            print(f"[KAMERA] {self.source_type} kapatıldı")
            
        if self.picamera:
            self.picamera.stop()
            self.picamera = None
            print("[KAMERA] PiCamera kapatıldı")
        
        self.is_running = False
    
    def __del__(self):
        """Destructor - nesne silinirken otomatik temizlik"""
        self.stop()
    
    def __enter__(self):
        """Context manager desteği: with CameraCapture() as cam:"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager çıkışı"""
        self.stop()


# =============================================================================
# TEST KODU
# =============================================================================
if __name__ == "__main__":
    """
    Doğrudan çalıştırıldığında test modu
    
    Kullanım:
        python capture.py                    # USB kamera test
        python capture.py --stream URL       # Network stream test
        python capture.py --picamera        # PiCamera test (RPi'de)
        python capture.py --video dosya.mp4 # Video dosyası test
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Kamera Yakalama Test")
    parser.add_argument("--stream", type=str, help="Network stream URL")
    parser.add_argument("--picamera", action="store_true", help="PiCamera kullan")
    parser.add_argument("--video", type=str, help="Video dosya yolu")
    parser.add_argument("--camera", type=int, default=0, help="USB kamera ID")
    args = parser.parse_args()
    
    print("=" * 50)
    print("Kamera Yakalama Test")
    print("=" * 50)
    
    # Kamera kaynağını belirle
    if args.stream:
        camera = CameraCapture(stream_url=args.stream)
    elif args.picamera:
        camera = CameraCapture(use_picamera=True)
    elif args.video:
        camera = CameraCapture(camera_id=args.video)
    else:
        camera = CameraCapture(camera_id=args.camera)
    
    # Kamerayı başlat
    if camera.start():
        print(f"\nKaynak bilgisi: {camera.get_source_info()}")
        print("'q' tuşuna basarak çıkın...\n")
        
        frame_count = 0
        start_time = time.time()
        
        while True:
            ret, frame = camera.read()
            
            if not ret:
                print("Frame alınamadı!")
                break
            
            frame_count += 1
            
            # FPS hesapla
            elapsed = time.time() - start_time
            if elapsed > 0:
                fps = frame_count / elapsed
            else:
                fps = 0
            
            # Merkez noktası çiz
            center_x, center_y = camera.get_center()
            cv2.circle(frame, (center_x, center_y), 5, (0, 255, 0), -1)
            cv2.line(frame, (center_x - 30, center_y), (center_x + 30, center_y), (0, 255, 0), 1)
            cv2.line(frame, (center_x, center_y - 30), (center_x, center_y + 30), (0, 255, 0), 1)
            
            # FPS göster
            cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Kaynak: {camera.source_type}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            cv2.imshow("Kamera Test", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        camera.stop()
        cv2.destroyAllWindows()
        
        print(f"\nToplam frame: {frame_count}")
        print(f"Ortalama FPS: {frame_count/elapsed:.1f}")
    else:
        print("Kamera başlatılamadı!")




# instance oluşturulurken self.cap=None ataması yapılmalı yoksa hata verir
#============================================================================
# HATA 1: self.cap'in nerede tanımlandığı belirsiz
#============================================================================

# # Yanlış:
# def __init__(self):
#     # self.cap tanımlanmadı!
#     pass

# def _start_picamera(self):
#     self.cap = Picamera2()  # İlk kez burada oluştu
    
# def stop(self):
#     if self.cap:   # HATA RİSKİ! 
#         self.cap.release()  # start() çağrılmadıysa self.cap yok!

# # Doğru:
# def __init__(self):
#     self.cap = None  # Başlangıçta None

# def _start_picamera(self):
#     self.cap = Picamera2()
    
# def stop(self):
#     if self.cap:
#         self.cap.release()


# #============================================================================
# # HATA 2: None kontrolü eksik
# #============================================================================

# # Yanlış:
# def read(self):
#     return self.cap.read()  # self.cap None ise hata verir!

# # Doğru:
# def read(self):
#     if self.cap is None:
#         return False, None
#     return self.cap.read()


# #============================================================================
# # HATA 3: Kaynak tipi kontrolü yok
# #============================================================================

# # Yanlış:
# def __init__(self, camera_id):
#     self.cap = cv2.VideoCapture(camera_id)  # Her zaman OpenCV kullanır

# # Doğru:
# def __init__(self, camera_id):
#     if isinstance(camera_id, int):
#         self.cap = cv2.VideoCapture(camera_id)
#     elif isinstance(camera_id, str):
#         self.cap = cv2.VideoCapture(camera_id)
#     else:
#         raise ValueError("camera_id int veya str olmalı")


# #============================================================================
# # HATA 4: Destructor'da hata riski
# #============================================================================

# # Yanlış:
# def __del__(self):
#     self.cap.release()  # self.cap None ise hata verir!

# # Doğru:
# def __del__(self):
#     if self.cap:
#         self.cap.release()
#============================================================================



# Start fonksiyonunun kullanımı
#============================================================================

    #                 start() çağrıldı
    #                       │
    #                       ▼
    #            ┌─ stream_url var mı? ─┐
    #            │                      │
    #           Evet                   Hayır
    #            │                      │
    #            ▼                      ▼
    # _start_network_stream()   ┌─ use_picamera True mu? ─┐
    #            │              │                          │
    #     success = True/False Evet                      Hayır
    #            │              │                          │
    #            ▼              ▼                          ▼
    # source_type = "stream"  _start_picamera()    _start_usb_camera()
    #                           │                          │
    #                    success = True/False       success = True/False
    #                           │                          │
    #                           ▼                          ▼
    #                source_type = "picamera"   source_type = "usb"
    #                           │                          │
    #                           └───────────┬──────────────┘
    #                                       │
    #                                       ▼
    #                            is_running = success
    #                            return success


#============================================================================

    # if self.stream_url:           # 1. Öncelik: Network stream
    #     success = self._start_network_stream()
    #     if success:
    #         self.source_type = "stream"   # Hangi kaynağı kullandığımızı kaydet


#Açıklama: stream_url varsa (None değilse), network stream kullan. Bu en yüksek önceliğe sahip çünkü RPi'den görüntü almak istiyorsanız bunu kullanırsınız.

#============================================================================

    # elif self.use_picamera:       # 2. Öncelik: PiCamera
    #     success = self._start_picamera()
    #     if success:
    #         self.source_type = "picamera"   # PiCamera kullandığımızı kaydet


#Açıklama: use_picamera True ise PiCamera kullan. Bu, stream_url yoksa ve PiCamera kullanmak istiyorsanız geçerlidir.

#============================================================================

    # else:                         # 3. Öncelik: USB/Video dosyası
    #     success = self._start_usb_camera()
    #     if success:
    #         self.source_type = "usb"      # USB kamera kullandığımızı kaydet


#Açıklama: Yukarıdakilerin hiçbiri değilse, USB kamera veya video dosyası kullan. Bu varsayılan davranıştır.    
#============================================================================






#buffer
#============================================================================

#  Buffer (Tampon Bellek) Nedir?
# Buffer, gelen verileri geçici olarak depolayan bir kuyruktu


# Buffer = 10 frame ise:
# ─────────────────────────────────────────────────────────────────
# Gerçek dünya:     [Hedef burada]
#                          ↓
# Kamera görüyor:   Frame 10 (şimdi)
#                          │
# Buffer'da bekliyor: [1][2][3][4][5][6][7][8][9][10]
#                      ↑
# Program okuyor:   Frame 1 (eski!)
#                          ↓
# Motorlara gönderilen: Frame 1'deki pozisyon (YANLIŞ!)
# ─────────────────────────────────────────────────────────────────
# Sonuç: Hedef çoktan başka yerde, motor yanlış yere dönüyor!


# self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Sadece 1 frame tut


# Buffer = 1 frame ise:
# ─────────────────────────────────────────────────────────────────
# Gerçek dünya:     [Hedef burada]
#                          ↓
# Kamera görüyor:   Frame 10 (şimdi)
#                          │
# Buffer'da:        [10]  ← Sadece en son frame
#                     ↓
# Program okuyor:   Frame 10 (GÜNCEL!)
#                          ↓
# Motorlara gönderilen: Doğru pozisyon ✓
# ─────────────────────────────────────────────────────────────────


# CAP_PROP_FRAME_WIDTH	Frame genişliği
# CAP_PROP_FRAME_HEIGHT	Frame yüksekliği
# CAP_PROP_FPS	Frame rate
# CAP_PROP_BUFFERSIZE	Buffer boyutu
# CAP_PROP_BRIGHTNESS	Parlaklık
# CAP_PROP_EXPOSURE	Pozlama


#============================================================================





# parametrelerin değiştirilmesi 
#============================================================================


# 1. YAML okunur          2. CameraCapture oluşur       3. start() çağrılır         4. Gerçek değer alınır
# ─────────────────      ───────────────────────       ─────────────────────       ────────────────────
# settings.yaml          main.py                        capture.py                   capture.py
# width: 640       ───>  CameraCapture(width=640)  ─>  self.width = 640        ─>  self.width = actual
#                                                                                   (stream'den gelen)




# # 1. YAML'da tanımlı:
# camera:
#   width: 640
#   height: 480

# # 2. main.py YAML'ı okur ve CameraCapture'a geçirir:
# self.camera = CameraCapture(
#     width=cam_cfg['width'],   # 640 (YAML'dan)
#     height=cam_cfg['height']  # 480 (YAML'dan)
# )

# # 3. capture.py __init__'te:
# def __init__(self, width=640, ...):
#     self.width = width   # 640 (main.py'den gelen)

# # 4. start() -> _start_network_stream() içinde:
# actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))  # 1280 (stream'den)
# self.width = actual_width  # ARTIK 1280! (üzerine yazıldı)


# YAML: "İstediğim değer" (başlangıç tahmini)
# Gerçek değer: "Kamera/stream ne veriyor?" (kesin doğru)


# main.py bu değeri sonra okursa:
# frame_center = self.camera.get_center()  
# → (640, 360) değil, (actual_width/2, actual_height/2) döner
# Çünkü self.width artık güncellenmiş durumda



# # main.py satır 180-185
# camera_config = CameraConfig(
#     width=cam_cfg['width'],       # ← Hâlâ YAML'dan okuyor!
#     height=cam_cfg['height'],
#     fov_horizontal=cam_cfg['fov_horizontal'],
#     fov_vertical=cam_cfg['fov_vertical']
# )
#============================================================================





# read() fonksiyonu akış şeması
#============================================================================

    #                    read() çağrıldı
    #                         │
    #                         ▼
    #           ┌─ use_picamera True ve picamera var mı? ─┐
    #           │                                          │
    #          Evet                                      Hayır
    #           │                                          │
    #           ▼                                          ▼
    # PiCamera'dan oku                          ┌─ cap var ve açık mı? ─┐
    #           │                               │                        │
    #           ▼                              Evet                    Hayır
    # RGB → BGR dönüştür                        │                        │
    #           │                               ▼                        ▼
    #           ▼                        cap.read()              return False, None
    # return True, frame                        │
    #                                           ▼
    #                                return ret, frame


# # 1. PiCamera kontrolü
# if self.use_picamera and self.picamera:
#     #  ↑ Her iki koşul da True olmalı:
#     #    - use_picamera=True (kullanıcı istedi)
#     #    - self.picamera var (başlatıldı)
    



#     frame = self.picamera.capture_array()
#     # PiCamera RGB formatında görüntü verir
#     # Ama OpenCV BGR bekler (Blue-Green-Red)
    
#     frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
#     # RGB → BGR dönüşümü yap
    
#     return True, frame  # (başarılı, görüntü)


# # 2. USB kamera veya Network stream
# elif self.cap and self.cap.isOpened():
#     #  ↑ OpenCV VideoCapture objesi var ve bağlı
    
#     ret, frame = self.cap.read()
#     # ret = True/False (başarılı mı?)
#     # frame = görüntü verisi
    
#     # Video dosyası bittiyse bilgi ver
#     if not ret and isinstance(self.camera_id, str):
#         print("[BİLGİ] Video dosyası sona erdi")
    
#     return ret, frame


# # 3. Hiçbiri aktif değilse
# return False, None  # Hata durumu

#============================================================================





# fps kontrolü
#============================================================================


# # Normal read() kullanırsan:
# while True:
#     ret, frame = camera.read()  # Olabildiğince hızlı okur
#     # İşlem yap...
    
# # Sonuç:
# # - Güçlü PC: 500+ FPS (gereksiz CPU kullanımı!)
# # - Zayıf PC: 15 FPS
# # - Tutarsız davranış





# # fps=30 ayarlandıysa:
# frame_interval = 1.0 / 30  # = 0.033 saniye (33ms)

# # Her frame arası EN AZ 33ms olmalı




# def read_with_fps_limit(self):
#     current_time = time.time()                    # Şu anki zaman
#     elapsed = current_time - self.last_frame_time  # Son frame'den bu yana geçen süre
    
#     # Çok erken mi okuyoruz?
#     if elapsed < self.frame_interval:
#         sleep_time = self.frame_interval - elapsed
#         time.sleep(sleep_time)  # Bekle!
    
#     self.last_frame_time = time.time()
#     return self.read()



#     Zaman (ms)    İşlem
# ─────────────────────────────────────────────────
# 0            read_with_fps_limit() çağrıldı
#              elapsed = 0 (ilk çağrı)
#              frame_interval = 33ms
#              elapsed < 33ms → 33ms bekle
# 33           read() çağrılır, frame alınır
             
# 40           read_with_fps_limit() çağrıldı
#              elapsed = 40 - 33 = 7ms
#              7ms < 33ms → 26ms bekle
# 66           read() çağrılır

# 70           read_with_fps_limit() çağrıldı
#              elapsed = 70 - 66 = 4ms
#              4ms < 33ms → 29ms bekle
# 99           read() çağrılır




# # settings.yaml
# camera:
#   fps: 60  # 30 yerine 60


# frame_interval = 1.0 / 60  # = 0.0166 saniye (16.6ms)
#============================================================================



# kamera fps performansı 
#============================================================================

# RPi Kamera (90 FPS)
#         │
#         ▼
#     JPEG Encode (~10ms)     ← CPU kullanır
#         │
#         ▼
#     Network Gönderim (~20-50ms)  ← Ağ gecikmesi
#         │
#         ▼
#     PC'de Decode (~5ms)
#         │
#         ▼
# Efektif FPS: 20-30 FPS





# Senaryo	Beklenen FPS	Gecikme
# 640x480, MJPEG, WiFi	25-35 FPS	100-200ms
# 640x480, MJPEG, Ethernet	30-40 FPS	50-100ms
# 1080p, MJPEG, WiFi	15-20 FPS	150-300ms
# 1080p, MJPEG, Ethernet	20-30 FPS	100-150ms





# Düşük FPS (15 FPS) + Yüksek Gecikme (200ms) = PROBLEM!

# Senaryo:
# - Hedef hızlı hareket ediyor
# - Frame 200ms gecikmeli geliyor
# - PID eski pozisyona göre hesaplıyor
# - Motor yanlış yere dönüyor
# - "Avcı" davranışı (hedefin gerisinde kalma)




# # settings.yaml - Takip sistemi için optimize
# camera:
#   width: 640        # Düşük çözünürlük = hızlı
#   height: 480
#   fps: 30           # Gerçekçi hedef
  
# # rpi_streamer.py çalıştırırken
# python rpi_streamer.py --width 640 --height 480 --fps 30 --quality 70
# #                                                          ↑ düşük kalite = hızlı
#============================================================================





# stop fonskiyonu son 3 kısım 
#============================================================================

# def __del__(self):
#     """Nesne silinirken otomatik çağrılır"""
#     self.stop()



# cam = CameraCapture()
# cam.start()

# # Program bitince veya:
# del cam  # ← __del__ otomatik çağrılır → stop() çalışır

# # Veya:
# cam = None  # ← Referans kalmadı, __del__ çağrılır





# def __enter__(self):
#     self.start()
#     return self

# def __exit__(self, exc_type, exc_val, exc_tb):
#     self.stop()


# with CameraCapture() as cam:     # 1. __init__() → 2. __enter__() → start()
#     ret, frame = cam.read()       # Normal kullanım
#     # ...
#                                   # 3. __exit__() → stop() (blok bitince)





# # Manuel yol (eski):
# cam = CameraCapture()
# cam.start()
# try:
#     # kamera işlemleri
#     pass
# finally:
#     cam.stop()  # Unutulabilir!

# # Context manager ile (yeni, güvenli):
# with CameraCapture() as cam:  # ← __enter__ çağrılır (start)
#     # kamera işlemleri
#     pass
# # ← Blok bitince __exit__ çağrılır (stop) - HATA OLSA BİLE!





# Özellik	Manuel	Context Manager
# stop()
#  unutma riski	⚠️ Var	✅ Yok
# Hata durumunda temizlik	⚠️ try/finally gerek	✅ Otomatik
# Kod uzunluğu	Uzun	Kısa





# # Güvenli kullanım:
# with CameraCapture(stream_url="http://192.168.1.100:8080/video") as cam:
#     while True:
#         ret, frame = cam.read()
#         if not ret:
#             break
#         cv2.imshow("Video", frame)
#         if cv2.waitKey(1) == ord('q'):
#             break
# # ← Buraya gelince otomatik stop() çağrılır







# def stop(self):
#     """Kamerayı durdur ve kaynakları serbest bırak"""
    
#     # 1. OpenCV VideoCapture varsa kapat
#     if self.cap:
#         self.cap.release()    # Kamerayı serbest bırak
#         self.cap = None       # Referansı temizle
#         print(f"[KAMERA] {self.source_type} kapatıldı")
    
#     # 2. PiCamera varsa kapat
#     if self.picamera:
#         self.picamera.stop()  # PiCamera'yı durdur
#         self.picamera = None  # Referansı temizle
#         print("[KAMERA] PiCamera kapatıldı")
    
#     # 3. Durumu güncelle
#     self.is_running = False





# stop() ÇAĞRILMAZSA:
# ───────────────────────────────────
# Kamera hâlâ "meşgul" olarak kalır
#     │
#     ▼
# Başka program kamerayı açamaz
#     │
#     ▼
# "Kamera kullanımda" hatası alırsın





# stop() ÇAĞRILIRSA:
# ───────────────────────────────────
# self.cap.release() → Kamera serbest
#     │
#     ▼
# Başka programlar kullanabilir ✓






# Durum	Nasıl Çağrılır
# Manuel	cam.stop()
# Program bitince	
# del
# ()
#  → 
# stop()

# with
#  bloğu bitince	
# exit
# ()
#  → 
# stop()


# Hata durumunda	
# exit
# ()
#  → 
# stop()







# if self.cap:           # None değilse
#     self.cap.release()
#     self.cap = None    # ← Önemli! İkinci kez çağrılırsa hata vermez

# cam.stop()  # İlk çağrı: self.cap.release() çalışır
# cam.stop()  # İkinci çağrı: self.cap = None, if self.cap → False, hata yok ✓


#============================================================================