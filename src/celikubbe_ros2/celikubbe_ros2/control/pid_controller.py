"""
PID Kontrolcü Modülü
Çift eksen (pan/tilt) için PID kontrol sistemi
"""


import time
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class PIDGains:
    """PID kazanç değerleri"""
    kp: float = 0.1
    ki: float = 0.01
    kd: float = 0.05


class PIDController:
    """
    PID Kontrolcü Sınıfı
    
    Formül:
        output = Kp*e + Ki*∫e*dt + Kd*(de/dt)
    
    Özellikler:
        - Anti-windup (integral sınırlama)
        - Derivative filtering (türev filtresi)
        - Output clamping (çıkış sınırlama)
    """
    
    def __init__(
        self,
        kp: float = 0.1,
        ki: float = 0.01,
        kd: float = 0.05,
        output_min: float = -100.0,
        output_max: float = 100.0,
        integral_limit: float = 50.0,
        derivative_filter: float = 0.1,
        deadband: float = 0.0
    ):
        """
        Args:
            kp: Proportional gain (oransal kazanç)
            ki: Integral gain (integral kazanç)
            kd: Derivative gain (türev kazanç)
            output_min: Minimum çıkış değeri
            output_max: Maximum çıkış değeri
            integral_limit: Anti-windup için integral sınırı
            derivative_filter: Türev filtre katsayısı (0-1, 0=filtresiz)
            deadband: Ölü bant (bu aralıkta hata 0 kabul edilir)
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self.integral_limit = integral_limit
        self.derivative_filter = derivative_filter
        self.deadband = deadband
        
        # Durum değişkenleri
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_derivative = 0.0
        self.prev_time = None
        
        # İstatistikler
        self.last_p_term = 0.0
        self.last_i_term = 0.0
        self.last_d_term = 0.0
        
    def reset(self):
        """Kontrolcüyü sıfırla"""
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_derivative = 0.0
        self.prev_time = None
        
    def set_gains(self, kp: float, ki: float, kd: float):
        """PID kazançlarını güncelle"""
        self.kp = kp
        self.ki = ki
        self.kd = kd
        
    def update(self, error: float, dt: Optional[float] = None) -> float:

#         def update(self, error: float, dt: Optional[float] = None) -> float:
# #                 ↑ GİRİŞ           ↑ GİRİŞ                    ↑ ÇIKIŞ
        """
        PID hesapla
        
        Args:
            error: Hedef - Mevcut (örn: pixel cinsinden)
            dt: Zaman farkı (None ise otomatik hesapla)
            
        Returns:
            Kontrol çıkışı
        """
        current_time = time.time()
        
        # Zaman farkını hesapla
        if dt is None:
            if self.prev_time is None:
                dt = 0.01  # İlk çalışma için varsayılan
            else:
                dt = current_time - self.prev_time
        
        self.prev_time = current_time
        
        # Çok küçük dt'yi engelle
        dt = max(dt, 0.001)
        
        # Deadband uygula
        if abs(error) < self.deadband:
            error = 0.0
        
        # Proportional term
        p_term = self.kp * error
        
        # Integral term (anti-windup ile)
        self.integral += error * dt
        self.integral = self._clamp(self.integral, -self.integral_limit, self.integral_limit)
        i_term = self.ki * self.integral
        
        # Derivative term (filtrelenmiş)
        derivative = (error - self.prev_error) / dt
        
        # Low-pass filter for derivative
        if self.derivative_filter > 0:
            derivative = (
                self.derivative_filter * derivative +
                (1 - self.derivative_filter) * self.prev_derivative
            )
        
        d_term = self.kd * derivative
        
        # Toplam çıkış
        output = p_term + i_term + d_term
        
        # Çıkışı sınırla
        output = self._clamp(output, self.output_min, self.output_max)
        
        # Durumu güncelle
        self.prev_error = error
        self.prev_derivative = derivative
        
        # İstatistikleri kaydet
        self.last_p_term = p_term
        self.last_i_term = i_term
        self.last_d_term = d_term
        
        return output
    
    def _clamp(self, value: float, min_val: float, max_val: float) -> float:
        """Değeri sınırla"""
        return max(min_val, min(value, max_val))
    
    def get_terms(self) -> Tuple[float, float, float]:
        """Son P, I, D terimlerini döndür"""
        return self.last_p_term, self.last_i_term, self.last_d_term


class DualAxisPIDController:
    """
    Çift Eksen PID Kontrolcü
    Pan ve Tilt için ayrı PID kontrolcüler
    """
    
    def __init__(
        self,
        pan_gains: Optional[PIDGains] = None,
        tilt_gains: Optional[PIDGains] = None,
        output_min: float = -100.0,
        output_max: float = 100.0,
        deadband: float = 1.0  # Derece cinsinden (PID'e artık açı giriyor)
    ):
        """
        Args:
            pan_gains: Pan ekseni PID kazançları
            tilt_gains: Tilt ekseni PID kazançları
            output_min: Minimum çıkış
            output_max: Maximum çıkış
            deadband: Ölü bant (derece) — PID'e açı cinsinden hata geldiği için derece olmalı
        """
        pan_gains = pan_gains or PIDGains()
        tilt_gains = tilt_gains or PIDGains()
        
        self.pan_pid = PIDController(
            kp=pan_gains.kp,
            ki=pan_gains.ki,
            kd=pan_gains.kd,
            output_min=output_min,
            output_max=output_max,
            deadband=deadband
        )
        
        self.tilt_pid = PIDController(
            kp=tilt_gains.kp,
            ki=tilt_gains.ki,
            kd=tilt_gains.kd,
            output_min=output_min,
            output_max=output_max,
            deadband=deadband
        )
    
    def reset(self):
        """Her iki ekseni de sıfırla"""
        self.pan_pid.reset()
        self.tilt_pid.reset()
    
    def update(
        self,
        error_x: float,
        error_y: float,
        dt: Optional[float] = None
    ) -> Tuple[float, float]:
        """
        Her iki eksen için PID hesapla
        
        Args:
            error_x: X ekseni hatası (sağ +, sol -)
            error_y: Y ekseni hatası (aşağı +, yukarı -)
            dt: Zaman farkı
            
        Returns:
            (pan_output, tilt_output)
        """
        pan_output = self.pan_pid.update(error_x, dt)
        tilt_output = self.tilt_pid.update(error_y, dt)
        
        return pan_output, tilt_output
    
    def set_pan_gains(self, kp: float, ki: float, kd: float):
        """Pan PID kazançlarını güncelle"""
        self.pan_pid.set_gains(kp, ki, kd)
    
    def set_tilt_gains(self, kp: float, ki: float, kd: float):
        """Tilt PID kazançlarını güncelle"""
        self.tilt_pid.set_gains(kp, ki, kd)
    
    def is_on_target(self, error_x: float, error_y: float, threshold: float = 10.0) -> bool:
        """
        Hedefin üzerinde mi kontrol et
        bu frame'in merkezidir
        Args:
            error_x: X hatası
            error_y: Y hatası
            threshold: Eşik değer (piksel)
        """
        return abs(error_x) < threshold and abs(error_y) < threshold


# Test kodu
if __name__ == "__main__":
    import matplotlib.pyplot as plt
    import numpy as np
    
    print("PID Controller test başlıyor...")
    
    # Simülasyon parametreleri
    dt = 0.033  # ~30 FPS
    duration = 5.0  # 5 saniye
    
    # Hedef pozisyon
    target = 0
    
    # Başlangıç pozisyonu
    position = 100  # Hedeften 100 piksel uzakta
    
    # PID kontrolcü
    pid = PIDController(
        kp=0.5,
        ki=0.1,
        kd=0.2,
        output_min=-50,
        output_max=50,
        deadband=2
    )
    
    # Kayıt listeleri
    times = []
    positions = []
    errors = []
    outputs = []
    
    t = 0
    while t < duration:
        error = target - position
        output = pid.update(error, dt)
        
        # Basit sistem dinamiği simülasyonu
        position += output * dt * 2
        
        times.append(t)
        positions.append(position)
        errors.append(error)
        outputs.append(output)
        
        t += dt
    
    # Grafik çiz
    fig, axes = plt.subplots(3, 1, figsize=(10, 8))
    
    axes[0].plot(times, positions, 'b-', label='Pozisyon')
    axes[0].axhline(y=target, color='r', linestyle='--', label='Hedef')
    axes[0].set_ylabel('Pozisyon (piksel)')
    axes[0].legend()
    axes[0].grid(True)
    
    axes[1].plot(times, errors, 'r-')
    axes[1].set_ylabel('Hata (piksel)')
    axes[1].grid(True)
    
    axes[2].plot(times, outputs, 'g-')
    axes[2].set_xlabel('Zaman (s)')
    axes[2].set_ylabel('PID Çıkışı')
    axes[2].grid(True)
    
    plt.suptitle('PID Controller Simülasyonu')
    plt.tight_layout()
    
    # Dinamik dosya yolu (hangi bilgisayarda olursa olsun çalışır)
    from pathlib import Path
    save_path = Path(__file__).parent.parent / 'tests' / 'pid_test.png'
    save_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path)
    print(f"Grafik kaydedildi: {save_path}")
    plt.show()
    
    print("Test tamamlandı!")






# proportional integral derivative
#===============================================================================


# output = Kp×e + Ki×∫e×dt + Kd×(de/dt)
#          ─┬─    ────┬───    ────┬────
#           │         │            │
#      Proportional  Integral   Derivative
#        (Oransal)  (Toplam)    (Değişim)




# self.ki = 0.01  # Integral gain


# Zaman    Hata    Integral (toplam)
# t=0      5       5
# t=1      5       10
# t=2      5       15
# t=3      5       20  ← Birikim arttı!



# I_output = Ki × Integral = 0.01 × 20 = 0.2

# "Küçük hata var ama uzun süredir var, düzeltmeliyim!"



# self.kd = 0.05  # Derivative gain


# t=0: Hata = 100
# t=1: Hata = 50   → Değişim = -50 (hızlı yaklaşıyorum)
# t=2: Hata = 25   → Değişim = -25 (hâlâ hızlı)

# D_output = Kd × Değişim = 0.05 × (-50) = -2.5

# "Çok hızlı yaklaşıyorum, fren yapmalıyım!"



# self.output_min = -100.0   # Minimum motor hızı
# self.output_max = 100.0    # Maximum motor hızı
# Motor hızı -100 ile +100 arasında sınırlandırılır.


# self.deadband = 0.0  # Ölü bant
# Hata bu değerden küçükse → "0" kabul et (titreşimi önler)



# self.derivative_filter = 0.1  # Türev filtresi
# Gürültülü sinyallerde türevi yumuşatır

# self.integral_limit = 50.0  # Anti-windup: max 50'ye kadar biriksin


# self.integral = 0.0       # Birikmiş hata toplamı
# self.prev_error = 0.0     # Önceki hata (türev için)
# self.prev_time = None     # Önceki zaman





# Terim	Ne Yapar	Çok Yüksekse
# Kp	Hata oranında tepki	Salınım
# Ki	Küçük hataları düzeltir	Overshoot
# Kd	Değişimi yavaşlatır	Yavaş tepki
#===============================================================================




# istatistik değişkenleri
#===============================================================================
# Bunlar debugging (hata ayıklama) ve monitöring (izleme) için kullanılır.



# self.last_p_term = 0.0  # Son P çıkışı
# self.last_i_term = 0.0  # Son I çıkışı
# self.last_d_term = 0.0  # Son D çıkışı


# Her 
# update()
#  çağrısında bu değerler güncellenir:

# def update(self, error):
#     p_term = self.kp * error           # P hesapla
#     i_term = self.ki * self.integral   # I hesapla
#     d_term = self.kd * derivative      # D hesapla
    
#     # İstatistikleri kaydet
#     self.last_p_term = p_term   # ← Kaydedildi
#     self.last_i_term = i_term
#     self.last_d_term = d_term
    
#     output = p_term + i_term + d_term
#     return output






# print(f"P: {pid.last_p_term}, I: {pid.last_i_term}, D: {pid.last_d_term}")
# # Çıktı: P: 15.0, I: 2.5, D: -3.2

# # "Aha! I terimi çok düşük, Ki'yi artırmalıyım"



# # Her frame'de kaydet
# p_values.append(pid.last_p_term)
# i_values.append(pid.last_i_term)
# d_values.append(pid.last_d_term)

# # Sonra grafik çiz
# plt.plot(p_values, label="P")
# plt.plot(i_values, label="I")
# plt.plot(d_values, label="D")


# Eğer:
# - P çok büyük → motor sallanıyor → Kp'yi düşür
# - I çok yavaş artıyor → uzun süre hata kalıyor → Ki'yi artır
# - D negatif ve büyük → çok fren yapıyor → Kd'yi düşür


# #===============================================================================



#update

#===============================================================================

#def update(self, error: float, dt: Optional[float] = None) -> float:



# Parametre	Tip	Açıklama
# error
# float	Hedef ile mevcut konum arasındaki fark (piksel)
# dt	float (opsiyonel)	İki frame arası süre (saniye)
# Döndürür	float	Motor hızı (-100 ile +100 arası)


# error = 150   # Hedef 150 piksel sağda
# output = pid.update(error)
# output = 25.5 → "Motoru sağa 25.5 hızla döndür"




#time.time() → Örnek: 1707523456.789

# if dt is None:                    # dt verilmediyse otomatik hesapla
#     if self.prev_time is None:    # İlk çağrı mı?
#         dt = 0.01                 # Varsayılan: 10ms
#     else:
#         dt = current_time - self.prev_time  # Önceki çağrıdan bu yana geçen süre



# İlk çağrı:     prev_time = None  →  dt = 0.01
# İkinci çağrı:  current_time = 1000.033
#                prev_time = 1000.000
#                dt = 0.033 (33ms = ~30 FPS)




# self.prev_time = current_time   # Şimdiki zamanı kaydet (bir sonraki çağrı için)

# dt = max(dt, 0.001)             # dt en az 0.001 olsun (0'a bölme hatasını engelle)




# Deadband (Ölü Bant) (Satır 113-115)

# if abs(error) < self.deadband:   # Hata çok küçükse
#     error = 0.0                  # "Hedeftesin" kabul et


# Neden? Motor sürekli titremesini engeller.


# deadband = 5 piksel ise:

# Hata = 3 piksel  →  "0 kabul et, motor durabilir"
# Hata = 10 piksel →  Gerçek hata, motor dönsün





# P Terimi (Satır 117-118)

# p_term = self.kp * error

# Kp = 0.1
# error = 100

# p_term = 0.1 × 100 = 10

# "100 piksel uzaktasın → 10 birim hareket et"





# I Terimi (Satır 120-123)


# self.integral += error * dt    # Hatayı zamana göre topla

# Önceki integral = 5
# error = 10
# dt = 0.033

# Yeni integral = 5 + (10 × 0.033) = 5.33

# self.integral = self._clamp(self.integral, -self.integral_limit, self.integral_limit)
# Anti-windup: Integral -50 ile +50 arasında kalır (taşmayı engeller)


# i_term = self.ki * self.integral

# Ki = 0.01
# integral = 20

# i_term = 0.01 × 20 = 0.2





# D Terimi (Satır 125-135)


# derivative = (error - self.prev_error) / dt   # Hatanın değişim hızı


# Önceki hata = 100
# Şimdiki hata = 80
# dt = 0.033

# derivative = (80 - 100) / 0.033 = -20 / 0.033 = -606

# "Hata saniyede 606 piksel hızla azalıyor (yaklaşıyorum!)"



# # Low-pass filter (gürültü azaltma)
# if self.derivative_filter > 0:
#     derivative = (
#         self.derivative_filter * derivative +           # Yeni değerin %10'u
#         (1 - self.derivative_filter) * self.prev_derivative  # Eski değerin %90'ı
#     )



# Neden filtre? Gürültülü sensör verilerini yumuşatır.
# d_term = self.kd * derivative


# Kd = 0.05
# derivative = -606

# d_term = 0.05 × (-606) = -30.3

# "Çok hızlı yaklaşıyorum, fren yap!"





# Toplam Çıkış (Satır 137-141)

# output = p_term + i_term + d_term


# p_term = 10
# i_term = 0.2
# d_term = -30.3

# output = 10 + 0.2 + (-30.3) = -20.1

# output = self._clamp(output, self.output_min, self.output_max)

# Çıkış -100 ile +100 arasında sınırlandırılır.


# output = -20.1 → sınırlar içinde, değişmez
# output = 150   → 100'e düşürülür
# output = -200  → -100'e yükseltilir







# Durum Güncelleme (Satır 143-150)


# self.prev_error = error           # Şimdiki hatayı kaydet (sonraki D için)
# self.prev_derivative = derivative  # Şimdiki türevi kaydet (filtre için)

# # İstatistikleri kaydet (debug için)
# self.last_p_term = p_term
# self.last_i_term = i_term
# self.last_d_term = d_term

# return output   # Motor hızını döndür!









# Giriş:
#   error = 100 piksel
#   dt = 0.033 saniye
  
# Hesaplama:
#   P: 0.1 × 100 = 10
#   I: 0.01 × 3.3 = 0.033  (integral = 100×0.033 = 3.3)
#   D: 0.05 × 3030 = 151.5  (derivative = 100/0.033)
  
#   output = 10 + 0.033 + 151.5 = 161.5
#   output = clamp(161.5, -100, 100) = 100  ← Sınırlandı!
  
# Çıkış:
#   return 100 (maksimum hız sağa)









# update() fonksiyonunu satır satır detaylı açıkladım:

# Zaman hesaplama - İki frame arası süreyi ölçer
# Deadband - Küçük hataları sıfır kabul eder (titreşimi önler)
# P terimi - Kp × error (hata oranında tepki)
# I terimi - Ki × integral (birikmiş hataları toplar)
# D terimi - Kd × derivative (değişim hızına göre fren)
# Toplam çıkış - P + I + D, sınırlandırılmış
# Anlaşıldı mı? Devam edelim mi? Sıradaki konular:

# DualAxisPIDController (pan ve tilt için çift eksenli PID)
# motor_calculator.py (PID çıkışını motor açısına çevirme)
# serial_comm.py (Arduino ile haberleşme)


#===============================================================================






#===============================================================================

        # pan_gains: Optional[PIDGains] = None,
        # tilt_gains: Optional[PIDGains] = None,




# pan_gains: Optional[PIDGains] = None
# Bu demek ki: 
# PIDGains
#  objesi VER, ya da hiç verme (None).


# @dataclass
# class PIDGains:
#     kp: float = 0.1
#     ki: float = 0.01
#     kd: float = 0.05



# main.py'de:
# pan_gains = PIDGains(kp=0.15, ki=0.01, kd=0.08)   # ← PIDGains objesi oluştur
# tilt_gains = PIDGains(kp=0.15, ki=0.01, kd=0.08)

# pid = DualAxisPIDController(
#     pan_gains=pan_gains,      # ← PIDGains objesi verildi
#     tilt_gains=tilt_gains
# )



# None olursa ne olur?
# DualAxisPIDController.__init__ içinde (satır 185-186):
# pan_gains = pan_gains or PIDGains()   # None ise → varsayılan PIDGains oluştur
# tilt_gains = tilt_gains or PIDGains()



# # Senaryo 1: Değer verilmiş
# pid = DualAxisPIDController(pan_gains=PIDGains(kp=0.5, ki=0.1, kd=0.2))
# # pan_gains = PIDGains(kp=0.5, ki=0.1, kd=0.2) ✓

# # Senaryo 2: None (verilmemiş)
# pid = DualAxisPIDController()  # pan_gains=None
# # pan_gains = None or PIDGains() → PIDGains(kp=0.1, ki=0.01, kd=0.05) (varsayılan)
#===============================================================================




#===============================================================================
# ┌────────────────────────────────┐
# │                                │
# │         ┏━━━━━━━━━━┓           │
# │         ┃ threshold┃           │
# │         ┃  (10px)  ┃           │
# │         ┃    +     ┃           │ ← Bu alan içinde → True
# │         ┃  merkez  ┃           │
# │         ┗━━━━━━━━━━┛           │
# │                         ●      │ ← Bu dışarıda → False
# │                                │
# └────────────────────────────────┘





# Durum 1: Nesne uzakta (error büyük)
# ┌────────────────────────────────┐
# │                                │
# │         +              ●       │  error_x = 150, error_y = 30
# │       merkez         nesne     │  is_on_target → False
# │                                │  Motor: "Sağa dön!"
# └────────────────────────────────┘

# Durum 2: Nesne merkezde (error küçük)
# ┌────────────────────────────────┐
# │                                │
# │            ●                   │  error_x = 3, error_y = 5
# │         merkez                 │  is_on_target → True ✓
# │                                │  Motor: "Dur, hedeftesin!"
# └────────────────────────────────┘
#===============================================================================