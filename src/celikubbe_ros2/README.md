# Çelikkubbe Hava Savunma Sistemi (ROS 2)

Bu paket, TEKNOFEST Hava Savunma Sistemleri Yarışması için tasarlanmış bağımsız (distributed) ROS 2 mimarisini içermektedir. Sistem, kameralı nesne tespiti (YOLOv8), Dual-Axis PID tabanlı kontrolcü, özel arayüz tasarımı (PyQt6 GUI) ve donanım haberleşmesi olmak üzere 6 farklı düğüm (node) barındırır.

## Mimari
Yazılım iki ana paketten oluşur:
1. `celikubbe_msgs`: Kullanılan özel ROS 2 arayüzlerini (`TargetInfo`, `MotorSetpoint`, `SetPhase`, `EngageTarget`) içerir.
2. `celikubbe_ros2`: Aşağıdaki düğümleri içeren yürütücü uygulamadır:
   - **`kamera_dugumu.py`**: Görüntü kaynağını okur ve ROS 2 formatında yayınlar.
   - **`tespit_dugumu.py`**: YOLOv8 modeli ile nesne tanır; ayrıca HSV destekli alan taraması ile renk analizi yaparak (Kırmızı=Düşman, Mavi=Dost) sistemi besler.
   - **`kontrol_dugumu.py`**: Doğrulanmış hedefleri takip etmek için gerekli pan ve tilt ekseni komutlarını PID ile hesaplar.
   - **`donanim_dugumu.py`**: Üretilen motor komutlarını donanımınıza (ESP32 vb.) seri port üzerinden iletir.
   - **`gorev_dugumu.py`**: Sistemin beynidir (*Mission Control*). `Action` ve `Service` mekanizmalarını kullanarak otonom Aşama Kontrolü (State Machine), puanlama ve atış karar algoritmasını yönetir.
   - **`arayuz_dugumu.py`**: PyQt6 tabanlı, "Glassmorphism" temalı yüksek kalite görev izleme panelidir.

## Kurulum ve Bağımlılıklar

> [!WARNING]
> ROS 2 Humble'ın sahip olduğu sistem paketleri, **NumPy 2.x** sürümüyle binary (C-API) uyumsuzluğu barındırır. Bu yüzden kurulumu yaparken NumPy'ın 1.x sürümlerinde kalması **çok önemlidir**.

Pip bağımılıklarını yüklemek için aşağıdaki komutu kullanın:
```bash
pip install "numpy<2" "opencv-python<4.9.0" "opencv-contrib-python<4.9.0" ultralytics pyserial PyQt6
```

Çalışma alanınızı (`hss_ws`) inşa etmek için çalışma alanınızın kökünde (örneğin `~/hss_ws/`):
```bash
colcon build --packages-select celikubbe_msgs celikubbe_ros2
```

## Çalıştırma
Sistemi tek adımda başlatmak için (Arayüz dahil tüm node'lar açılacaktır):
```bash
source install/setup.bash
ros2 launch celikubbe_ros2 celikubbe_launch.py
```
