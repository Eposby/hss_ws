#!/usr/bin/env python3
"""
ÇELİK KUBBE — Gerçek Zamanlı Kontrol Merkezi GUI
TEKNOFEST Test Videosu Yeteneklerine Uygun Tam Donanımlı Arayüz

Kontroller:
  WASD / Ok Tuşları : Manuel taret yönlendirme (Pan/Tilt)
  Space             : Ateşle
  Escape            : Acil Durdur (E-Stop) toggle
  1 / 2 / 3         : Aşama seçimi
  M                 : Manuel ↔ Otonom mod geçişi
  H                 : Home pozisyonuna dönüş
  F11               : Tam ekran toggle
  Mouse Sol Tık     : Kamera üzerinde tıklanan noktaya taret yönlendirme
"""

import sys
import time
import threading
from datetime import datetime
from collections import deque

import cv2
import numpy as np
import rclpy
from rclpy.node import Node

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGridLayout, QScrollArea,
    QProgressBar, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QSize
from PyQt6.QtGui import QImage, QPixmap, QFont, QKeyEvent, QMouseEvent, QPainter, QColor

from std_msgs.msg import String, Int32, Bool
from sensor_msgs.msg import Image
from celikkubbe_msgs.msg import TargetInfo, MotorFeedback, MotorSetpoint
from celikkubbe_msgs.srv import SetPhase
from cv_bridge import CvBridge
import json


# ═══════════════════════════════════════════════════════════════
# ROS 2 Thread
# ═══════════════════════════════════════════════════════════════
class ROS2Thread(threading.Thread):
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.daemon = True

    def run(self):
        rclpy.spin(self.node)


# ═══════════════════════════════════════════════════════════════
# Qt Signal Bridge (ROS → GUI thread-safe)
# ═══════════════════════════════════════════════════════════════
class Signaler(QObject):
    image_signal = pyqtSignal(np.ndarray)
    motor_signal = pyqtSignal(MotorFeedback)
    target_signal = pyqtSignal(TargetInfo)
    durum_signal = pyqtSignal(str)


# ═══════════════════════════════════════════════════════════════
# ROS 2 Node
# ═══════════════════════════════════════════════════════════════
class ArayuzDugumu(Node):
    def __init__(self, signaler: Signaler):
        super().__init__('arayuz_dugumu')
        self.signaler = signaler
        self.bridge = CvBridge()

        # Subscribers
        self.img_sub = self.create_subscription(
            Image, '/tespit/isaretli_goruntu', self.image_callback, 10)
        self.motor_sub = self.create_subscription(
            MotorFeedback, '/donanim/motor_geri_bildirim', self.motor_callback, 10)
        self.target_sub = self.create_subscription(
            TargetInfo, '/tespit/hedef_bilgisi', self.target_callback, 10)
        self.durum_sub = self.create_subscription(
            String, '/gorev/durum', self.durum_callback, 10)

        # Publishers
        self.operator_pub = self.create_publisher(String, '/arayuz/operator_komutu', 10)
        self.estop_pub = self.create_publisher(Bool, '/arayuz/acil_dur', 10)
        self.manual_motor_pub = self.create_publisher(MotorSetpoint, '/kontrol/motor_komutu', 10)
        self.nfz_pub = self.create_publisher(String, '/arayuz/yasak_bolge', 10)

        # Service Clients
        self.phase_client = self.create_client(SetPhase, '/gorev/asama_sec')

    # --- Callbacks ---
    def image_callback(self, msg: Image):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        self.signaler.image_signal.emit(frame)

    def motor_callback(self, msg: MotorFeedback):
        self.signaler.motor_signal.emit(msg)

    def target_callback(self, msg: TargetInfo):
        self.signaler.target_signal.emit(msg)

    def durum_callback(self, msg: String):
        self.signaler.durum_signal.emit(msg.data)

    # --- Commands ---
    def set_phase(self, phase_id: int):
        if self.phase_client.wait_for_service(timeout_sec=1.0):
            req = SetPhase.Request()
            req.phase = phase_id
            self.phase_client.call_async(req)
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

    def send_operator_cmd(self, cmd: str):
        msg = String()
        msg.data = cmd
        self.operator_pub.publish(msg)

    def send_manual_jog(self, pan_steps: int, tilt_steps: int,
                        pan_speed: int = 500, tilt_speed: int = 500):
        """Manuel modda taret hareket komutu gönder."""
        msg = MotorSetpoint()
        msg.pan_steps = pan_steps
        msg.tilt_steps = tilt_steps
        msg.pan_speed = pan_speed
        msg.tilt_speed = tilt_speed
        msg.pan_angle_deg = 0.0
        msg.tilt_angle_deg = 0.0
        self.manual_motor_pub.publish(msg)

    def publish_nfz(self, nfz_list):
        msg = String()
        # nfz_list is list of dicts: {"x_min": x, "y_min": y, "x_max": x, "y_max": y}
        msg.data = json.dumps(nfz_list)
        self.nfz_pub.publish(msg)


# ═══════════════════════════════════════════════════════════════
# Clickable Camera Label (Mouse ile aim)
# ═══════════════════════════════════════════════════════════════
class ClickableCameraLabel(QLabel):
    clicked = pyqtSignal(int, int)   # (pixel_x, pixel_y) kamera koordinatı
    nfz_added = pyqtSignal(int, int, int, int) # x1, y1, x2, y2 (real coordinates)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image_size = QSize(640, 480)   # gerçek görüntü boyutu
        self.nfz_zones = [] # list of (x1, y1, x2, y2)
        self.drag_start = None
        self.drag_current = None
        self.setMouseTracking(True)

    def set_image_size(self, w, h):
        self.image_size = QSize(w, h)

    def _get_real_coords(self, click_x, click_y):
        if not self.pixmap(): return -1, -1
        pm = self.pixmap()
        label_w, label_h = self.width(), self.height()
        pm_w, pm_h = pm.width(), pm.height()
        offset_x = (label_w - pm_w) // 2
        offset_y = (label_h - pm_h) // 2
        click_x = max(0, min(click_x - offset_x, pm_w))
        click_y = max(0, min(click_y - offset_y, pm_h))
        
        scale_x = self.image_size.width() / max(1, pm_w)
        scale_y = self.image_size.height() / max(1, pm_h)
        return int(click_x * scale_x), int(click_y * scale_y)

    def _get_label_coords(self, real_x, real_y):
        if not self.pixmap(): return -1, -1
        pm = self.pixmap()
        label_w, label_h = self.width(), self.height()
        pm_w, pm_h = pm.width(), pm.height()
        scale_x = pm_w / max(1, self.image_size.width())
        scale_y = pm_h / max(1, self.image_size.height())
        lx = real_x * scale_x
        ly = real_y * scale_y
        offset_x = (label_w - pm_w) // 2
        offset_y = (label_h - pm_h) // 2
        return int(lx + offset_x), int(ly + offset_y)

    def mousePressEvent(self, ev: QMouseEvent):
        if not self.pixmap(): return
        rx, ry = self._get_real_coords(ev.position().x(), ev.position().y())
        if rx < 0 or ry < 0: return
        
        if ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(rx, ry)
        elif ev.button() == Qt.MouseButton.RightButton:
            self.drag_start = (rx, ry)
            self.drag_current = (rx, ry)
            
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev: QMouseEvent):
        if self.drag_start and self.pixmap():
            rx, ry = self._get_real_coords(ev.position().x(), ev.position().y())
            self.drag_current = (rx, ry)
            self.update()
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev: QMouseEvent):
        if ev.button() == Qt.MouseButton.RightButton and self.drag_start:
            rx, ry = self._get_real_coords(ev.position().x(), ev.position().y())
            x1 = min(self.drag_start[0], rx)
            y1 = min(self.drag_start[1], ry)
            x2 = max(self.drag_start[0], rx)
            y2 = max(self.drag_start[1], ry)
            
            if x2 - x1 > 10 and y2 - y1 > 10:
                self.nfz_zones.append((x1, y1, x2, y2))
                self.nfz_added.emit(x1, y1, x2, y2)
            
            self.drag_start = None
            self.drag_current = None
            self.update()
        super().mouseReleaseEvent(ev)

    def paintEvent(self, ev):
        super().paintEvent(ev)
        if not self.pixmap(): return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        brush = QColor(255, 0, 0, 80)
        pen = QColor(255, 0, 0, 255)
        painter.setBrush(brush)
        painter.setPen(pen)
        
        for z in self.nfz_zones:
            lx1, ly1 = self._get_label_coords(z[0], z[1])
            lx2, ly2 = self._get_label_coords(z[2], z[3])
            painter.drawRect(lx1, ly1, lx2 - lx1, ly2 - ly1)
            
        if self.drag_start and self.drag_current:
            lx1, ly1 = self._get_label_coords(self.drag_start[0], self.drag_start[1])
            lx2, ly2 = self._get_label_coords(self.drag_current[0], self.drag_current[1])
            painter.drawRect(int(min(lx1, lx2)), int(min(ly1, ly2)), int(abs(lx2 - lx1)), int(abs(ly2 - ly1)))


# ═══════════════════════════════════════════════════════════════
# Ana GUI Penceresi
# ═══════════════════════════════════════════════════════════════
class CelikKubbeGUI(QMainWindow):

    # Manuel jog boyutu (step/count)
    JOG_STEP = 30

    def __init__(self, ros_node: ArayuzDugumu, signaler: Signaler):
        super().__init__()
        self.node = ros_node
        self.signaler = signaler

        # State
        self.estop_active = False
        self.is_manual_mode = False
        self.current_phase = 0
        self.current_state = "BEKLE"
        self.pressed_keys = set()

        # FPS
        self._frame_count = 0
        self._fps = 0.0
        self._fps_time = time.time()

        # Event log
        self._log_entries: deque = deque(maxlen=100)

        # Son hedef bilgisi
        self._last_target = TargetInfo()
        self._last_motor = MotorFeedback()
        self._camera_img_size = (640, 480)

        self._build_ui()
        self._connect_signals()
        self._start_timers()

    # ───────────────────────────────────────
    # UI Oluşturma
    # ───────────────────────────────────────
    def _build_ui(self):
        self.setWindowTitle("ÇELİKKUBBE — Kontrol Merkezi")
        self.setMinimumSize(1280, 720)
        self.resize(1440, 900)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        root = QWidget()
        self.setCentralWidget(root)
        root_lay = QVBoxLayout(root)
        root_lay.setContentsMargins(8, 8, 8, 8)
        root_lay.setSpacing(6)

        # ── HEADER ──
        header = self._make_frame("HeaderFrame")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(12, 6, 12, 6)

        self.lbl_title = QLabel("🛡  ÇELİK KUBBE SAVUNMA SİSTEMİ")
        self.lbl_title.setObjectName("TitleLabel")

        self.lbl_mode = QLabel("MOD: OTONOM")
        self.lbl_mode.setObjectName("ModeLabel")

        self.lbl_fps = QLabel("⏱ FPS: --")
        self.lbl_fps.setObjectName("FPSLabel")

        self.lbl_phase = QLabel("AŞAMA: -")
        self.lbl_phase.setObjectName("PhaseLabel")

        self.lbl_global = QLabel("DURUM: BEKLENİYOR")
        self.lbl_global.setObjectName("GlobalStatus")

        h_lay.addWidget(self.lbl_title, stretch=3)
        h_lay.addWidget(self.lbl_mode)
        h_lay.addWidget(self.lbl_fps)
        h_lay.addWidget(self.lbl_phase)
        h_lay.addWidget(self.lbl_global, stretch=1)
        root_lay.addWidget(header)

        # ── MIDDLE (Kamera + Sağ Panel) ──
        mid_lay = QHBoxLayout()
        mid_lay.setSpacing(6)

        # Kamera
        self.camera_label = ClickableCameraLabel("KAMERA BEKLENİYOR…")
        self.camera_label.setObjectName("CameraFrame")
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setMinimumSize(640, 480)
        self.camera_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.camera_label.clicked.connect(self._on_camera_click)
        mid_lay.addWidget(self.camera_label, stretch=3)

        # Sağ Panel
        right_lay = QVBoxLayout()
        right_lay.setSpacing(6)

        # ─ Telemetri ─
        tf = self._make_frame("PanelFrame")
        tl = QVBoxLayout(tf)
        tl.setContentsMargins(10, 8, 10, 8)
        tl.addWidget(self._header_lbl("📊 SİSTEM TELEMETRİ"))
        self.lbl_pan = QLabel("Pan:  0.0°")
        self.lbl_tilt = QLabel("Tilt: 0.0°")
        self.lbl_range = QLabel("Menzil: --")
        self.lbl_motor_state = QLabel("Motor: ⏸ DURDU")
        tl.addWidget(self.lbl_pan)
        tl.addWidget(self.lbl_tilt)
        tl.addWidget(self.lbl_range)
        tl.addWidget(self.lbl_motor_state)
        right_lay.addWidget(tf)

        # ─ Hedef Bilgisi ─
        hf = self._make_frame("PanelFrame")
        hl = QVBoxLayout(hf)
        hl.setContentsMargins(10, 8, 10, 8)
        hl.addWidget(self._header_lbl("🎯 HEDEF BİLGİSİ"))
        self.lbl_tgt_type = QLabel("Tip: -")
        self.lbl_tgt_conf = QLabel("Güven: 0.00")
        self.lbl_tgt_balloon = QLabel("Balon: -")
        self.lbl_tgt_status = QLabel("Durum: BEKLENİYOR")

        hl.addWidget(self.lbl_tgt_type)
        hl.addWidget(self.lbl_tgt_conf)
        hl.addWidget(self.lbl_tgt_balloon)
        hl.addWidget(self.lbl_tgt_status)

        # Hata barları
        hl.addWidget(QLabel("Hata X:"))
        self.bar_error_x = QProgressBar()
        self.bar_error_x.setObjectName("ErrorBar")
        self.bar_error_x.setRange(-320, 320)
        self.bar_error_x.setValue(0)
        self.bar_error_x.setTextVisible(True)
        self.bar_error_x.setFormat("%v px")
        hl.addWidget(self.bar_error_x)

        hl.addWidget(QLabel("Hata Y:"))
        self.bar_error_y = QProgressBar()
        self.bar_error_y.setObjectName("ErrorBar")
        self.bar_error_y.setRange(-240, 240)
        self.bar_error_y.setValue(0)
        self.bar_error_y.setTextVisible(True)
        self.bar_error_y.setFormat("%v px")
        hl.addWidget(self.bar_error_y)
        right_lay.addWidget(hf)

        # ─ State Machine ─
        sf = self._make_frame("PanelFrame")
        sl = QVBoxLayout(sf)
        sl.setContentsMargins(10, 8, 10, 8)
        sl.addWidget(self._header_lbl("📌 GÖREV DURUMU"))
        self.lbl_state = QLabel("State: BEKLE")
        sl.addWidget(self.lbl_state)
        right_lay.addWidget(sf)

        # ─ Olay Logu ─
        lf = self._make_frame("PanelFrame")
        ll = QVBoxLayout(lf)
        ll.setContentsMargins(10, 8, 10, 8)
        ll.addWidget(self._header_lbl("📋 OLAY LOGU"))
        self.log_container = QVBoxLayout()
        self.log_container.setSpacing(1)
        log_widget = QWidget()
        log_widget.setLayout(self.log_container)

        scroll = QScrollArea()
        scroll.setObjectName("LogScroll")
        scroll.setWidget(log_widget)
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(160)
        ll.addWidget(scroll)
        right_lay.addWidget(lf, stretch=1)

        mid_lay.addLayout(right_lay, stretch=1)
        root_lay.addLayout(mid_lay, stretch=10)

        # ── ALT PANEL (Kontroller + Kısayollar) ──
        bottom = self._make_frame("BottomFrame")
        b_lay = QVBoxLayout(bottom)
        b_lay.setContentsMargins(10, 8, 10, 8)
        b_lay.setSpacing(6)

        # Butonlar
        btn_row = QHBoxLayout()
        self.btn_p1 = QPushButton("AŞAMA 1 (MANUEL)")
        self.btn_p1.setObjectName("PhaseBtn")
        self.btn_p2 = QPushButton("AŞAMA 2 (SÜRÜ)")
        self.btn_p2.setObjectName("PhaseBtn")
        self.btn_p3 = QPushButton("AŞAMA 3 (HAREKETLİ)")
        self.btn_p3.setObjectName("PhaseBtn")
        self.btn_mode = QPushButton("M: OTONOM MOD")
        self.btn_mode.setObjectName("ModeBtn")
        self.btn_home = QPushButton("H: HOME")
        self.btn_home.setObjectName("HomeBtn")
        self.btn_fire = QPushButton("🔫 ATEŞLE (Space)")
        self.btn_fire.setObjectName("BtnFire")
        self.btn_estop = QPushButton("⛔ ACİL DURDUR (Esc)")
        self.btn_estop.setObjectName("BtnEstop")

        self.btn_clear_nfz = QPushButton("YASAK BÖLGELERİ TEMİZLE (N)")
        self.btn_clear_nfz.setObjectName("ModeBtn")

        btn_row.addWidget(self.btn_p1)
        btn_row.addWidget(self.btn_p2)
        btn_row.addWidget(self.btn_p3)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_clear_nfz)
        btn_row.addWidget(self.btn_mode)
        btn_row.addWidget(self.btn_home)
        btn_row.addWidget(self.btn_fire)
        btn_row.addWidget(self.btn_estop)
        b_lay.addLayout(btn_row)

        # Kısayol rehberi
        shortcut_lbl = QLabel(
            "⌨  WASD/Oklar: Taret Yönlendirme  |  Space: Ateş  |  "
            "Esc: E-Stop  |  1/2/3: Aşama  |  M: Mod  |  H: Home  |  "
            "F11: Tam Ekran  |  🖱 Sol Tık: Hedefe Yönlendir"
        )
        shortcut_lbl.setObjectName("ShortcutLabel")
        shortcut_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        b_lay.addWidget(shortcut_lbl)

        root_lay.addWidget(bottom)

        # E-Stop Overlay (Gizli başlar)
        self.estop_overlay = QLabel(self.centralWidget())
        self.estop_overlay.setObjectName("EstopOverlay")
        self.estop_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.estop_overlay.setText("⛔  ACİL DURDURMA AKTİF  ⛔")
        self.estop_overlay.hide()

        # Buton bağlantıları
        self.btn_p1.clicked.connect(lambda: self._select_phase(1))
        self.btn_p2.clicked.connect(lambda: self._select_phase(2))
        self.btn_p3.clicked.connect(lambda: self._select_phase(3))
        self.btn_fire.clicked.connect(self._fire)
        self.btn_estop.clicked.connect(self._toggle_estop)
        self.btn_mode.clicked.connect(self._toggle_mode)
        self.btn_home.clicked.connect(self._go_home)
        self.btn_clear_nfz.clicked.connect(self._clear_nfz)
        self.camera_label.nfz_added.connect(self._on_nfz_added)

        self._apply_stylesheet()

    # ───────────────────────────────────────
    # Yardımcı Widget Oluşturucular
    # ───────────────────────────────────────
    @staticmethod
    def _make_frame(name: str) -> QFrame:
        f = QFrame()
        f.setObjectName(name)
        return f

    @staticmethod
    def _header_lbl(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("SectionHeader")
        return lbl

    # ───────────────────────────────────────
    # Signal Bağlantıları
    # ───────────────────────────────────────
    def _connect_signals(self):
        self.signaler.image_signal.connect(self._on_image)
        self.signaler.motor_signal.connect(self._on_motor)
        self.signaler.target_signal.connect(self._on_target)
        self.signaler.durum_signal.connect(self._on_state)

    # ───────────────────────────────────────
    # Timerlar
    # ───────────────────────────────────────
    def _start_timers(self):
        # FPS timer — her saniye güncelle
        self._fps_timer = QTimer(self)
        self._fps_timer.timeout.connect(self._update_fps_display)
        self._fps_timer.start(1000)

        # Manuel jog timer — tuş basılıyken sürekli gönder
        self._jog_timer = QTimer(self)
        self._jog_timer.timeout.connect(self._process_jog)
        self._jog_timer.start(50)  # 20 Hz

        # E-Stop blink timer
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._blink_estop)
        self._blink_visible = True

    # ───────────────────────────────────────
    # Klavye Kontrolleri
    # ───────────────────────────────────────
    def keyPressEvent(self, ev: QKeyEvent):
        key = ev.key()
        if ev.isAutoRepeat():
            return

        self.pressed_keys.add(key)

        if key == Qt.Key.Key_Space:
            self._fire()
        elif key == Qt.Key.Key_Escape:
            self._toggle_estop()
        elif key == Qt.Key.Key_1:
            self._select_phase(1)
        elif key == Qt.Key.Key_2:
            self._select_phase(2)
        elif key == Qt.Key.Key_3:
            self._select_phase(3)
        elif key == Qt.Key.Key_M:
            self._toggle_mode()
        elif key == Qt.Key.Key_H:
            self._go_home()
        elif key == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        elif key == Qt.Key.Key_N:
            self._clear_nfz()

        super().keyPressEvent(ev)

    def keyReleaseEvent(self, ev: QKeyEvent):
        if ev.isAutoRepeat():
            return
        self.pressed_keys.discard(ev.key())
        super().keyReleaseEvent(ev)

    def _process_jog(self):
        """Basılı tuşlara göre manuel taret komutu gönder."""
        if not self.is_manual_mode or self.estop_active:
            return

        pan = 0
        tilt = 0
        k = Qt.Key

        if k.Key_A in self.pressed_keys or k.Key_Left in self.pressed_keys:
            pan = -self.JOG_STEP
        if k.Key_D in self.pressed_keys or k.Key_Right in self.pressed_keys:
            pan = self.JOG_STEP
        if k.Key_W in self.pressed_keys or k.Key_Up in self.pressed_keys:
            tilt = -self.JOG_STEP   # yukarı = negatif
        if k.Key_S in self.pressed_keys or k.Key_Down in self.pressed_keys:
            tilt = self.JOG_STEP

        if pan != 0 or tilt != 0:
            self.node.send_manual_jog(pan, tilt)

    # ───────────────────────────────────────
    # Mouse Click-to-Aim
    # ───────────────────────────────────────
    def _on_camera_click(self, pixel_x: int, pixel_y: int):
        """Kamera üzerindeki tıklama noktasına tareti yönlendir."""
        if self.estop_active:
            return

        img_w, img_h = self._camera_img_size

        # Tıklanan nokta ile frame merkezi arasındaki hata
        error_x = pixel_x - img_w // 2
        error_y = pixel_y - img_h // 2

        # Hata pikselini step/count'a basit orantıyla çevir
        pan_steps = int(error_x * 0.5)
        tilt_steps = int(error_y * 0.5)

        self.node.send_manual_jog(pan_steps, tilt_steps, pan_speed=800, tilt_speed=800)
        self._add_log(f"🖱 Mouse aim → ({pixel_x},{pixel_y}) Δx={error_x} Δy={error_y}", "#58a6ff")

    # ───────────────────────────────────────
    # Komut Fonksiyonları
    # ───────────────────────────────────────
    def _fire(self):
        if self.estop_active:
            return
        self.node.send_fire_cmd()
        self._add_log("🔫 ATEŞ AÇILDI", "#ff4757")

    def _toggle_estop(self):
        self.estop_active = not self.estop_active
        self.node.send_estop(self.estop_active)

        if self.estop_active:
            self.lbl_global.setText("⛔ E-STOP AKTİF")
            self.lbl_global.setStyleSheet(
                "color:#ff4757; border-color:#ff4757; background:rgba(255,71,87,0.15);")
            self.estop_overlay.show()
            self._blink_timer.start(500)
            self._add_log("⛔ ACİL DURDURMA AKTİVE EDİLDİ", "#ff4757")

            # Tüm tuşları temizle
            self.pressed_keys.clear()
        else:
            self.lbl_global.setText("DURUM: AKTİF")
            self.lbl_global.setStyleSheet(
                "color:#3fb950; border-color:#3fb950; background:rgba(63,185,80,0.1);")
            self.estop_overlay.hide()
            self._blink_timer.stop()
            self._add_log("✅ E-Stop kaldırıldı", "#3fb950")

    def _select_phase(self, phase: int):
        self.current_phase = phase
        self.node.set_phase(phase)
        self.lbl_phase.setText(f"AŞAMA: {phase}")
        names = {1: "MANUEL", 2: "SÜRÜ", 3: "HAREKETLİ"}
        self._add_log(f"📌 Aşama {phase} ({names.get(phase,'')}) seçildi", "#d2a8ff")

    def _toggle_mode(self):
        self.is_manual_mode = not self.is_manual_mode
        mode_str = "MANUEL" if self.is_manual_mode else "OTONOM"
        self.lbl_mode.setText(f"MOD: {mode_str}")
        self.btn_mode.setText(f"M: {mode_str} MOD")

        if self.is_manual_mode:
            self.lbl_mode.setStyleSheet(
                "color:#ffa502; border-color:#ffa502; background:rgba(255,165,2,0.1);")
            self.node.send_operator_cmd("mod_manuel")
        else:
            self.lbl_mode.setStyleSheet(
                "color:#3fb950; border-color:#3fb950; background:rgba(63,185,80,0.1);")
            self.node.send_operator_cmd("mod_otonom")

        self._add_log(f"🔄 Mod değişti: {mode_str}", "#58a6ff")

    def _go_home(self):
        self.node.send_operator_cmd("home")
        self._add_log("🏠 Home pozisyonuna dönülüyor", "#58a6ff")

    def _on_nfz_added(self, x1, y1, x2, y2):
        self._add_log(f"🛑 Yasak Bölge Eklendi", "#ff4757")
        self._publish_current_nfz()

    def _clear_nfz(self):
        self.camera_label.nfz_zones.clear()
        self.camera_label.update()
        self._add_log("🟩 Yasak Bölgeler Temizlendi", "#3fb950")
        self._publish_current_nfz()

    def _publish_current_nfz(self):
        zone_dicts = [{"x_min": z[0], "y_min": z[1], "x_max": z[2], "y_max": z[3]} for z in self.camera_label.nfz_zones]
        self.node.publish_nfz(zone_dicts)

    # ───────────────────────────────────────
    # E-Stop Blink Animasyonu
    # ───────────────────────────────────────
    def _blink_estop(self):
        self._blink_visible = not self._blink_visible
        if self._blink_visible:
            self.estop_overlay.setStyleSheet(
                "background: rgba(255,0,0,0.35); color: white; "
                "font-size: 48px; font-weight: 900;")
        else:
            self.estop_overlay.setStyleSheet(
                "background: rgba(255,0,0,0.10); color: rgba(255,255,255,0.3); "
                "font-size: 48px; font-weight: 900;")

    def resizeEvent(self, ev):
        """E-Stop overlay'ini pencere boyutuna uyarla."""
        super().resizeEvent(ev)
        if hasattr(self, 'estop_overlay'):
            cw = self.centralWidget()
            self.estop_overlay.setGeometry(0, 0, cw.width(), cw.height())

    # ───────────────────────────────────────
    # Olay Logu
    # ───────────────────────────────────────
    def _add_log(self, text: str, color: str = "#c9d1d9"):
        ts = datetime.now().strftime("%H:%M:%S")
        entry = f'<span style="color:#8b949e">[{ts}]</span> <span style="color:{color}">{text}</span>'
        self._log_entries.appendleft(entry)

        # Widget güncelle (en yeni üstte)
        lbl = QLabel(entry)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setStyleSheet("background:transparent; border:none; padding:1px 0;")
        lbl.setWordWrap(True)
        self.log_container.insertWidget(0, lbl)

        # Eski girişleri temizle (max 50 widget)
        while self.log_container.count() > 50:
            item = self.log_container.takeAt(self.log_container.count() - 1)
            if item.widget():
                item.widget().deleteLater()

    # ───────────────────────────────────────
    # FPS
    # ───────────────────────────────────────
    def _update_fps_display(self):
        now = time.time()
        elapsed = now - self._fps_time
        if elapsed > 0:
            self._fps = self._frame_count / elapsed
        self._frame_count = 0
        self._fps_time = now
        self.lbl_fps.setText(f"⏱ FPS: {self._fps:.0f}")

    # ───────────────────────────────────────
    # ROS Callback → GUI Updates
    # ───────────────────────────────────────
    def _on_image(self, frame: np.ndarray):
        self._frame_count += 1
        h, w, ch = frame.shape
        self._camera_img_size = (w, h)
        self.camera_label.set_image_size(w, h)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qt_img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img)
        self.camera_label.setPixmap(pixmap.scaled(
            self.camera_label.width(), self.camera_label.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))

    def _on_motor(self, msg: MotorFeedback):
        self._last_motor = msg
        self.lbl_pan.setText(f"Pan:  {msg.current_pan_angle:+.1f}°")
        self.lbl_tilt.setText(f"Tilt: {msg.current_tilt_angle:+.1f}°")
        self.lbl_range.setText(f"Menzil: {msg.estimated_range:.1f} m")

        if msg.is_moving:
            self.lbl_motor_state.setText("Motor: ▶ HAREKET EDİYOR")
            self.lbl_motor_state.setStyleSheet("color: #3fb950;")
        else:
            self.lbl_motor_state.setText("Motor: ⏸ DURDU")
            self.lbl_motor_state.setStyleSheet("color: #8b949e;")

    def _on_target(self, msg: TargetInfo):
        self._last_target = msg

        if msg.is_tracked:
            self.lbl_tgt_type.setText(f"Tip: {msg.target_type.upper()}")
            self.lbl_tgt_conf.setText(f"Güven: {msg.confidence:.2f}")

            if msg.has_balloon:
                self.lbl_tgt_balloon.setText("🎈 BALON VAR")
                self.lbl_tgt_balloon.setStyleSheet("color: #ff4757; font-weight:bold;")
                self.lbl_tgt_status.setText("VURULABİLİR")
                self.lbl_tgt_status.setStyleSheet("color: #ff4757;")
            else:
                self.lbl_tgt_balloon.setText("❌ BALON YOK")
                self.lbl_tgt_balloon.setStyleSheet("color: #ffa502;")
                self.lbl_tgt_status.setText("İMHA EDİLMİŞ")
                self.lbl_tgt_status.setStyleSheet("color: #ffa502;")

            # Hata barları
            self.bar_error_x.setValue(int(msg.error_x))
            self.bar_error_y.setValue(int(msg.error_y))
        else:
            self.lbl_tgt_type.setText("Tip: -")
            self.lbl_tgt_conf.setText("Güven: 0.00")
            self.lbl_tgt_balloon.setText("Balon: -")
            self.lbl_tgt_balloon.setStyleSheet("color: #8b949e;")
            self.lbl_tgt_status.setText("BEKLENİYOR")
            self.lbl_tgt_status.setStyleSheet("color: #8b949e;")
            self.bar_error_x.setValue(0)
            self.bar_error_y.setValue(0)

    def _on_state(self, state: str):
        self.current_state = state
        self.lbl_state.setText(f"State: {state}")

        # Log bazı önemli state geçişlerini
        if state in ("ATESLE", "IMHA_BASARILI", "IMHA_IPTAL", "HEDEF_BEKLEME"):
            colors = {
                "ATESLE": "#ff4757",
                "IMHA_BASARILI": "#3fb950",
                "IMHA_IPTAL": "#ffa502",
                "HEDEF_BEKLEME": "#ffa502"
            }
            self._add_log(f"🔔 State → {state}", colors.get(state, "#c9d1d9"))

    # ───────────────────────────────────────
    # Stylesheet
    # ───────────────────────────────────────
    def _apply_stylesheet(self):
        self.setStyleSheet("""
        QMainWindow {
            background-color: #0d1117;
        }
        QWidget {
            font-family: 'Inter', 'Segoe UI', 'SF Pro', sans-serif;
        }
        QLabel {
            color: #c9d1d9;
            font-size: 13px;
            background: transparent;
            border: none;
        }

        /* ── Header ── */
        #HeaderFrame {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #161b22, stop:1 #1c2333);
            border: 1px solid #30363d;
            border-radius: 8px;
        }
        #TitleLabel {
            font-size: 22px; font-weight: 800;
            color: #58a6ff; letter-spacing: 1.5px;
        }
        #ModeLabel, #PhaseLabel, #FPSLabel {
            font-size: 13px; font-weight: bold;
            padding: 4px 12px; border-radius: 4px;
            border: 1px solid #30363d;
            background: rgba(22,27,34,0.8);
            color: #3fb950;
        }
        #GlobalStatus {
            font-size: 14px; font-weight: bold;
            color: #3fb950;
            background: rgba(63,185,80,0.1);
            border: 1px solid #3fb950;
            padding: 4px 14px; border-radius: 6px;
        }
        #ScoreLabel {
            font-size: 20px; font-weight: 900;
            color: #d2a8ff;
        }

        /* ── Camera ── */
        #CameraFrame {
            background-color: #010409;
            border: 2px solid #58a6ff;
            border-radius: 8px;
        }

        /* ── Side Panels ── */
        #PanelFrame {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
        }
        #SectionHeader {
            font-size: 14px; font-weight: bold;
            color: #58a6ff; margin-bottom: 4px; border: none;
        }

        /* ── Error Bars ── */
        QProgressBar#ErrorBar {
            background-color: #21262d;
            border: 1px solid #30363d;
            border-radius: 4px;
            height: 16px;
            text-align: center;
            font-size: 11px;
            color: #c9d1d9;
        }
        QProgressBar#ErrorBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #ff4757, stop:0.4 #ffa502, stop:0.5 #3fb950,
                stop:0.6 #ffa502, stop:1 #ff4757);
            border-radius: 3px;
        }

        /* ── Log ── */
        #LogScroll {
            background: #0d1117;
            border: 1px solid #21262d;
            border-radius: 4px;
        }
        QScrollArea QWidget {
            background: transparent;
        }

        /* ── Bottom ── */
        #BottomFrame {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
        }
        #ShortcutLabel {
            font-size: 11px; color: #8b949e;
            padding: 2px; border: none;
        }

        /* ── Buttons ── */
        QPushButton {
            background-color: #21262d;
            color: #c9d1d9;
            border: 1px solid #30363d;
            padding: 10px 16px;
            font-size: 13px; font-weight: bold;
            border-radius: 6px;
        }
        QPushButton:hover { background-color: #30363d; }
        QPushButton:pressed { background-color: #484f58; }

        QPushButton#PhaseBtn {
            background-color: #1f6feb;
            color: #ffffff;
            border: 1px solid #388bfd;
        }
        QPushButton#PhaseBtn:hover { background-color: #388bfd; }

        QPushButton#ModeBtn {
            background-color: #238636;
            color: white; border-color: #2ea043;
        }
        QPushButton#ModeBtn:hover { background-color: #2ea043; }

        QPushButton#HomeBtn {
            background-color: #6e40c9;
            color: white; border-color: #8957e5;
        }
        QPushButton#HomeBtn:hover { background-color: #8957e5; }

        QPushButton#BtnFire {
            background-color: #b62324;
            color: white; border-color: #da3633;
            font-size: 14px;
        }
        QPushButton#BtnFire:hover { background-color: #da3633; }

        QPushButton#BtnEstop {
            background-color: #8b0000;
            color: white; border: 2px solid #ff0000;
            font-size: 15px; font-weight: 900;
            padding: 10px 24px;
        }
        QPushButton#BtnEstop:hover {
            background-color: #cc0000;
        }

        /* ── E-Stop Overlay ── */
        #EstopOverlay {
            background: rgba(255,0,0,0.35);
            color: white;
            font-size: 48px;
            font-weight: 900;
            border: none;
        }
        """)


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════
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
