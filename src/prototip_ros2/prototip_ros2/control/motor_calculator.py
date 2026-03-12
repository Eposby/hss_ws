"""
Motor Hesaplama Modülü
Hibrit Sistem: Step Motor (Pan) + DC Motor/Enkoder (Tilt)
Piksel hatasından step veya encoder count dönüşümü
"""

import math
from typing import Tuple
from dataclasses import dataclass


#===============================================================================

# !!! en alttki yorum satırlarına göre motor ayarlarını yap

#===============================================================================


@dataclass
class MotorConfig:
    """Motor yapılandırması (Step veya DC/Enkoder)"""
    motor_type: str = "stepper"          # "stepper" veya "dc_encoder"
    
    # Ortak Parametreler
    gear_ratio: float = 1.0              # Dişli oranı (örn: 1:90 redüktör için 90.0)
    min_angle: float = -90.0             # Minimum açı (derece)
    max_angle: float = 90.0              # Maximum açı (derece)
    max_speed: float = 1000.0            # Max hız (step/sn veya count/sn)
    acceleration: float = 500.0          # İvme
    
    # Step Motor Parametreleri
    steps_per_revolution: int = 200      # 1.8° motor için 200
    microstepping: int = 16              # Microstepping faktörü
    
    # DC Motor + Enkoder Parametreleri
    encoder_ppr: int = 11                # Pulse Per Revolution (Motor milindeki ham değer)
    # Not: Quadrature enkoderler için toplam count = ppr * gear_ratio * 4


@dataclass  
class CameraConfig:
    """Kamera yapılandırması"""
    width: int = 640                     # Görüntü genişliği
    height: int = 480                    # Görüntü yüksekliği
    fov_horizontal: float = 60.0         # Yatay görüş açısı (derece)
    fov_vertical: float = 45.0           # Dikey görüş açısı (derece)


class MotorCalculator:
    """
    Motor Açı Hesaplama Sınıfı (Hibrit: Step + DC)
    
    Piksel → Açı → Step/Count dönüşümleri yapar
    """
    
    def __init__(
        self,
        pan_motor: MotorConfig = None,
        tilt_motor: MotorConfig = None,
        camera: CameraConfig = None
    ):
        """
        Args:
            pan_motor: Pan motoru yapılandırması
            tilt_motor: Tilt motoru yapılandırması
            camera: Kamera yapılandırması
        """
        self.pan_motor = pan_motor or MotorConfig(motor_type="stepper")
        self.tilt_motor = tilt_motor or MotorConfig(motor_type="dc_encoder")
        self.camera = camera or CameraConfig()
        
        # Dönüşüm katsayıları (steps_per_degree veya counts_per_degree)
        self.pan_ratio = 0.0
        self.tilt_ratio = 0.0
        
        # Hesaplanmış değerler
        self._calculate_resolutions()
        
        # Mevcut pozisyonlar (derece)
        self.current_pan_angle = 0.0
        self.current_tilt_angle = 0.0
        
    def _calculate_resolutions(self):
        """Çözünürlük değerlerini hesapla"""
        
        # --- PAN MOTORU (Genelde Step) ---
        if self.pan_motor.motor_type == "stepper":
            total_steps = (
                self.pan_motor.steps_per_revolution *
                self.pan_motor.microstepping *
                self.pan_motor.gear_ratio
            )
            self.pan_ratio = total_steps / 360.0  # steps per degree
            print(f"[MOTOR] Pan (Step): {self.pan_ratio:.2f} step/derece")
            
        elif self.pan_motor.motor_type == "dc_encoder":
            # Quadrature enkoder: PPR * 4 * GearRatio
            total_counts = (
                self.pan_motor.encoder_ppr * 4 * 
                self.pan_motor.gear_ratio
            )
            self.pan_ratio = total_counts / 360.0 # counts per degree
            print(f"[MOTOR] Pan (DC): {self.pan_ratio:.2f} count/derece")

        # --- TILT MOTORU (JGY-370 DC) ---
        if self.tilt_motor.motor_type == "stepper":
            total_steps = (
                self.tilt_motor.steps_per_revolution *
                self.tilt_motor.microstepping *
                self.tilt_motor.gear_ratio
            )
            self.tilt_ratio = total_steps / 360.0
            print(f"[MOTOR] Tilt (Step): {self.tilt_ratio:.2f} step/derece")
            
        elif self.tilt_motor.motor_type == "dc_encoder":
            # JGY-370 örneği: 11 PPR, 1:90 Redüktör
            # Toplam count = 11 * 4 * 90 = 3960 count/tur
            total_counts = (
                self.tilt_motor.encoder_ppr * 4 * 
                self.tilt_motor.gear_ratio
            )
            self.tilt_ratio = total_counts / 360.0
            print(f"[MOTOR] Tilt (DC): {self.tilt_ratio:.2f} count/derece")
        
        # Kamera
        self.degrees_per_pixel_x = self.camera.fov_horizontal / self.camera.width
        self.degrees_per_pixel_y = self.camera.fov_vertical / self.camera.height
        
        print(f"[MOTOR] Kamera: {self.degrees_per_pixel_x:.4f}°/px (X), {self.degrees_per_pixel_y:.4f}°/px (Y)")
    
    def pixel_error_to_angle(
        self,
        error_x: int,
        error_y: int
    ) -> Tuple[float, float]:
        """
        Piksel hatasını açıya çevir
        
        Args:
            error_x: Hedef merkezden kaç piksel uzakta? (Örn: +100 piksel sağda)
            error_y: Hedef merkezden kaç piksel yukarıda/aşağıda? (Örn: -50 piksel yukarıda)

        Returns:
            (pan_angle, tilt_angle) derece cinsinden
            Daha önce hesapladığımız degrees_per_pixel (bir pikselin gerçek hayattaki karşılığı) değeri ile çarpar.
            pan_angle = error_x * 0.093 deg/px
            tilt_angle = error_y * 0.093 deg/px

            Motorların dönmesi gereken GERÇEK AÇI değerini verir.
            Örn: "Pan motoru 9.3 derece sağa, Tilt motoru 4.6 derece yukarı dönmeli."
        """
        pan_angle = error_x * self.degrees_per_pixel_x
        tilt_angle = error_y * self.degrees_per_pixel_y
        return pan_angle, tilt_angle
    

# pixel_error_to_angle
# : Piksel -> Derece (Kameradan Fiziğe)
# angle_to_units
# : Derece -> Motor Birimi (Fizikten Donanıma)



    def angle_to_units(
        self,
        pan_angle: float,
        tilt_angle: float
    ) -> Tuple[int, int]:
        """Açıyı motor birimine (step veya count) çevir

            Girdi:
                pan_angle: Pan motoru 9.3 derece dönmeli.
                tilt_angle: Tilt motoru 4.6 derece dönmeli.

            İşlem (Çeviri):
                Her eksen için kendi "oranı" (ratio) ile çarpar.
                Pan (Step): 9.3 derece * 8.88 step/derece = 82.5 step
                Tilt (Count): 4.6 derece * 11 count/derece = 50.6 count

        """
        pan_units = int(round(pan_angle * self.pan_ratio))
        tilt_units = int(round(tilt_angle * self.tilt_ratio))
        return pan_units, tilt_units
    
    def calculate_target_position(
        self,
        error_x: int,
        error_y: int
    ) -> Tuple[float, float]:
        """Hedef pozisyonu hesapla
        
            🧠 Mantık: "Şu anki konumum + Hatam = Gitmem gereken yer"
        
            current_pan_angle: Motor şu an kaç derecede duruyor? (Örn: 30° sağa bakıyor)
            delta_pan: Hedef ne kadar uzakta? (Örn: +10° daha sağda)
            target_pan: Sonuç (30° + 10° = 40°).
        
            📝 Örnek Senaryo
                Durum 1: Kule 30 derecede duruyor.
                Kamera: "Hedefim 10 derece sağımda" dedi (delta_pan = 10).
                Hesap: 30 + 10 = 40.
                Komut: Kuleyi 40. dereceye çevir.
                Sonuç: Kule 40'a gelir. Artık hedef merkezdedir (delta_pan = 0).
        ⚠️ Eğer Sadece delta_pan Kullansaydık?
        Kod sadece delta_pan gönderseydi, motor sürekli "10 derece dön, 10 derece dön" derdi ama "Nereden itibaren?" sorusunu bilemezdi. target_pan, motorun dünya üzerindeki sabit adresidir.
        """
        delta_pan, delta_tilt = self.pixel_error_to_angle(error_x, error_y)
        
        target_pan = self.current_pan_angle + delta_pan
        target_tilt = self.current_tilt_angle + delta_tilt
        
        # Sınırla
        """
            Not: Bizim yeni hibrit sistemde     
                serial_comm.py
            için RELATIVE (Göreceli) hareket kullanıyoruz (<P:steps>). Yani aslında Arduino'ya "40'a git" demiyoruz, "olduğun yerden 10 daha git" diyoruz.

            main.py
            -> 
            MotorCommand
            -> 
            serial_comm.py
            : "50 adım sağa git" (Relative)
            Bu hesap (target_pan) ise 
            MotorCalculator
            içinde sanal olarak şu an nerede olduğumuzu takip etmek için kullanılır. Böylece limitlere (min_angle, max_angle) çarpıp çarpmayacağımızı kontrol edebiliriz.
        
        """
        target_pan = self._clamp(target_pan, self.pan_motor.min_angle, self.pan_motor.max_angle)
        target_tilt = self._clamp(target_tilt, self.tilt_motor.min_angle, self.tilt_motor.max_angle)
        
        return target_pan, target_tilt
    

    
    def calculate_movement(
        self,
        error_x: int,
        error_y: int
    ) -> dict:
        """Tam hareket hesaplaması"""
        # Açıları hesapla
        delta_pan, delta_tilt = self.pixel_error_to_angle(error_x, error_y)
        target_pan, target_tilt = self.calculate_target_position(error_x, error_y)
        
        # Motor birimlerine çevir (Step veya Count)
        pan_units, tilt_units = self.angle_to_units(delta_pan, delta_tilt)
        
        # Hız hesabı (basit orantılı)
        pan_speed = min(abs(pan_units) * 10, self.pan_motor.max_speed)
        tilt_speed = min(abs(tilt_units) * 10, self.tilt_motor.max_speed)
        
        return {
            "delta_pan_degrees": delta_pan,
            "delta_tilt_degrees": delta_tilt,
            "target_pan_degrees": target_pan,
            "target_tilt_degrees": target_tilt,
            "pan_units": pan_units,       # Step veya Count
            "tilt_units": tilt_units,     # Step veya Count
            "pan_speed": pan_speed,
            "tilt_speed": tilt_speed,
            "current_pan": self.current_pan_angle,
            "current_tilt": self.current_tilt_angle
        }
    
    def update_position(self, pan_angle: float, tilt_angle: float):
        """Mevcut pozisyonu güncelle"""
        self.current_pan_angle = pan_angle
        self.current_tilt_angle = tilt_angle
    
    def reset_position(self):
        """Pozisyonu sıfırla (home)"""
        self.current_pan_angle = 0.0
        self.current_tilt_angle = 0.0
        
    def _clamp(self, value: float, min_val: float, max_val: float) -> float:
        """Değeri sınırla"""
        return max(min_val, min(value, max_val))
    
    def get_resolution_info(self) -> dict:
        """Çözünürlük bilgilerini döndür"""
        return {
            "pan_ratio": self.pan_ratio,
            "tilt_ratio": self.tilt_ratio,
            "degrees_per_pixel_x": self.degrees_per_pixel_x,
            "degrees_per_pixel_y": self.degrees_per_pixel_y
        }


# Test kodu
if __name__ == "__main__":
    print("Motor Calculator (Hibrit) test başlıyor...")
    print("=" * 60)
    
    # 1. Pan Motoru (Step - NEMA 17)
    pan_config = MotorConfig(
        motor_type="stepper",
        steps_per_revolution=200,
        microstepping=16,
        gear_ratio=1.0
    )
    
    # 2. Tilt Motoru (DC - JGY-370)
    tilt_config = MotorConfig(
        motor_type="dc_encoder",
        encoder_ppr=11,          # JGY-370 arka encoder
        gear_ratio=90.0,         # 1:90 redüktör varsayalım
        max_speed=5000           # count/saniye
    )
    
    camera_config = CameraConfig(
        width=640,
        height=480,
        fov_horizontal=60.0,
        fov_vertical=45.0
    )
    
    # Hesaplayıcı oluştur
    calculator = MotorCalculator(
        pan_motor=pan_config,
        tilt_motor=tilt_config,
        camera=camera_config
    )
    
    print("\n" + "=" * 50)
    print("Çözünürlük Bilgileri:")
    info = calculator.get_resolution_info()
    for key, value in info.items():
        print(f"  {key}: {value:.6f}")
    
    print("\n" + "=" * 50)
    print("Test Senaryoları:")
    
    # Test 1: Merkezdeki nesne
    print("\nSenaryo 1: Nesne merkezde")
    result = calculator.calculate_movement(0, 0)
    print(f"  Delta Pan: {result['delta_pan_degrees']:.4f}°")
    print(f"  Delta Tilt: {result['delta_tilt_degrees']:.4f}°")
    print(f"  Pan Units: {result['pan_units']}")
    print(f"  Tilt Units: {result['tilt_units']}")
    
    # Test 2: Nesne sağda
    print("\nSenaryo 2: Nesne 100 piksel sağda, 50 piksel yukarıda")
    result = calculator.calculate_movement(100, -50)
    print(f"  Delta Pan: {result['delta_pan_degrees']:.4f}°")
    print(f"  Delta Tilt: {result['delta_tilt_degrees']:.4f}°")
    print(f"  Pan Units: {result['pan_units']}")
    print(f"  Tilt Units: {result['tilt_units']}")
    print(f"  Target Pan: {result['target_pan_degrees']:.4f}°")
    print(f"  Target Tilt: {result['target_tilt_degrees']:.4f}°")
    
    # Test 3: Ekstrem değerler
    print("\nSenaryo 3: Nesne en köşede (320, 240 piksel uzakta)")
    result = calculator.calculate_movement(320, 240)
    print(f"  Delta Pan: {result['delta_pan_degrees']:.4f}°")
    print(f"  Delta Tilt: {result['delta_tilt_degrees']:.4f}°")
    print(f"  Pan Units: {result['pan_units']}")
    print(f"  Tilt Units: {result['tilt_units']}")
    
    print("\n" + "=" * 50)
    print("Test tamamlandı!")




# dataclasses motor ve kamera

#===============================================================================

#  MotorConfig Sabitleri (Motor Özellikleri)
# steps_per_revolution (Tur Başına Adım): Motorun bir tam tur (360°) dönmesi için kaç adım atması gerektiğini ifade eder. Genellikle 200 adım (1.8°/adım) veya 400 adım (0.9°/adım) olur.
# Formül: 360 / Adım Açısı
# microstepping (Mikro Adımlama): Motor sürücüsü (TMC2208 vb.) bir tam adımı daha küçük parçalara bölerek hassasiyeti artırır.
# Örnek: 16 mikro adım = 1 tam adımı 16'ya böl.
# Sonuç: Daha pürüzsüz hareket, daha yüksek çözünürlük.
# gear_ratio (Dişli Oranı): Motor mili ile hareket eden eksen arasındaki dişli/kayış oranı.
# 1.0: Doğrudan bağlı (1 tur motor = 1 tur eksen).
# 4.0: 4 tur motor = 1 tur eksen (Tork artar, hız düşer).
# max_speed & acceleration: Motorun fiziksel sınırları (adım/saniye ve adım/saniye²).



# 2. CameraConfig Sabitleri (Kamera Özellikleri)
# fov_horizontal (Yatay Görüş Açısı): Kameranın yatayda kaç derecelik bir alanı gördüğüdür.
# Standart lens: ~60°
# Geniş açı: ~120°
# Telefoto: ~30°
# fov_vertical: Dikey görüş açıs




# Adım 1: Çözünürlük Hesabı (Derece/Piksel) Kameranın bir pikselinin kaç dereceye denk geldiğini buluruz.

# degrees_per_pixel_x = fov_horizontal / width
# # Örnek: 60° / 640px = 0.09375°/piksel


# Adım 2: Hata Açısı Hesabı Piksel hatasını dereceye çeviririz.

# angle_error_x = pixel_error_x * degrees_per_pixel_x
# # Örnek: 50px hata * 0.09375 = 4.6875° (Motor bu kadar dönmeli)



# Adım 3: Adım Sayısı Hesabı Dönülmesi gereken açıyı motor adımına çeviririz.

# steps_per_degree = (steps_per_rev * microstepping * gear_ratio) / 360
# # Örnek: (200 * 16 * 1) / 360 = 8.88 adım/derece

# motor_steps = angle_error_x * steps_per_degree
# # Örnek: 4.6875° * 8.88 = 41.6 adım ≈ 42 adım


# Sonuç: Kamera "Hedef 50 piksel sağda" der, hesaplayıcı "Motoru 42 adım sağa döndür" der.






# Model	Sensör	Yatay FOV (Horizontal)	Dikey FOV (Vertical)	Not
# Camera Module v1	OV5647	~53.5°	~41.4°	Eski, 5MP
# Camera Module v2	IMX219	~62.2°	~48.8°	En yaygın, 8MP
# Camera Module v3 (Standart)	IMX708	~66°	~41°	Yeni, 12MP, HDR
# Camera Module v3 (Wide/Geniş)	IMX708	~102°	~67°	Geniş açı lensli
# HQ Camera (Yüksek Kalite)	IMX477	Lense Bağlı	Lense Bağlı	C/CS mount lens takılır
# Global Shutter	IMX296	~66°	~41°	Hızlı hareket için
#===============================================================================





#_calculate_resolution_info
#===============================================================================

# Motor ve Kamera Çözünürlük Hesaplamalarının Mantığı:

# Bu fonksiyon, sistemin fiziksel dünyayı nasıl algıladığını ve buna nasıl tepki vereceğini matematiksel olarak tanımlar.

# 1. Motor Çözünürlüğü (Adım/Derece)
# Motorun 1 derece dönebilmesi için kaç adım atması gerektiğini hesaplarız.

# Formül: (Motor Adımı * Mikro Adım * Dişli Oranı) / 360
# Örnek:
# Motor: 200 adım/tur (1.8°)
# Mikro Adım: 16 (Sürücü ayarı)
# Sonuç: (200 * 16) / 360 = 8.88 adım/derece
# Anlamı: Sistemi 1 derece döndürmek için motora ~9 adım attırmalıyız.





# 2. Kamera Çözünürlüğü (Derece/Piksel)
# Kameradaki tek bir pikselin gerçek dünyada kaç derecelik bir açıya denk geldiğini hesaplarız.

# Formül: Görüş Açısı (FOV) / Ekran Genişliği
# Örnek:
# FOV: 60 derece
# Genişlik: 640 piksel
# Sonuç: 60 / 640 = 0.09375 derece/piksel
# Anlamı: Hedef ekranda 1 piksel kayarsa, bu gerçekte 0.09 derece hareket etmiştir.




# 3. Büyük Resim: Pikselden Harekete
# Bu iki hesaplama birleştiğinde sistem şu şekilde çalışır:

# Kamera: "Hedef sağa doğru 100 piksel kaydı."
# Dönüşüm: 100 piksel * 0.09 = 9 derece (Hedef gerçekte 9 derece sağda).
# Motor Komutu: 9 derece * 8.88 = 80 adım
# Eylem: Motor sağa 80 adım atar ve hedef tam merkeze gelir.
# Bu hesaplama sayesinde PID kontrolcüsü rastgele sayılarla değil, gerçek fiziksel büyüklüklerle çalışır.


#===============================================================================








# MOTOR AYARLARI
#===============================================================================

# 1. gear_ratio (Dişli Oranı)
# Ne anlama gelir? Motor milinin kaç tur attığında kule/eklemin 1 tur attığını söyler.
# Nereden bulunur?
# Eğer doğrudan bağlıysa: 1.0 (Motor 1 tur = Kule 1 tur)
# Kayış-Kasnak varsa: Büyük Kasnak Diş Sayısı / Küçük Kasnak Diş Sayısı (Örn: 60/20 = 3.0)
# Redüktörlü Motor (JGY-370 vb.) kullanıyorsanız: Satın aldığınız modelin üzerinde yazar (Örn: 1:90 ise 90.0, 1:600 ise 600.0).
# 2. min_angle ve max_angle
# Ne anlama gelir? Robotun kafasını çevirebileceği fiziksel limitler (derece cinsinden).
# Neye göre değiştirilir? Kabloların dolanmaması veya mekaniğin bir yere çarpmaması için.
# Pan (Sağ-Sol) için genelde -180 ile 180 (veya 0 ile 360).
# Tilt (Yukarı-Aşağı) için genelde -45 (yer) ile 90 (gökyüzü) arası.
# 3. max_speed ve acceleration
# Ne anlama gelir?
# max_speed: Motorun en yüksek hızı. Çok yüksek yaparsanız motor tork kaybeder ve adım kaçırır (viykler ama dönmez).
# acceleration: Hızlanma yumuşaklığı. Düşük değer = Ağır kalkış (Kamyon), Yüksek değer = Ani kalkış (Spor araba).
# Neye göre değiştirilir? Deneme-yanılma ile. Motor titriyorsa veya ses çıkarıp dönmüyorsa düşürün.
# 4. steps_per_revolution (Sadece Step Motor)
# Ne anlama gelir? Motorun iç yapısındaki mıknatıs sayısı.
# Nereden bulunur?
# %99 ihtimalle standart NEMA 17 motorlar 200 adımdır (1.8°).
# Bazı hassas motorlar 400 adımdır (0.9°). Motorun etiketinde yazar.
# 5. microstepping (Sadece Step Motor)
# Ne anlama gelir? Sürücü kartı üzerindeki jumper/switch ayarıdır. Bir adımı daha küçük parçalara böler.
# Nereden bulunur? A4988 veya DRV8825 sürücüsünün altındaki 3 minik jumper'ın (MS1, MS2, MS3) nasıl takıldığına göre değişir.
# Hepsi takılıysa (A4988): 16
# Hepsi takılıysa (DRV8825): 32
# Hiçbiri takılı değilse: 1 (Tam Adım)
# 6. encoder_ppr (Sadece DC Motor + Enkoder)
# Ne anlama gelir? Motorun arkasındaki siyah diskin üzerindeki delik (mıknatıs) sayısı. "Pulse Per Revolution".
# Nereden bulunur? Motorun veri sayfasında (datasheet) yazar.
# Standart JGY-370 motorlarda genelde 11 PPR veya 7 PPR'dır.

#===============================================================================







# calculate_resolution_info
#===============================================================================
#STEP MOTOR HESABI
# total_steps = (
#     self.pan_motor.steps_per_revolution * # Motor 1 tur için kaç adım atar? (Genelde 200)
#     self.pan_motor.microstepping *        # Sürücü her adımı kaça bölüyor? (Genelde 16)
#     self.pan_motor.gear_ratio             # Mekanik dişli oranı ne? (Genelde 1.0)
# )
# self.pan_ratio = total_steps / 360.0      # 1 derece için kaç adım lazım?


# Örnek:

# Motor: 200 adım
# Sürücü: 16 mikro adım
# Dişli: 1.0 (Direkt)
# Hesap: 200 * 16 * 1.0 = 3200 adım (Tam bir tur yani 360 derece için).
# Sonuç: 3200 / 360 = 8.88 adım.
# Anlamı: "Robot kafasını 1 derece döndürmek istiyorsan, motora 9 adım at de."




#DC MOTOR HESABI

# total_counts = (
#     self.pan_motor.encoder_ppr *      # Tek turda kaç delik/mıknatıs geçiyor? (Genelde 11)
#     4 *                               # Quadrature okuma (x4 hassasiyet)
#     self.pan_motor.gear_ratio         # Redüktör oranı (JGY-370'de çok yüksek, örn: 90)
# )
# self.pan_ratio = total_counts / 360.0 # 1 derece için enkoder kaç saymalı?


# Neden 4 ile çarpıyoruz? Enkoderlerde A ve B diye iki sensör vardır.

# A yandı
# B yandı
# A söndü
# B söndü Bu 4 durumu da sayarak hassasiyeti 4 katına çıkarırız. Buna Quadrature Encoding denir.
# Örnek:

# Enkoder: 11 PPR
# Redüktör: 1:90
# Hesap: 11 * 4 * 90 = 3960 count (Kule 1 tam tur attığında enkoder 3960 kere sinyal verir).
# Sonuç: 3960 / 360 = 11 count.
# Anlamı: "Robot kafasını 1 derece döndürmek istiyorsan, enkoder sayısı 11 artana kadar motoru döndür."

# Enkoder mantığını ve A-B sensörlerini en basit haliyle, "Kapı ve İki Bekçi" benzetmesiyle anlatayım.

# Bir döner kapı düşünün. Bu kapıdan insanlar geçiyor. Bizim amacımız:

# Kaç kişi geçti? (Mesafe/Açı)
# İçeri mi girdiler, dışarı mı çıktılar? (Yön)
# Standart Sayaç (Tek Sensör) - Yetersiz
# Kapıya tek bir bekçi (Sensör A) koysak:

# Biri geçerken bekçi "Düt!" der.
# Sorun: Bu kişi içeri mi girdi, dışarı mı çıktı bilemeyiz. Sadece "biri hareket etti" deriz. Robot kafasını sağa mı çevirdi sola mı anlayamayız.
# Quadrature Enkoder (İki Sensör: A ve B) - Çözüm
# Kapıya yan yana iki bekçi (Sensör A ve Sensör B) koyuyoruz. Amaçları sırayla sinyal vermek.

# Disk dönerken delikler bu sensörlerin önünden geçer. Ancak sensörler öyle yerleştirilmiştir ki, delik önce birine, az sonra diğerine gelir.

# Senaryo 1: SAĞA Dönüş (İçeri Giriş)

# Önce Bekçi A kişiyi görür: "A Yandı!" (1-0)
# Sonra Bekçi B de görür: "B de Yandı!" (1-1)
# Bekçi A kişiyi kaybeder: "A Söndü!" (0-1)
# Bekçi B kişiyi kaybeder: "B Söndü!" (0-0)
# Sıralama: A önce, B sonra. Mikroişlemci der ki: "Ha, demek ki SAĞA dönüyoruz."

# Senaryo 2: SOLA Dönüş (Dışarı Çıkış)

# Önce Bekçi B kişiyi görür: "B Yandı!" (0-1)
# Sonra Bekçi A da görür: "A da Yandı!" (1-1)
# Bekçi B kişiyi kaybeder: "B Söndü!" (1-0)
# Bekçi A kişiyi kaybeder: "A Söndü!" (0-0)
# Sıralama: B önce, A sonra. Mikroişlemci der ki: "Ha, demek ki SOLA dönüyoruz."

# Neden 4 ile Çarpıyoruz?
# Tek bir delik geçerken yukarıdaki 4 olay yaşanır:

# A Yan (1. Adım)
# B Yan (2. Adım)
# A Sön (3. Adım)
# B Sön (4. Adım)
# Normalde 1 delik = 1 adım diyebilirdik. Ama bu 4 aşamayı da sayarsak hassasiyetimiz 4 katına çıkar.

# 11 delikli bir diskte, sadece delikleri sayarsanız 11 adım olur.
# Bu 4 olayı da sayarsanız 11 * 4 = 44 adım olur. Robotunuz 4 kat daha hassas durabilir.


#===============================================================================

