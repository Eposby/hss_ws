import sys
import threading
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QImage, QPixmap, QFont
from std_msgs.msg import String, Int32, Bool
from sensor_msgs.msg import Image
from celikubbe_msgs.msg import TargetInfo, MotorFeedback
from celikubbe_msgs.srv import SetPhase
from cv_bridge import CvBridge

class ROS2Thread(threading.Thread):
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.daemon = True
        
    def run(self):
        rclpy.spin(self.node)


class Signaler(QObject):
    image_signal = pyqtSignal(np.ndarray)
    motor_signal = pyqtSignal(MotorFeedback)
    target_signal = pyqtSignal(TargetInfo)
    durum_signal = pyqtSignal(str)
    puan_signal = pyqtSignal(int)


class ArayuzDugumu(Node):
    def __init__(self, signaler: Signaler):
        super().__init__('arayuz_dugumu')
        self.signaler = signaler
        self.bridge = CvBridge()
        
        # Subscribers
        self.img_sub = self.create_subscription(Image, '/tespit/isaretli_goruntu', self.image_callback, 10)
        self.motor_sub = self.create_subscription(MotorFeedback, '/donanim/motor_geri_bildirim', self.motor_callback, 10)
        self.target_sub = self.create_subscription(TargetInfo, '/tespit/hedef_bilgisi', self.target_callback, 10)
        self.durum_sub = self.create_subscription(String, '/gorev/durum', self.durum_callback, 10)
        self.puan_sub = self.create_subscription(Int32, '/gorev/puan', self.puan_callback, 10)
        
        # Publishers
        self.operator_pub = self.create_publisher(String, '/arayuz/operator_komutu', 10)
        self.estop_pub = self.create_publisher(Bool, '/arayuz/acil_dur', 10)
        
        # Clients
        self.phase_client = self.create_client(SetPhase, '/gorev/asama_sec')

    def image_callback(self, msg: Image):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        self.signaler.image_signal.emit(frame)
        
    def motor_callback(self, msg: MotorFeedback):
        self.signaler.motor_signal.emit(msg)
        
    def target_callback(self, msg: TargetInfo):
        self.signaler.target_signal.emit(msg)
        
    def durum_callback(self, msg: String):
        self.signaler.durum_signal.emit(msg.data)
        
    def puan_callback(self, msg: Int32):
        self.signaler.puan_signal.emit(msg.data)

    def set_phase(self, phase_id: int):
        if self.phase_client.wait_for_service(timeout_sec=1.0):
            req = SetPhase.Request()
            req.phase = phase_id
            future = self.phase_client.call_async(req)
            # GUI runs asynchronously, we won't block it
        else:
            self.get_logger().error("Aşama seçme servisi hazır değil!")

    def send_estop(self, state: bool):
        msg = Bool()
        msg.data = state
        self.estop_pub.publish(msg)

    def send_fire_cmd(self):
        msg = String()
        msg.data = "ates_istegi"
        self.operator_pub.publish(msg)


class CelikKubbeGUI(QMainWindow):
    def __init__(self, ros_node: ArayuzDugumu, signaler: Signaler):
        super().__init__()
        self.node = ros_node
        self.signaler = signaler
        
        self.init_ui()
        self.connect_signals()
        self.estop_active = False

    def init_ui(self):
        self.setWindowTitle("ÇELİK KUBBE - Premium Hava Savunma UI")
        self.setGeometry(100, 100, 1280, 720)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # ÜST PANEL
        header_frame = QFrame()
        header_frame.setObjectName("HeaderFrame")
        header_layout = QHBoxLayout(header_frame)
        
        title_label = QLabel("🛡 ÇELİK KUBBE SAVUNMA SİSTEMİ")
        title_label.setObjectName("TitleLabel")
        
        self.global_status_label = QLabel("DURUM: BEKLENİYOR")
        self.global_status_label.setObjectName("GlobalStatus")
        
        header_layout.addWidget(title_label, stretch=3)
        header_layout.addWidget(self.global_status_label, stretch=1)
        main_layout.addWidget(header_frame)

        # ORTA PANEL (Kamera ve Bilgi Paneli)
        middle_layout = QHBoxLayout()
        
        # Kamera Ekranı
        self.camera_frame = QLabel("KAMERA BAĞLANTISI BEKLENİYOR...")
        self.camera_frame.setObjectName("CameraFrame")
        self.camera_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_frame.setMinimumSize(640, 480)
        middle_layout.addWidget(self.camera_frame, stretch=2)

        # Bilgi Paneli (Sağ)
        info_layout = QVBoxLayout()
        
        # Telemetri
        telemetry_frame = QFrame()
        telemetry_frame.setObjectName("TelemetryFrame")
        t_layout = QVBoxLayout(telemetry_frame)
        t_layout.addWidget(QLabel("📊 SİSTEM TELEMETRİ", objectName="HeaderLabel"))
        self.lbl_pan_tilt = QLabel("Pan: 0.0°  Tilt: 0.0°")
        self.lbl_range = QLabel("Menzil: 0.0m")
        t_layout.addWidget(self.lbl_pan_tilt)
        t_layout.addWidget(self.lbl_range)
        info_layout.addWidget(telemetry_frame)

        # Hedef Bilgisi
        target_frame = QFrame()
        target_frame.setObjectName("TargetFrame")
        tgt_layout = QVBoxLayout(target_frame)
        tgt_layout.addWidget(QLabel("🎯 HEDEF BİLGİSİ", objectName="HeaderLabel"))
        self.lbl_target_type = QLabel("Tip: - | Renk: -")
        self.lbl_target_conf = QLabel("Güven: 0.00")
        self.lbl_target_status = QLabel("Durum: BEKLENİYOR")
        tgt_layout.addWidget(self.lbl_target_type)
        tgt_layout.addWidget(self.lbl_target_conf)
        tgt_layout.addWidget(self.lbl_target_status)
        info_layout.addWidget(target_frame)
        
        # State Machine & Puan
        state_frame = QFrame()
        state_frame.setObjectName("StateFrame")
        s_layout = QVBoxLayout(state_frame)
        s_layout.addWidget(QLabel("📌 GÖREV DURUMU", objectName="HeaderLabel"))
        self.lbl_state = QLabel("State: BEKLE")
        self.lbl_score = QLabel("🏆 PUAN: 0", objectName="ScoreLabel")
        s_layout.addWidget(self.lbl_state)
        s_layout.addWidget(self.lbl_score)
        info_layout.addWidget(state_frame)

        middle_layout.addLayout(info_layout, stretch=1)
        main_layout.addLayout(middle_layout, stretch=10)

        # ALT PANEL (Kontroller)
        controls_frame = QFrame()
        controls_frame.setObjectName("ControlsFrame")
        controls_layout = QHBoxLayout(controls_frame)

        self.btn_phase1 = QPushButton("AŞAMA 1 (MANUEL)")
        self.btn_phase2 = QPushButton("AŞAMA 2 (SÜRÜ)")
        self.btn_phase3 = QPushButton("AŞAMA 3 (HAREKETLİ)")
        
        self.btn_fire = QPushButton("🔫 ATEŞLE")
        self.btn_fire.setObjectName("BtnFire")
        
        self.btn_estop = QPushButton("⛔ ACİL DURDUR (E-STOP)")
        self.btn_estop.setObjectName("BtnEstop")

        controls_layout.addWidget(self.btn_phase1)
        controls_layout.addWidget(self.btn_phase2)
        controls_layout.addWidget(self.btn_phase3)
        controls_layout.addStretch()
        controls_layout.addWidget(self.btn_fire)
        controls_layout.addWidget(self.btn_estop)

        main_layout.addWidget(controls_frame)

        # Olay Bağlantıları
        self.btn_phase1.clicked.connect(lambda: self.node.set_phase(1))
        self.btn_phase2.clicked.connect(lambda: self.node.set_phase(2))
        self.btn_phase3.clicked.connect(lambda: self.node.set_phase(3))
        self.btn_fire.clicked.connect(self.node.send_fire_cmd)
        self.btn_estop.clicked.connect(self.toggle_estop)

        # CSS Stilleri
        self.apply_stylesheet()

    def apply_stylesheet(self):
        dark_stylesheet = """
        QMainWindow {
            background-color: #0d1117;
        }
        QLabel {
            color: #c9d1d9;
            font-family: 'Inter', 'Segoe UI', sans-serif;
            font-size: 14px;
        }
        #TitleLabel {
            font-size: 24px;
            font-weight: 800;
            color: #58a6ff;
            letter-spacing: 2px;
        }
        #GlobalStatus {
            font-size: 16px;
            font-weight: bold;
            color: #3fb950;
            background: rgba(63, 185, 80, 0.1);
            border: 1px solid #3fb950;
            padding: 5px 15px;
            border-radius: 6px;
        }
        #HeaderLabel {
            font-size: 16px;
            font-weight: bold;
            color: #58a6ff;
            margin-bottom: 5px;
        }
        #ScoreLabel {
            font-size: 20px;
            font-weight: 800;
            color: #d2a8ff;
            margin-top: 10px;
        }
        QFrame {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 10px;
        }
        #CameraFrame {
            background-color: #010409;
            border: 2px solid #58a6ff;
        }
        QPushButton {
            background-color: #238636;
            color: #ffffff;
            border: 1px solid rgba(240, 246, 252, 0.1);
            padding: 12px 20px;
            font-size: 14px;
            font-weight: bold;
            border-radius: 6px;
        }
        QPushButton:hover {
            background-color: #2ea043;
        }
        QPushButton#BtnFire {
            background-color: #b73939;
        }
        QPushButton#BtnFire:hover {
            background-color: #ff5252;
        }
        QPushButton#BtnEstop {
            background-color: #d73a49;
            font-size: 16px;
        }
        QPushButton#BtnEstop:hover {
            background-color: #ff4757;
        }
        QPushButton#BtnEstop[active="true"] {
            background-color: #ff0000;
            border: 2px solid white;
        }
        """
        self.setStyleSheet(dark_stylesheet)

    def toggle_estop(self):
        self.estop_active = not self.estop_active
        self.node.send_estop(self.estop_active)
        
        self.btn_estop.setProperty("active", self.estop_active)
        self.btn_estop.style().unpolish(self.btn_estop)
        self.btn_estop.style().polish(self.btn_estop)
        
        if self.estop_active:
            self.global_status_label.setText("DURUM: KİLİTLİ (E-STOP)")
            self.global_status_label.setStyleSheet("color: #ff4757; border-color: #ff4757; background: rgba(255, 71, 87, 0.1);")
        else:
            self.global_status_label.setText("DURUM: AKTİF")
            self.global_status_label.setStyleSheet("color: #3fb950; border-color: #3fb950; background: rgba(63, 185, 80, 0.1);")

    def connect_signals(self):
        self.signaler.image_signal.connect(self.update_image)
        self.signaler.motor_signal.connect(self.update_motor_fb)
        self.signaler.target_signal.connect(self.update_target)
        self.signaler.durum_signal.connect(self.update_state)
        self.signaler.puan_signal.connect(self.update_score)

    def update_image(self, frame):
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qt_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img)
        # Ölçekleme
        self.camera_frame.setPixmap(pixmap.scaled(
            self.camera_frame.width(), self.camera_frame.height(), 
            Qt.AspectRatioMode.KeepAspectRatio)
        )

    def update_motor_fb(self, msg: MotorFeedback):
        self.lbl_pan_tilt.setText(f"Pan: {msg.current_pan_angle:.1f}°  Tilt: {msg.current_tilt_angle:.1f}°")
        self.lbl_range.setText(f"Menzil: {msg.estimated_range:.1f}m")

    def update_target(self, msg: TargetInfo):
        if msg.is_tracked:
            self.lbl_target_type.setText(f"Tip: {msg.target_type} | Renk: {msg.target_color}")
            self.lbl_target_conf.setText(f"Güven: {msg.confidence:.2f}")
            self.lbl_target_status.setText("Durum: TAKİP")
            self.lbl_target_status.setStyleSheet("color: #3fb950;")
        else:
            self.lbl_target_type.setText("Tip: - | Renk: -")
            self.lbl_target_conf.setText("Güven: 0.00")
            self.lbl_target_status.setText("Durum: BEKLENİYOR")
            self.lbl_target_status.setStyleSheet("color: #c9d1d9;")

    def update_state(self, state: str):
        self.lbl_state.setText(f"State:\n{state}")

    def update_score(self, score: int):
        self.lbl_score.setText(f"🏆 PUAN: {score}")

def main(args=None):
    rclpy.init(args=args)
    signaler = Signaler()
    ros_node = ArayuzDugumu(signaler)
    
    ros_thread = ROS2Thread(ros_node)
    ros_thread.start()
    
    app = QApplication(sys.argv)
    gui = CelikKubbeGUI(ros_node, signaler)
    gui.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
