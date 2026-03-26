# Çelikkubbe Hava Savunma Sistemi (HSS)

Teknofest Hava Savunma Sistemleri yarışması için geliştirilmiş, ROS 2 (Humble) tabanlı, dağıtık (distributed) ve gerçek zamanlı otonom çalışan bir hava savunma sistemidir. YOLOv8 ile görsel hedef tespiti, PID ile yatay/dikey eksen kontrolü ve PyQt6 tabanlı gelişmiş bir arayüze sahiptir.

---

## 📋 Proje Özeti

Çelikkubbe HSS, aşağıdaki yetenekleri içerir:

- **Görüntü İşleme**: YOLOv8 tabanlı derin öğrenme ile hedef tespiti ve HSV algoritması ile dost/düşman renk sınıflandırması.
- **Durum Yönetimi (State Machine)**: Otonom hedef arama, nişan alma, onay bekleme ve ateşleme takibi yapabilen, Aşama 1, 2 ve 3 yarışma kurallarına entegre görev makinesi.
- **Motor Kontrolü**: Dual-Axis PID (Pan-Tilt) kontrolcü ve piksel hata-açı dönüştürücüsü ile hassas hedef takibi.
- **Gelişmiş Arayüz (GUI)**: ROS 2 ile tam entegre, PyQt6 ile yazılmış, şeffaf (Glassmorphism) temalı, telemetri ve canlı video feed ekranı barındıran kontrol paneli.
- **Standartlaştırılmış ROS İletişimi**: Özel oluşturulmuş ROS 2 mesajları (`TargetInfo`, `MotorSetpoint`), Servisleri (`SetPhase`) ve Eylem (Action) sunucuları (`EngageTarget`).

---

## 📁 Klasör Yapısı

Sistem, iki ana ROS 2 paketinden oluşmaktadır:

```text
hss_ws/
├── src/                                   
│   ├── celikubbe_msgs/                    # ROS 2 Mesaj, Servis ve Eylem Paketleri
│   │   ├── msg/
│   │   │   ├── TargetInfo.msg             # Kapsamlı hedef bilgi mesajı (renk, güven skoru vs.)
│   │   │   ├── MotorSetpoint.msg          # Pan/Tilt adımları ve hedef hızlar
│   │   │   └── MotorFeedback.msg          # Güncel açı, adım ve konum geribildirimleri
│   │   ├── srv/
│   │   │   └── SetPhase.srv               # Yarışma aşamasını seçme servisi
│   │   └── action/
│   │       └── EngageTarget.action        # Hedefe kilitlenme ve ateşleme süreci eylemi
│   │
│   ├── celikubbe_ros2/                    # ROS 2 Düğüm (Node) Paketi
│   │   ├── celikubbe_ros2/
│   │   │   ├── kamera_dugumu.py           # Kamera akışını okur, topic'e yazar
│   │   │   ├── tespit_dugumu.py           # YOLOv8 ve Renk algılama
│   │   │   ├── kontrol_dugumu.py          # PID ve Motor açı hesaplamaları
│   │   │   ├── donanim_dugumu.py          # Seri port / Mikrodenetleyici iletişimi
│   │   │   ├── gorev_dugumu.py            # Ana Sistem Görev Yöneticisi (State Machine)
│   │   │   └── arayuz_dugumu.py           # PyQt6 ROS 2 Arayüzü (GUI)
│   │   ├── launch/
│   │   │   └── celikubbe_launch.py        # Tüm sistemi çalıştıran konfigürasyon dosyası
│   │   └── config/
│   │       └── params.yaml                # PID, YOLO ve Kamera için parametreler
│   │
│   ├── hava_savunma_pkg/                  # (Eski - Deprecated) Tekil script yapısı
│   ├── hss_gazebo_sim/                    # Gazebo Simülasyonu
│   └── prototip/                          # (Eski - Deprecated) İlkel test kodları
└── README.md
```

---

## �️ Bağımlılıklar ve Kurulum

Sistem **ROS 2 Humble** (Ubuntu 22.04 LTS) kullanılarak geliştirilmiştir.

### 1. Ekran Çökmelerini (Numpy x OpenCV) Önleme
ÖNEMLİ: ROS 2 Humble üzerindeki `cv_bridge`, standart olarak Numpy 1.x C-API yapısına göre derlenmiştir. Numpy 2.0 veya OpenCV'nin çok güncel sürümlerinin sistemde olması `<AttributeError: _ARRAY_API not found>` hatasına sebep olur. Lütfen Numpy ve OpenCV'yi aşağıdaki sürümlere kilitleyin:

```bash
pip install "numpy<2" "opencv-python<4.9.0" "opencv-contrib-python<4.9.0"
```

### 2. Gerekli Python Paketleri
PyQt6 ve YOLOv8 için gerekenler:
```bash
pip install ultralytics pyserial PyQt6
```

### 3. Sistemi Derleme (Colcon Build)
Aşağıdaki komutlarla çalışma alanınızdaki Çelikkubbe paketlerini derleyip ortama bağlayın:
```bash
cd ~/hss_ws
colcon build --packages-select celikubbe_msgs celikubbe_ros2
source install/setup.bash
```

*(Not: Her yeni SSH oturumunda `source install/setup.bash` yapmayı unutmayın veya `~/.bashrc` dosyanıza ekleyin).*

---

## 🚀 Sistemi Çalıştırma (Quick Start)

Tasarladığımız tüm Düğümleri (Kamera, Tespit, Kontrol, Donanım, Görev Yöneticisi ve Arayüz) eş zamanlı olarak `launch` dosyasıyla başlatabilirsiniz:

```bash
ros2 launch celikubbe_ros2 celikubbe_launch.py
```

Bu kod çalıştırıldığında ROS 2 ağı arka planda aktive edilecek ve **ÇELİK KUBBE SAVUNMA SİSTEMİ** isimli arayüz penceresi karşınıza otomatik açılacaktır. 

Arayüz üzerinden:
- **Canlı Kamera Görüntüsü** izleyebilir,
- Hedeflenen nesnenin türü, menzili, rengi ve **Durum Makinesi evresini** kontrol edebilir,
- Aşama 1, 2 veya 3 modlarına geçirebilir,
- E-Stop (Acil Durdurma) veya Ateşleme tetiklemelerini yapabilirsiniz.

---

## � Mimari Detaylar

1. **İletişim Altyapısı**: ROS 2 Topic'leri (kamera/ham_goruntu, tespit/hedef_bilgisi, donanim/motor_geri_bildirim vs.) hızı kontrol ederken, kritik sistem kararları `SetPhase` Service Client'i ve hata takibini yapabilen `EngageTarget` Action Server'i üzerinden yapılır.
2. **PID Algoritması**: Hedefin kameradaki piksel sapmaları hesaplanarak kamera FOV (Field of View) açılarına dönüştürülür. Doğrusal hareket için her bir pan ve tilt ekseninde Dual-Axis PID hesaplaması yapılır.
3. **Dost-Düşman Ayrımı (IFF)**: YOLOv8 ile Bounding Box çıkarılan hedefin içi HSV renk uzayı dönüşümünden geçirilerek baskın renk tespitiyle ayrılır. Mavi renkler tespit edilse bile angajmana geçilmez (Dost kuvvet atlanır).

---
**Geliştiren:** Mert | Tasarlandı: 2026 TEKNOFEST HSS Yarışması
