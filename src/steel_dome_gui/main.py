import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class CelikKubbeArayuz(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ÇELİK KUBBE - Hava Savunma Sistemi Kontrol Paneli")
        self.setGeometry(100, 100, 1280, 720) # HD Boyut

        # Ana Widget ve Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # --- ÜST PANEL (Başlık ve Durum) ---
        header_frame = QFrame()
        header_frame.setObjectName("HeaderFrame")
        header_layout = QHBoxLayout(header_frame)
        
        self.title_label = QLabel("ÇELİK KUBBE SAVUNMA SİSTEMİ")
        self.title_label.setObjectName("TitleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.status_label = QLabel("SİSTEM DURUMU: BEKLEMEDE")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        header_layout.addWidget(self.title_label, stretch=3)
        header_layout.addWidget(self.status_label, stretch=1)
        main_layout.addWidget(header_frame)

        # --- ORTA PANEL (Kamera ve Radar) ---
        content_layout = QHBoxLayout()
        
        # Kamera Alanı (Sol)
        self.camera_frame = QFrame()
        self.camera_frame.setObjectName("CameraFrame")
        camera_layout = QVBoxLayout(self.camera_frame)
        self.camera_label = QLabel("KAMERA GÖRÜNTÜSÜ YOK")
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        camera_layout.addWidget(self.camera_label)
        
        # Radar Alanı (Sağ)
        self.radar_frame = QFrame()
        self.radar_frame.setObjectName("RadarFrame")
        radar_layout = QVBoxLayout(self.radar_frame)
        self.radar_label = QLabel("RADAR VERİSİ YOK")
        self.radar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        radar_layout.addWidget(self.radar_label)

        content_layout.addWidget(self.camera_frame, stretch=6) # Kamera daha geniş
        content_layout.addWidget(self.radar_frame, stretch=4) # Radar daha dar
        main_layout.addLayout(content_layout, stretch=8)

        # --- ALT PANEL (Kontroller) ---
        controls_frame = QFrame()
        controls_frame.setObjectName("ControlsFrame")
        controls_layout = QHBoxLayout(controls_frame)

        self.btn_arm = QPushButton("SİSTEMİ KUR")
        self.btn_arm.setObjectName("BtnArm")
        
        self.btn_fire = QPushButton("ATEŞLE")
        self.btn_fire.setObjectName("BtnFire")
        self.btn_fire.setEnabled(False) # Başlangıçta pasif

        self.btn_exit = QPushButton("ÇIKIŞ")
        self.btn_exit.setObjectName("BtnExit")
        self.btn_exit.clicked.connect(self.close)

        controls_layout.addWidget(self.btn_arm)
        controls_layout.addWidget(self.btn_fire)
        controls_layout.addStretch() # Butonları sola yasla
        controls_layout.addWidget(self.btn_exit)

        main_layout.addWidget(controls_frame, stretch=1)

        # Buton Bağlantıları
        self.btn_arm.clicked.connect(self.sistemi_kur)
        self.btn_fire.clicked.connect(self.atesle)

    def sistemi_kur(self):
        self.status_label.setText("SİSTEM DURUMU: AKTİF - HEDEF ARANIYOR")
        self.status_label.setStyleSheet("color: #00adb5; font-weight: bold;")
        self.btn_fire.setEnabled(True)
        self.btn_fire.setStyleSheet("background-color: #e74c3c; color: white;")

    def atesle(self):
        self.status_label.setText("DURUM: ATEŞLENDİ! HEDEF İMHA EDİLİYOR")
        self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 16px;")

def apply_stylesheet(app):
    dark_stylesheet = """
    QMainWindow {
        background-color: #1e1e1e;
    }
    QLabel {
        color: #eeeeee;
        font-family: 'Segoe UI', 'Roboto', sans-serif;
        font-size: 14px;
    }
    #TitleLabel {
        font-size: 24px;
        font-weight: bold;
        color: #00adb5;
        letter-spacing: 2px;
    }
    #StatusLabel {
        font-size: 14px;
        font-weight: bold;
        color: #ffcc00;
        border: 1px solid #ffcc00;
        padding: 5px;
        border-radius: 4px;
    }
    QFrame#HeaderFrame, QFrame#ControlsFrame {
        background-color: #2b2b2b;
        border: 1px solid #393e46;
        border-radius: 8px;
    }
    QFrame#CameraFrame, QFrame#RadarFrame {
        background-color: #000000;
        border: 2px solid #00adb5;
        border-radius: 8px;
    }
    QPushButton {
        background-color: #393e46;
        color: #eeeeee;
        border: none;
        padding: 10px 20px;
        font-size: 14px;
        font-weight: bold;
        border-radius: 4px;
    }
    QPushButton:hover {
        background-color: #00adb5;
        color: #1e1e1e;
    }
    QPushButton:pressed {
        background-color: #007f85;
    }
    QPushButton#BtnFire {
        background-color: #4a1c1c;
        color: #a0a0a0;
    }
    QPushButton#BtnExit {
        background-color: #393e46;
        border: 1px solid #e74c3c;
        color: #e74c3c;
    }
    QPushButton#BtnExit:hover {
        background-color: #e74c3c;
        color: white;
    }
    """
    app.setStyleSheet(dark_stylesheet)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_stylesheet(app)
    pencere = CelikKubbeArayuz()
    pencere.show()
    sys.exit(app.exec())
