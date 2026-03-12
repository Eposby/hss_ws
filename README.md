# Hava Savunma Sistemi (Air Defense System) - HSS

Teknofest Hava Savunma Sistemi projesi, hava araçlarını tespit ve takip etmek için tasarlanmış bir otonom hava savunma sistemidir. Proje ROS2 framework'ü kullanılarak geliştirilmiş olup, gerçek zamanlı görüntü işleme, durum yönetimi ve Gazebo simülasyonu içermektedir.

## 📋 Proje Özeti

HSS (Hava Savunma Sistemi), aşağıdaki yetenekleri içerir:

- **Görüntü İşleme**: YOLO tabanlı hedef tespiti
- **Durum Yönetimi**: Üç aşamalı (Stage) durum makinesi
- **Motor Kontrolü**: PID kontrolcü ile hassas motor kontrolü
- **Gazebo Simülasyonu**: Test ve geliştirme için simülasyon ortamı
- **Arduino İletişimi**: Seri haberleşme ile donanım kontrolü

---

## 📁 Klasör Yapısı

```
hss_ws/
├── src/                              # Kaynak kodlar
│   ├── hava_savunma_pkg/             # Ana ROS2 paketi (Python)
│   │   ├── hava_savunma_pkg/         # Paket modülü
│   │   │   ├── nodes/                # ROS2 düğümleri
│   │   │   │   └── balloon_detector.py       # Hedef tespit düğümü
│   │   │   ├── state_machine/        # Durum makinesi mantığı
│   │   │   │   ├── main.py                   # Durum makinesi ana giriş
│   │   │   │   ├── machine.py                # Durum makinesi sınıfı
│   │   │   │   ├── state_idle.py             # Boş durum
│   │   │   │   ├── state_scanning.py         # Tarama durumu
│   │   │   │   ├── state_detected.py         # Tespit durumu
│   │   │   │   ├── stage1_states.py          # Aşama 1 durumları
│   │   │   │   ├── stage2_states.py          # Aşama 2 durumları
│   │   │   │   └── stage3_states.py          # Aşama 3 durumları
│   │   │   ├── utils/                # Yardımcı fonksiyonlar
│   │   │   ├── launch.py             # ROS2 launch dosyası
│   │   │   └── test_balloon.py        # Test dosyası
│   │   ├── launch/                   # ROS2 launch dosyaları
│   │   │   └── hss_system.launch.py   # Sistem başlatma dosyası
│   │   ├── config/                   # Konfigürasyon dosyaları
│   │   ├── package.xml               # ROS2 paket tanımı
│   │   ├── setup.py                  # Python paket kurulum
│   │   └── setup.cfg                 # Kurulum konfigürasyonu
│   │
│   ├── hss_gazebo_sim/               # Gazebo simülasyon paketi (C++)
│   │   ├── src/                      # C++ kaynak kodları
│   │   ├── include/                  # C++ başlık dosyaları
│   │   ├── launch/                   # Simülasyon launch dosyaları
│   │   │   └── simulation.launch.py   # Gazebo simülasyonunu başlatır
│   │   ├── models/                   # Gazebo 3D modelleri
│   │   ├── worlds/                   # Gazebo simülasyon dünyaları
│   │   ├── CMakeLists.txt            # CMake build tanımı
│   │   └── package.xml               # ROS2 paket tanımı
│   │
│   ├── prototip/                     # Prototip implementasyon
│   │   ├── main.py                   # Ana giriş dosyası
│   │   ├── improved.py               # İyileştirilmiş versiyon
│   │   ├── camera/                   # Kamera yönetimi
│   │   ├── detection/                # Hedef tespiti
│   │   ├── control/                  # Motor kontrolü
│   │   ├── communication/            # Arduino iletişimi
│   │   ├── firmware/                 # Arduino firmware
│   │   ├── models/                   # YOLO modelleri
│   │   ├── config/                   # YAML konfigürasyon dosyaları
│   │   ├── requirements.txt          # Python bağımlılıkları
│   │   └── tests/                    # Test dosyaları
│   │
│   └── steel_dome_gui/               # GUI arayüzü
│
├── build/                            # Build çıktıları (otomatik oluşturulur)
├── install/                          # Install edilmiş paketler
├── log/                              # Build logları
├── tutorial_notes/                   # Proje notları ve tutoriallar
└── README.md                         # Bu dosya
```

---

## 📦 Bileşenlerin Açıklaması

### 1. **hava_savunma_pkg** (Ana Paket)
Durum makinesi tabanlı hava savunma sistemi paketi.

**Klasör Yapısı:**
- `nodes/balloon_detector.py`: Hedef tespiti yapan ROS2 düğümü
- `state_machine/`: Üç aşamalı durum yönetim sistemi
  - Idle → Scanning → Detected → Stage1 → Stage2 → Stage3
- `utils/`: Yardımcı fonksiyonlar
- `launch/hss_system.launch.py`: Tüm sistemi başlatır

### 2. **hss_gazebo_sim** (Gazebo Simülasyonu)
Gazebo simülasyonu içeren C++ ROS2 paketi.

**Özellikler:**
- Gazebo ortamında sistem simülasyonu
- 3D modeller ve dünyalar
- ROS-Gazebo köprüsü (ros_gz_bridge integrate)

### 3. **prototip** (Prototip Implementasyon)
Doğrudan Arduino ve kamera kontrolü için prototip kod.

**Modüller:**
- `camera/`: Kamera feed işleme
- `detection/`: YOLO ile hedef tespiti
- `control/`: PID motor kontrolü
- `communication/`: Arduino seri haberleşim

---

## 🛠️ Gereksinimler ve Kurulum

### Sistem Gereksinimleri
- **İşletim Sistemi**: Ubuntu 20.04 LTS veya sonrası
- **ROS2**: Foxy, Galactic, Humble veya Jazzy (önerilir: Humble)
- **Python**: 3.8+
- **C++ Derleyicisi**: GCC 9 veya sonrası

### Bağımlılıkların Kurulması

#### 1. ROS2 Kurulumu (Eğer yüklü değilse)
```bash
# Ubuntu 22.04 için ROS2 Humble
sudo apt update
sudo curl -sSL https://raw.githubusercontent.com/ros/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
sudo apt update
sudo apt install ros-humble-desktop
```

#### 2. Bağımlılıkları Kurulum
```bash
# ROS2 temel araçları
sudo apt install -y ros-humble-ros2-bag ros-humble-rqt* ros-humble-gazebo* ros-humble-rviz*

# Gazebo simülasyonu için
sudo apt install -y gazebo ros-humble-ros-gz* ros-humble-ros-gz-bridge

# Python paketleri
pip install numpy opencv-python pyyaml scipy

# Colcon build tool
sudo apt install -y python3-colcon-common-extensions

# Kaynak ortam
source /opt/ros/humble/setup.bash
```

---

## 🚀 Kurulum ve Build

### 1. Repoyu Klonla
```bash
cd ~
git clone https://github.com/yourusername/hss_ws.git
cd hss_ws
```

### 2. Ortamı Kur
```bash
# ROS2 ortamını source'la
source /opt/ros/humble/setup.bash

# Workspace'i build et
colcon build
```

### 3. Setup Scriptini Çalıştır
```bash
source install/setup.bash
```

Her Terminal açtığında bu komutu çalıştırmanız gerekir. Otomatikleştirmek için:
```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
echo "source ~/hss_ws/install/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

---

## ▶️ Çalıştırma Talimatları

### Seçenek 1: Tam Sistemi Çalıştır (ROS2)
```bash
source install/setup.bash
ros2 launch hava_savunma_pkg hss_system.launch.py
```

### Seçenek 2: Gazebo Simülasyonu
```bash
source install/setup.bash
ros2 launch hss_gazebo_sim simulation.launch.py
```

### Seçenek 3: Prototip (Doğrudan Python)
```bash
cd src/prototip
python main.py
```

### Seçenek 4: Durum Makinesi
```bash
ros2 run hava_savunma_pkg balloon_detector
```

---

## 🔧 Konfigürasyon

### YAML Konfigürasyon Dosyaları
`src/prototip/config/` altında bulunan YAML dosyaları kullanılır.

**Önemli Not**: 
- YAML dosyası program başlangıcında bir kere okunur
- Çalışma sırasında YAML değişikliği etkili olmaz
- Yeni ayarları uygulamak için programı yeniden başlatınız

```yaml
# Örnek konfigürasyon
camera:
  device: 0
  resolution: [640, 480]
  fps: 30

detection:
  model: "yolo-weights.pt"
  confidence: 0.5

motor:
  pid_kp: 1.0
  pid_ki: 0.5
  pid_kd: 0.2
```

---

## 📊 Sistem Mimarisi

```
Kamera Input
    ↓
[Hedef Tespit - YOLO]
    ↓
[Durum Makinesi]
    ├─ idle
    ├─ scanning
    ├─ detected
    └─ stages (1, 2, 3)
    ↓
[Motor Kontrolü - PID]
    ↓
[Arduino İletişimi]
    ↓
Motor Çıkışı
```

---

## 📝 Sık Sorulan Sorular

### Build Hatası: "Package not found"
```bash
# Build klasörünü temizle and yeniden build et
rm -rf build/ install/ log/
colcon build
```

### ROS2 Komutları Tanınmıyor
```bash
# Setup scriptini source'la
source install/setup.bash
```

### Kamera Erişimi Hatası
```bash
# Kamera izinlerini kontrol et
sudo usermod -a -G video $USER
# Logout ve login yap
```

### Arduino Bağlantı Hatası
```bash
# Seri port izinlerini kontrol et
sudo usermod -a -G dialout $USER
# Logout ve login yap
```

---

## 🐛 Troubleshooting

### Gazebo Başlamazsa
```bash
# Gazebo'yu temizle
killall gzserver
killall gzclient
pkill -f gazebo

# Yeniden başla
ros2 launch hss_gazebo_sim simulation.launch.py
```

### ROS2 Node Başlamıyorsa
```bash
# ROS2 demon'u kontrol et
ros2 daemon stop
ros2 daemon start

# İlgili node'u debug mode'da çalıştır
ROS_LOG_DIR=/tmp ros2 run hava_savunma_pkg balloon_detector --ros-args --log-level debug
```

---

## 📚 Kaynaklar

- [ROS2 Resmi Dokümantasyonu](https://docs.ros.org/en/humble/)
- [Gazebo Simülasyonu](https://gazebosim.org/)
- [Colcon Build Tool](https://colcon.readthedocs.io/)
- [YOLOv8 Dokumentasyonu](https://docs.ultralytics.com/)

---

## 📄 Lisans

MIT Lisansı altında yayınlanmaktadır. Detay için [LICENSE](LICENSE) dosyasına bakınız.

---
