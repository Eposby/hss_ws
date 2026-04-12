# Çelikkubbe Hava Savunma Sistemi (ROS 2)

Bu paket, TEKNOFEST Hava Savunma Sistemleri Yarışması için tasarlanmış bağımsız (distributed) ROS 2 mimarisini içermektedir. Sistem, kameralı nesne tespiti (YOLOv8), Dual-Axis PID tabanlı kontrolcü, özel arayüz tasarımı (PyQt6 GUI) ve donanım haberleşmesi olmak üzere 6 farklı düğüm (node) barındırır.

## Mimari
Yazılım iki ana paketten oluşur:
1. `celikkubbe_msgs`: Kullanılan özel ROS 2 arayüzlerini (`TargetInfo`, `MotorSetpoint`, `SetPhase`, `EngageTarget`) içerir.
2. `celikkubbe_ros2`: Aşağıdaki düğümleri içeren yürütücü uygulamadır:
   - **`kamera_dugumu.py`**: Görüntü kaynağını okur ve ROS 2 formatında yayınlar.
   - **`tespit_dugumu.py`**: YOLOv8 ile nesne tanır. Buna ek olarak; pin-hole kamera modeli ile hedef menzili tahmini yapar, bağımsız bir balon sınır kutusu (bbox) çizer, balon hariç gövde bölgesinin renk analizini (HSV) yaparak dost/düşman ayrımını hedefe ekler ve sahada tespit edilen tüm hedeflerin listesini yayınlar.
   - **`kontrol_dugumu.py`**: Doğrulanmış hedefleri takip etmek için gerekli pan ve tilt ekseni komutlarını PID ile hesaplar.
   - **`donanim_dugumu.py`**: Üretilen motor komutlarını donanımınıza (ESP32 vb.) seri port üzerinden iletir.
   - **`gorev_dugumu.py`**: Sistemin beynidir (*Mission Control*). Otonom Aşama Kontrolü (State Machine) ve menzil/zaman tabanlı dinamik atış karar algoritmasını yönetir. Araçların 15 metrelik kapalı döngü engelleri (bariyer) arkasına girmesi durumunu zaman-aşımı yönetimiyle kompanse eder. Ayrıca tespit edilen hedefin Arayüz üzerinden çizilen yasaklı atış bölgeleri (No-Fire Zone) içinde olup olmadığını denetler.
   - **`arayuz_dugumu.py`**: PyQt6 tabanlı, "Glassmorphism" temalı yüksek kalite görev izleme panelidir. Sağ tıklayıp sürükleme yöntemiyle ekrana **Atışa Yasak Bölge (NFZ)** çizme, manuel mouse-aim taret yönlendirme, sistem telemetrisi görüntüleme imkanı sağlar.

## Kurulum ve Bağımlılıklar

> [!WARNING]
> ROS 2 Humble'ın sahip olduğu sistem paketleri, **NumPy 2.x** sürümüyle binary (C-API) uyumsuzluğu barındırır. Bu yüzden kurulumu yaparken NumPy'ın 1.x sürümlerinde kalması **çok önemlidir**.

Pip bağımılıklarını yüklemek için aşağıdaki komutu kullanın:
```bash
pip install "numpy<2" "opencv-python<4.9.0" "opencv-contrib-python<4.9.0" ultralytics pyserial PyQt6
```

Çalışma alanınızı (`hss_ws`) inşa etmek için çalışma alanınızın kökünde (örneğin `~/hss_ws/`):
```bash
colcon build --packages-select celikkubbe_msgs celikkubbe_ros2
```

## Çalıştırma
Sistemi tek adımda başlatmak için (Arayüz dahil tüm node'lar açılacaktır):
```bash
source install/setup.bash
ros2 launch celikkubbe_ros2 celikkubbe_launch.py
```
