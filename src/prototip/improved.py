"""
ÇELİK KUBBE - TEKNOFEST 2026
Hava Savunma Sistemi Kontrol Arayüzü

Şartname gereksinimleri:
- Manuel / Otonom mod geçişi
- Acil Durdur (zorunlu)
- Harekete yasak alan / Atışa yasak alan
- Hedef sırası takibi (Aşama 1)
- YOLO hedef sınıflandırması (Yetenek 6)
- Sistem durumu ve motor pozisyonu


main.py bunları çağırmak gerekiyormuş

window.set_serial_communicator(self.serial)
window.update_camera_frame(frame, detections, fps)
window.update_motor_position(pan, tilt)
window.update_detection(primary_target)
"""

import sys
import time
import json
import numpy as np
import cv2
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGridLayout, QComboBox,
    QSlider, QSpinBox, QGroupBox, QListWidget, QListWidgetItem,
    QProgressBar, QSizePolicy, QStackedWidget, QCheckBox,
    QDoubleSpinBox, QTextEdit, QSplitter, QMessageBox
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation,
    QEasingCurve, QSize, pyqtSlot
)
from PyQt6.QtGui import (
    QFont, QPixmap, QImage, QPainter, QPen, QColor,
    QBrush, QLinearGradient, QRadialGradient, QPalette,
    QKeySequence, QShortcut, QIcon
)

# ==========================================
# RENK PALETİ & STİL
# ==========================================
COLORS = {
    'bg_dark':      '#0a0e1a',
    'bg_panel':     '#0d1526',
    'bg_card':      '#111d35',
    'border':       '#1a3a5c',
    'border_glow':  '#0066cc',
    'accent_blue':  '#0088ff',
    'accent_cyan':  '#00d4ff',
    'accent_green': '#00ff88',
    'accent_red':   '#ff2244',
    'accent_orange':'#ff6600',
    'accent_yellow':'#ffcc00',
    'text_primary': '#e8f4ff',
    'text_secondary':'#7aa0cc',
    'text_dim':     '#3a5a7c',
}

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['text_primary']};
    font-family: 'Courier New', monospace;
}}

QFrame#PanelFrame {{
    background-color: {COLORS['bg_panel']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
}}

QFrame#CardFrame {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
}}

QGroupBox {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    font-family: 'Courier New', monospace;
    font-size: 10px;
    font-weight: bold;
    color: {COLORS['text_secondary']};
    margin-top: 14px;
    padding-top: 8px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 6px;
    color: {COLORS['accent_cyan']};
    letter-spacing: 1px;
}}

QPushButton {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 8px 14px;
    font-family: 'Courier New', monospace;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}}

QPushButton:hover {{
    background-color: {COLORS['border']};
    border-color: {COLORS['accent_blue']};
    color: {COLORS['accent_cyan']};
}}

QPushButton:pressed {{
    background-color: {COLORS['border_glow']};
}}

QPushButton:disabled {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['text_dim']};
    border-color: {COLORS['text_dim']};
}}

QPushButton#BtnEmergency {{
    background-color: #3a0010;
    color: {COLORS['accent_red']};
    border: 2px solid {COLORS['accent_red']};
    border-radius: 6px;
    font-size: 16px;
    font-weight: bold;
    letter-spacing: 3px;
    min-height: 60px;
}}

QPushButton#BtnEmergency:hover {{
    background-color: #6a0020;
}}

QPushButton#BtnFire {{
    background-color: #2a1500;
    color: {COLORS['accent_orange']};
    border: 2px solid {COLORS['accent_orange']};
    font-size: 13px;
    letter-spacing: 2px;
    min-height: 45px;
}}

QPushButton#BtnFire:hover {{
    background-color: #4a2500;
}}

QPushButton#BtnFire:disabled {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['text_dim']};
    border-color: {COLORS['text_dim']};
}}

QPushButton#BtnModeManual {{
    background-color: #0a2000;
    color: {COLORS['accent_green']};
    border: 1px solid {COLORS['accent_green']};
    letter-spacing: 2px;
}}

QPushButton#BtnModeAuto {{
    background-color: #000a25;
    color: {COLORS['accent_blue']};
    border: 1px solid {COLORS['accent_blue']};
    letter-spacing: 2px;
}}

QPushButton#BtnModeActive {{
    border-width: 2px;
    font-weight: bold;
}}

QLabel {{
    color: {COLORS['text_primary']};
    font-family: 'Courier New', monospace;
}}

QLabel#LabelTitle {{
    font-size: 18px;
    font-weight: bold;
    color: {COLORS['accent_cyan']};
    letter-spacing: 4px;
}}

QLabel#LabelSectionHeader {{
    font-size: 10px;
    color: {COLORS['text_secondary']};
    letter-spacing: 2px;
}}

QLabel#StatusOK {{
    color: {COLORS['accent_green']};
    font-weight: bold;
}}

QLabel#StatusWARN {{
    color: {COLORS['accent_yellow']};
    font-weight: bold;
}}

QLabel#StatusERR {{
    color: {COLORS['accent_red']};
    font-weight: bold;
}}

QListWidget {{
    background-color: {COLORS['bg_dark']};
    border: 1px solid {COLORS['border']};
    color: {COLORS['text_primary']};
    font-family: 'Courier New', monospace;
    font-size: 11px;
    border-radius: 4px;
}}

QListWidget::item:selected {{
    background-color: {COLORS['border']};
    color: {COLORS['accent_cyan']};
}}

QTextEdit {{
    background-color: {COLORS['bg_dark']};
    border: 1px solid {COLORS['border']};
    color: #44ff88;
    font-family: 'Courier New', monospace;
    font-size: 10px;
    border-radius: 4px;
}}

QSlider::groove:horizontal {{
    height: 4px;
    background: {COLORS['border']};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: {COLORS['accent_cyan']};
    width: 14px;
    height: 14px;
    border-radius: 7px;
    margin: -5px 0;
}}

QSlider::sub-page:horizontal {{
    background: {COLORS['accent_blue']};
    border-radius: 2px;
}}

QComboBox {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    color: {COLORS['text_primary']};
    font-family: 'Courier New', monospace;
    padding: 4px 8px;
    border-radius: 4px;
}}

QComboBox::drop-down {{
    border: none;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_panel']};
    border: 1px solid {COLORS['border']};
    color: {COLORS['text_primary']};
    selection-background-color: {COLORS['border']};
}}

QProgressBar {{
    background-color: {COLORS['bg_dark']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    height: 8px;
    text-align: center;
    color: transparent;
}}

QProgressBar::chunk {{
    background-color: {COLORS['accent_blue']};
    border-radius: 2px;
}}

QCheckBox {{
    color: {COLORS['text_secondary']};
    font-family: 'Courier New', monospace;
    font-size: 10px;
    spacing: 6px;
}}

QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {COLORS['border']};
    border-radius: 2px;
    background: {COLORS['bg_dark']};
}}

QCheckBox::indicator:checked {{
    background: {COLORS['accent_blue']};
    border-color: {COLORS['accent_cyan']};
}}

QSpinBox, QDoubleSpinBox {{
    background-color: {COLORS['bg_dark']};
    border: 1px solid {COLORS['border']};
    color: {COLORS['text_primary']};
    font-family: 'Courier New', monospace;
    padding: 3px 6px;
    border-radius: 3px;
}}

QSplitter::handle {{
    background-color: {COLORS['border']};
}}
"""

# ==========================================
# HEDEF TİPLERİ (Şartname Aşama 1 & 3)
# ==========================================
TARGET_TYPES = {
    'f16':        {'label': 'F-16 SAVAŞ UÇAĞI',    'color': '#ff2244', 'min_range': 10, 'max_range': 15},
    'helicopter': {'label': 'HELİKOPTER',           'color': '#ff6600', 'min_range': 5,  'max_range': 15},
    'ballistic':  {'label': 'BALİSTİK FÜZE',        'color': '#ff6600', 'min_range': 5,  'max_range': 15},
    'iha':        {'label': 'İHA',                   'color': '#ffcc00', 'min_range': 0,  'max_range': 15},
    'mini_iha':   {'label': 'MİNİ/MİCRO İHA',       'color': '#ffcc00', 'min_range': 0,  'max_range': 15},
    'friend':     {'label': 'DOST UNSUR',            'color': '#00ff88', 'min_range': -1, 'max_range': -1},
    'unknown':    {'label': 'TANIMSIZ',              'color': '#7aa0cc', 'min_range': -1, 'max_range': -1},
}

# Aşama 1 hedef sırası (yarışmada zarf ile verilecek, buradan girilecek)
DEFAULT_TARGET_ORDER = ['ballistic', 'iha', 'helicopter', 'f16', 'mini_iha']


# ==========================================
# KAMERA OVERLAY WİDGET
# ==========================================
class CameraWidget(QLabel):
    """
    Kamera görüntüsü + YOLO overlay + nişangah çizen widget.
    Fare tıklaması ile hedef kilitleme desteği.
    """
    target_clicked = pyqtSignal(int, int)  # x, y piksel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(640, 480)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setObjectName("CameraWidget")
        self.setStyleSheet(f"""
            QLabel#CameraWidget {{
                background-color: #000000;
                border: 2px solid {COLORS['border']};
                border-radius: 6px;
            }}
        """)

        # Mevcut tespit verisi
        self.detections = []
        self.selected_target = None
        self.crosshair_visible = True
        self.frame_size = (640, 480)

        # Overlay bilgileri
        self.mode_text = "MANUEL"
        self.fps = 0.0
        self.pan_angle = 0.0
        self.tilt_angle = 0.0

        # No-signal ekranı
        self._show_no_signal()

    def _show_no_signal(self):
        """Kamera bağlı değilse göster"""
        pixmap = QPixmap(640, 480)
        pixmap.fill(QColor('#000510'))
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor(COLORS['text_dim']), 1))
        painter.setFont(QFont('Courier New', 14, QFont.Weight.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "[ KAMERA SİNYALİ YOK ]")
        painter.setPen(QPen(QColor(COLORS['border']), 1, Qt.PenStyle.DashLine))
        painter.drawRect(10, 10, 619, 459)
        painter.end()
        self.setPixmap(pixmap)

    def update_frame(self, frame: np.ndarray, detections: list, fps: float):
        """Her kamera frame'inde çağrılır"""
        self.fps = fps
        self.detections = detections
        self.frame_size = (frame.shape[1], frame.shape[0])

        # Frame'i kopyala ve overlay çiz
        display = frame.copy()
        self._draw_overlay(display)

        # numpy → QPixmap
        h, w, ch = display.shape
        qt_image = QImage(display.data, w, h, ch * w, QImage.Format.Format_BGR888)
        scaled = QPixmap.fromImage(qt_image).scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled)

    def _draw_overlay(self, frame):
        """Nişangah, tespitler, mod yazısı çiz"""
        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2

        # Nişangah
        if self.crosshair_visible:
            col = (0, 255, 136)  # accent_green
            cv2.line(frame, (cx - 40, cy), (cx - 12, cy), col, 1)
            cv2.line(frame, (cx + 12, cy), (cx + 40, cy), col, 1)
            cv2.line(frame, (cx, cy - 40), (cx, cy - 12), col, 1)
            cv2.line(frame, (cx, cy + 12), (cx, cy + 40), col, 1)
            cv2.circle(frame, (cx, cy), 4, col, 1)
            # Köşe işaretleri
            for dx, dy in [(-50, -35), (50, -35), (-50, 35), (50, 35)]:
                sx = cx + dx
                sy = cy + dy
                ex_h = sx + (10 if dx > 0 else -10)
                ey_v = sy + (8 if dy > 0 else -8)
                cv2.line(frame, (sx, sy), (ex_h, sy), col, 1)
                cv2.line(frame, (sx, sy), (sx, ey_v), col, 1)

        # YOLO tespitlerini çiz
        for det in self.detections:
            x1, y1, x2, y2 = det.get('bbox', (0, 0, 0, 0))
            cls = det.get('class_name', 'unknown')
            conf = det.get('confidence', 0.0)
            is_friend = det.get('is_friend', False)

            color_hex = COLORS['accent_green'] if is_friend else COLORS['accent_red']
            color_bgr = self._hex_to_bgr(color_hex)

            # Bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color_bgr, 2)

            # Köşe vurguları
            corner_len = 12
            for px, py in [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]:
                dx = corner_len if px == x1 else -corner_len
                dy = corner_len if py == y1 else -corner_len
                cv2.line(frame, (px, py), (px + dx, py), color_bgr, 2)
                cv2.line(frame, (px, py), (px, py + dy), color_bgr, 2)

            # Etiket
            target_info = TARGET_TYPES.get(cls, TARGET_TYPES['unknown'])
            label = f"{target_info['label']} {conf:.0%}"
            cv2.putText(frame, label, (x1, y1 - 8),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, color_bgr, 1)

            # Merkez nokta
            mx, my = (x1 + x2) // 2, (y1 + y2) // 2
            cv2.circle(frame, (mx, my), 4, color_bgr, -1)

        # Mod yazısı (sol üst)
        mode_color = (0, 255, 136) if self.mode_text == "MANUEL" else (0, 136, 255)
        cv2.putText(frame, f"[ {self.mode_text} ]", (12, 24),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.55, mode_color, 1)

        # FPS (sağ üst)
        cv2.putText(frame, f"FPS: {self.fps:.1f}", (w - 90, 24),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 160, 200), 1)

        # Motor açıları (sol alt)
        cv2.putText(frame, f"PAN: {self.pan_angle:+.1f}°  TILT: {self.tilt_angle:+.1f}°",
                   (12, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 160, 200), 1)

        # Tarama çizgisi efekti
        scan_y = int((time.time() * 80) % h)
        cv2.line(frame, (0, scan_y), (w, scan_y), (0, 40, 80), 1)

    def _hex_to_bgr(self, hex_color: str):
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return (b, g, r)

    def mousePressEvent(self, event):
        """Fare tıklaması ile hedef kilitleme"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.target_clicked.emit(event.pos().x(), event.pos().y())


# ==========================================
# MOTOR POZİSYON GÖSTERGESİ
# ==========================================
class MotorGaugeWidget(QWidget):
    """Pan ve Tilt açılarını görsel olarak gösteren widget"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 80)
        self.pan_angle = 0.0
        self.tilt_angle = 0.0
        self.pan_min = -180.0
        self.pan_max = 180.0
        self.tilt_min = -45.0
        self.tilt_max = 90.0

    def set_angles(self, pan: float, tilt: float):
        self.pan_angle = pan
        self.tilt_angle = tilt
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Arka plan
        painter.fillRect(0, 0, w, h, QColor(COLORS['bg_dark']))

        bar_h = 14
        margin = 10
        label_w = 40
        bar_w = w - label_w - margin * 2

        for i, (label, angle, min_a, max_a, color) in enumerate([
            ('PAN', self.pan_angle, self.pan_min, self.pan_max, COLORS['accent_blue']),
            ('TILT', self.tilt_angle, self.tilt_min, self.tilt_max, COLORS['accent_cyan']),
        ]):
            y = margin + i * (bar_h + 20)

            # Etiket
            painter.setPen(QColor(COLORS['text_secondary']))
            painter.setFont(QFont('Courier New', 8))
            painter.drawText(margin, y, label_w, bar_h, Qt.AlignmentFlag.AlignVCenter, label)

            # Bar arka plan
            bar_x = margin + label_w
            painter.fillRect(bar_x, y, bar_w, bar_h, QColor(COLORS['bg_card']))
            painter.setPen(QColor(COLORS['border']))
            painter.drawRect(bar_x, y, bar_w, bar_h)

            # Merkez çizgisi
            mid_x = bar_x + bar_w // 2
            painter.setPen(QPen(QColor(COLORS['text_dim']), 1, Qt.PenStyle.DashLine))
            painter.drawLine(mid_x, y, mid_x, y + bar_h)

            # Değer barı
            ratio = (angle - min_a) / (max_a - min_a)
            ratio = max(0.0, min(1.0, ratio))
            fill_x = bar_x + int(ratio * bar_w) - bar_w // 2
            fill_w = bar_w // 2 - fill_x + bar_x if fill_x < mid_x else int(ratio * bar_w) - bar_w // 2
            painter.fillRect(
                min(mid_x, bar_x + int(ratio * bar_w)), y + 2,
                abs(int(ratio * bar_w) - bar_w // 2), bar_h - 4,
                QColor(color)
            )

            # Değer yazısı
            painter.setPen(QColor(COLORS['text_primary']))
            painter.setFont(QFont('Courier New', 8, QFont.Weight.Bold))
            painter.drawText(bar_x, y + bar_h + 2, bar_w, 14,
                           Qt.AlignmentFlag.AlignRight,
                           f"{angle:+.1f}°")


# ==========================================
# HEDEF SIRASI PANELİ (Aşama 1)
# ==========================================
class TargetOrderPanel(QGroupBox):
    """
    Şartname gereği: Aşama 1'de zarf ile verilen hedef sırası.
    Takım bu sırayı buraya girer ve takip eder.
    """

    def __init__(self, parent=None):
        super().__init__("[ AŞAMA 1 - HEDEF SIRASI ]", parent)
        self.target_order = list(DEFAULT_TARGET_ORDER)
        self.current_index = 0
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        # Sıra listesi
        self.list_widget = QListWidget()
        self.list_widget.setMaximumHeight(130)
        self._refresh_list()
        layout.addWidget(self.list_widget)

        # Kontroller
        btn_row = QHBoxLayout()

        self.btn_confirm = QPushButton("✓ İMHA ONAYLA")
        self.btn_confirm.setStyleSheet(f"""
            QPushButton {{
                background: #002200;
                color: {COLORS['accent_green']};
                border: 1px solid {COLORS['accent_green']};
                font-size: 10px;
                padding: 5px;
            }}
        """)
        self.btn_confirm.clicked.connect(self._confirm_destroy)

        self.btn_reset = QPushButton("↺ SIFIRLA")
        self.btn_reset.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['bg_dark']};
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border']};
                font-size: 10px;
                padding: 5px;
            }}
        """)
        self.btn_reset.clicked.connect(self._reset)

        btn_row.addWidget(self.btn_confirm)
        btn_row.addWidget(self.btn_reset)
        layout.addLayout(btn_row)

        # Mevcut hedef göstergesi
        self.current_label = QLabel()
        self.current_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_current_label()
        layout.addWidget(self.current_label)

    def _refresh_list(self):
        self.list_widget.clear()
        for i, target_key in enumerate(self.target_order):
            info = TARGET_TYPES.get(target_key, TARGET_TYPES['unknown'])
            item = QListWidgetItem(f"  {i+1}. {info['label']}")
            if i < self.current_index:
                item.setForeground(QColor(COLORS['text_dim']))
                item.setText(f"  ✓ {i+1}. {info['label']}")
            elif i == self.current_index:
                item.setForeground(QColor(info['color']))
                item.setFont(QFont('Courier New', 10, QFont.Weight.Bold))
            else:
                item.setForeground(QColor(COLORS['text_secondary']))
            self.list_widget.addItem(item)

    def _update_current_label(self):
        if self.current_index < len(self.target_order):
            key = self.target_order[self.current_index]
            info = TARGET_TYPES[key]
            self.current_label.setText(
                f"<span style='color:{info['color']};font-weight:bold;font-size:11px;'>"
                f"► {info['label']}</span>"
                f"<span style='color:{COLORS['text_dim']};font-size:9px;'>"
                f"  [{info['min_range']}-{info['max_range']}m]</span>"
            )
            self.current_label.setTextFormat(Qt.TextFormat.RichText)
        else:
            self.current_label.setText(
                f"<span style='color:{COLORS['accent_green']};font-weight:bold;'>"
                f"✓ TÜM HEDEFLER İMHA EDİLDİ</span>"
            )

    def _confirm_destroy(self):
        if self.current_index < len(self.target_order):
            self.current_index += 1
            self._refresh_list()
            self._update_current_label()

    def _reset(self):
        self.current_index = 0
        self._refresh_list()
        self._update_current_label()

    def set_target_order(self, order: list):
        self.target_order = order
        self.current_index = 0
        self._refresh_list()
        self._update_current_label()

    def get_current_target(self):
        if self.current_index < len(self.target_order):
            return self.target_order[self.current_index]
        return None


# ==========================================
# YASAK BÖLGE PANELİ (Şartname Zorunluluğu)
# ==========================================
class ForbiddenZonePanel(QGroupBox):
    """
    Şartname: Harekete yasak alan ve atışa yasak alan tanımlama.
    Pan/Tilt açı sınırları olarak tanımlanır.
    """

    def __init__(self, parent=None):
        super().__init__("[ YASAK BÖLGE TANIMLAMA ]", parent)
        self._build_ui()

    def _build_ui(self):
        layout = QGridLayout(self)
        layout.setSpacing(6)

        # Harekete yasak alan
        layout.addWidget(self._make_label("HAREKETE YASAK"), 0, 0, 1, 2)

        self.chk_move_forbidden = QCheckBox("AKTİF")
        self.chk_move_forbidden.setStyleSheet(f"color: {COLORS['accent_orange']};")
        layout.addWidget(self.chk_move_forbidden, 0, 2)

        layout.addWidget(self._make_label("Pan Maks:"), 1, 0)
        self.spin_move_pan_max = self._make_spinbox(-180, 180, 170)
        layout.addWidget(self.spin_move_pan_max, 1, 1)
        layout.addWidget(self._make_label("°"), 1, 2)

        layout.addWidget(self._make_label("Tilt Maks:"), 2, 0)
        self.spin_move_tilt_max = self._make_spinbox(-45, 90, 85)
        layout.addWidget(self.spin_move_tilt_max, 2, 1)
        layout.addWidget(self._make_label("°"), 2, 2)

        # Ayırıcı
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {COLORS['border']};")
        layout.addWidget(line, 3, 0, 1, 3)

        # Atışa yasak alan
        layout.addWidget(self._make_label("ATIŞA YASAK"), 4, 0, 1, 2)

        self.chk_fire_forbidden = QCheckBox("AKTİF")
        self.chk_fire_forbidden.setStyleSheet(f"color: {COLORS['accent_red']};")
        layout.addWidget(self.chk_fire_forbidden, 4, 2)

        layout.addWidget(self._make_label("Pan Min:"), 5, 0)
        self.spin_fire_pan_min = self._make_spinbox(-180, 180, -30)
        layout.addWidget(self.spin_fire_pan_min, 5, 1)
        layout.addWidget(self._make_label("°"), 5, 2)

        layout.addWidget(self._make_label("Pan Maks:"), 6, 0)
        self.spin_fire_pan_max = self._make_spinbox(-180, 180, 30)
        layout.addWidget(self.spin_fire_pan_max, 6, 1)
        layout.addWidget(self._make_label("°"), 6, 2)

    def _make_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px;")
        return lbl

    def _make_spinbox(self, min_v, max_v, default):
        sb = QSpinBox()
        sb.setRange(min_v, max_v)
        sb.setValue(default)
        sb.setSuffix("°")
        return sb

    def is_move_forbidden(self, pan: float, tilt: float) -> bool:
        if not self.chk_move_forbidden.isChecked():
            return False
        return abs(pan) > self.spin_move_pan_max.value() or tilt > self.spin_move_tilt_max.value()

    def is_fire_forbidden(self, pan: float) -> bool:
        if not self.chk_fire_forbidden.isChecked():
            return False
        return self.spin_fire_pan_min.value() <= pan <= self.spin_fire_pan_max.value()


# ==========================================
# SİSTEM LOG PANELİ
# ==========================================
class SystemLogPanel(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("[ SİSTEM LOGU ]", parent)
        layout = QVBoxLayout(self)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        layout.addWidget(self.log_text)

    def log(self, message: str, level: str = "INFO"):
        colors = {
            "INFO":  COLORS['accent_cyan'],
            "OK":    COLORS['accent_green'],
            "WARN":  COLORS['accent_yellow'],
            "ERROR": COLORS['accent_red'],
        }
        color = colors.get(level, COLORS['text_secondary'])
        ts = time.strftime("%H:%M:%S")
        self.log_text.append(
            f'<span style="color:{COLORS["text_dim"]}">[{ts}]</span> '
            f'<span style="color:{color}">[{level}]</span> '
            f'<span style="color:{COLORS["text_primary"]}">{message}</span>'
        )
        # En alta kaydır
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


# ==========================================
# HEDEF SINIFLANDIRMA PANELİ (Yetenek 6)
# ==========================================
class ClassificationPanel(QGroupBox):
    """
    YOLO'dan gelen tespit sonuçlarını gösterir.
    Şartname Yetenek 6: F16, İHA, Mini/Micro İHA, Helikopter, Balistik Füze.
    """

    def __init__(self, parent=None):
        super().__init__("[ HEDEF SINIFLANDIRMA - YETENEĞİ 6 ]", parent)
        self._build_ui()
        self._current_detection = None

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        # Aktif tespit
        self.detection_label = QLabel("— TESPİT YOK —")
        self.detection_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detection_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_dim']};
                font-size: 13px;
                font-weight: bold;
                padding: 8px;
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                letter-spacing: 2px;
            }}
        """)
        layout.addWidget(self.detection_label)

        # Güven skoru bar
        conf_row = QHBoxLayout()
        conf_row.addWidget(QLabel("GÜVEN:"))
        self.conf_bar = QProgressBar()
        self.conf_bar.setRange(0, 100)
        self.conf_bar.setValue(0)
        self.conf_bar.setFormat("%p%")
        conf_row.addWidget(self.conf_bar)
        layout.addLayout(conf_row)

        # Menzil bilgisi
        self.range_label = QLabel("UYGUN MENZİL: —")
        self.range_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px;")
        self.range_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.range_label)

        # Dost/Düşman durumu
        self.friend_foe_label = QLabel("—")
        self.friend_foe_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.friend_foe_label.setStyleSheet(f"font-size: 12px; font-weight: bold; padding: 4px;")
        layout.addWidget(self.friend_foe_label)

    def update_detection(self, detection: dict):
        """Yeni tespit verisi geldiğinde çağrılır"""
        if not detection:
            self.detection_label.setText("— TESPİT YOK —")
            self.detection_label.setStyleSheet(f"""
                QLabel {{
                    color: {COLORS['text_dim']};
                    font-size: 13px;
                    font-weight: bold;
                    padding: 8px;
                    border: 1px solid {COLORS['border']};
                    border-radius: 4px;
                }}
            """)
            self.conf_bar.setValue(0)
            self.range_label.setText("UYGUN MENZİL: —")
            self.friend_foe_label.setText("—")
            return

        cls = detection.get('class_name', 'unknown')
        conf = detection.get('confidence', 0.0)
        is_friend = detection.get('is_friend', False)
        info = TARGET_TYPES.get(cls, TARGET_TYPES['unknown'])

        # Tespit etiketi
        self.detection_label.setText(info['label'])
        self.detection_label.setStyleSheet(f"""
            QLabel {{
                color: {info['color']};
                font-size: 13px;
                font-weight: bold;
                padding: 8px;
                border: 2px solid {info['color']};
                border-radius: 4px;
                letter-spacing: 2px;
            }}
        """)

        # Güven skoru
        self.conf_bar.setValue(int(conf * 100))

        # Menzil bilgisi
        if info['min_range'] >= 0:
            self.range_label.setText(
                f"UYGUN MENZİL: {info['min_range']}m – {info['max_range']}m"
            )
        else:
            self.range_label.setText("UYGUN MENZİL: —")

        # Dost/Düşman
        if is_friend:
            self.friend_foe_label.setText("◆ DOST UNSUR — ATEŞ ETME")
            self.friend_foe_label.setStyleSheet(
                f"font-size: 12px; font-weight: bold; padding: 4px; color: {COLORS['accent_green']};"
            )
        elif cls == 'unknown':
            self.friend_foe_label.setText("? TANIMSIZ")
            self.friend_foe_label.setStyleSheet(
                f"font-size: 12px; font-weight: bold; padding: 4px; color: {COLORS['text_dim']};"
            )
        else:
            self.friend_foe_label.setText("◆ DÜŞMAN HEDEF")
            self.friend_foe_label.setStyleSheet(
                f"font-size: 12px; font-weight: bold; padding: 4px; color: {COLORS['accent_red']};"
            )


# ==========================================
# ANA PENCERE
# ==========================================
class CelikKubbeMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ÇELİK KUBBE — HAVA SAVUNMA SİSTEMİ KONTROL MERKEZİ")
        self.setMinimumSize(1280, 800)
        self.setStyleSheet(STYLESHEET)

        # Durum değişkenleri
        self.current_mode = "MANUEL"   # "MANUEL" veya "OTONOM"
        self.system_armed = False
        self.emergency_active = False
        self.serial_connected = False
        self.pan_angle = 0.0
        self.tilt_angle = 0.0
        self.current_stage = 1         # Aktif aşama (1/2/3)

        self._build_ui()
        self._setup_shortcuts()
        self._setup_timer()

        self.log.log("Sistem başlatıldı", "OK")
        self.log.log("Arduino bağlantısı bekleniyor...", "WARN")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # --- ÜST BAR ---
        root.addWidget(self._build_header())

        # --- ANA İÇERİK ---
        content = QHBoxLayout()
        content.setSpacing(6)

        # Sol: Kamera
        content.addWidget(self._build_camera_panel(), stretch=6)

        # Sağ: Kontrol panelleri
        content.addWidget(self._build_right_panel(), stretch=4)

        root.addLayout(content, stretch=1)

        # --- ALT BAR ---
        root.addWidget(self._build_bottom_bar())

    def _build_header(self):
        frame = QFrame()
        frame.setObjectName("PanelFrame")
        frame.setMaximumHeight(56)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(14, 6, 14, 6)

        # Logo / Başlık
        title = QLabel("◈ ÇELİK KUBBE")
        title.setObjectName("LabelTitle")
        layout.addWidget(title)

        subtitle = QLabel("HAVA SAVUNMA SİSTEMİ — TEKNOFEST 2026")
        subtitle.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 10px; letter-spacing: 2px;"
        )
        layout.addWidget(subtitle)

        layout.addStretch()

        # Bağlantı durumu
        self.conn_label = QLabel("● BAĞLANTI YOK")
        self.conn_label.setObjectName("StatusERR")
        self.conn_label.setStyleSheet(
            f"color: {COLORS['accent_red']}; font-size: 11px; font-weight: bold;"
        )
        layout.addWidget(self.conn_label)

        layout.addSpacing(20)

        # Aktif aşama
        self.stage_label = QLabel("AŞAMA: 1")
        self.stage_label.setStyleSheet(
            f"color: {COLORS['accent_yellow']}; font-size: 11px; font-weight: bold;"
            f"border: 1px solid {COLORS['accent_yellow']}; padding: 3px 8px; border-radius: 3px;"
        )
        layout.addWidget(self.stage_label)

        layout.addSpacing(20)

        # Saat
        self.clock_label = QLabel()
        self.clock_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 11px;"
        )
        layout.addWidget(self.clock_label)

        return frame

    def _build_camera_panel(self):
        frame = QFrame()
        frame.setObjectName("PanelFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Kamera widget
        self.camera_widget = CameraWidget()
        self.camera_widget.target_clicked.connect(self._on_camera_click)
        layout.addWidget(self.camera_widget)

        # Alt kontrol barı
        cam_ctrl = QHBoxLayout()

        # Nişangah toggle
        self.chk_crosshair = QCheckBox("NİŞANGAH")
        self.chk_crosshair.setChecked(True)
        self.chk_crosshair.toggled.connect(
            lambda v: setattr(self.camera_widget, 'crosshair_visible', v)
        )
        cam_ctrl.addWidget(self.chk_crosshair)

        cam_ctrl.addStretch()

        # Motor göstergesi
        self.motor_gauge = MotorGaugeWidget()
        self.motor_gauge.setMinimumWidth(240)
        cam_ctrl.addWidget(self.motor_gauge)

        layout.addLayout(cam_ctrl)
        return frame

    def _build_right_panel(self):
        frame = QFrame()
        frame.setObjectName("PanelFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # 1. ACİL DURDUR (her zaman en üstte, en büyük)
        self.btn_emergency = QPushButton("⚠  ACİL DURDUR  ⚠")
        self.btn_emergency.setObjectName("BtnEmergency")
        self.btn_emergency.clicked.connect(self._emergency_stop)
        layout.addWidget(self.btn_emergency)

        # 2. MOD SEÇİMİ
        layout.addWidget(self._build_mode_panel())

        # 3. ATEŞ KONTROLÜ
        layout.addWidget(self._build_fire_panel())

        # 4. HEDEF SINIFLANDIRMA (Yetenek 6)
        self.classification_panel = ClassificationPanel()
        layout.addWidget(self.classification_panel)

        # 5. HEDEF SIRASI (Aşama 1)
        self.target_order_panel = TargetOrderPanel()
        layout.addWidget(self.target_order_panel)

        # 6. YASAK BÖLGE
        self.forbidden_zone = ForbiddenZonePanel()
        layout.addWidget(self.forbidden_zone)

        # 7. SİSTEM LOGU
        self.log = SystemLogPanel()
        layout.addWidget(self.log)

        return frame

    def _build_mode_panel(self):
        group = QGroupBox("[ ÇALIŞMA MODU ]")
        layout = QHBoxLayout(group)
        layout.setSpacing(6)

        self.btn_manual = QPushButton("◈ MANUEL")
        self.btn_manual.setObjectName("BtnModeManual")
        self.btn_manual.clicked.connect(lambda: self._set_mode("MANUEL"))

        self.btn_auto = QPushButton("◎ OTONOM")
        self.btn_auto.setObjectName("BtnModeAuto")
        self.btn_auto.clicked.connect(lambda: self._set_mode("OTONOM"))

        layout.addWidget(self.btn_manual)
        layout.addWidget(self.btn_auto)

        self._update_mode_buttons()
        return group

    def _build_fire_panel(self):
        group = QGroupBox("[ ATEŞLİ SİLAH KONTROLÜ ]")
        layout = QVBoxLayout(group)
        layout.setSpacing(6)

        # Kur / Devre dışı
        arm_row = QHBoxLayout()
        self.btn_arm = QPushButton("SİSTEMİ KUR")
        self.btn_arm.setStyleSheet(f"""
            QPushButton {{
                background: #001a10;
                color: {COLORS['accent_green']};
                border: 1px solid {COLORS['accent_green']};
                font-size: 10px;
                padding: 6px;
            }}
            QPushButton:checked {{
                background: #003020;
                border-width: 2px;
            }}
        """)
        self.btn_arm.setCheckable(True)
        self.btn_arm.toggled.connect(self._on_arm_toggle)
        arm_row.addWidget(self.btn_arm)

        self.arm_status = QLabel("DEVRE DIŞI")
        self.arm_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.arm_status.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px;")
        arm_row.addWidget(self.arm_status)
        layout.addLayout(arm_row)

        # Ateş butonu
        self.btn_fire = QPushButton("▶  ATEŞ  ◀")
        self.btn_fire.setObjectName("BtnFire")
        self.btn_fire.setEnabled(False)
        self.btn_fire.clicked.connect(self._fire)
        layout.addWidget(self.btn_fire)

        return group

    def _build_bottom_bar(self):
        frame = QFrame()
        frame.setObjectName("PanelFrame")
        frame.setMaximumHeight(44)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 4, 10, 4)

        # Aşama seçimi
        layout.addWidget(QLabel("AŞAMA:"))
        for i in range(1, 4):
            btn = QPushButton(f"  {i}  ")
            btn.setMaximumWidth(50)
            btn.clicked.connect(lambda _, s=i: self._set_stage(s))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['bg_card']};
                    color: {COLORS['text_secondary']};
                    border: 1px solid {COLORS['border']};
                    font-size: 11px;
                    padding: 4px;
                }}
            """)
            layout.addWidget(btn)

        layout.addStretch()

        # Pan/Tilt göstergesi
        self.pan_tilt_label = QLabel(f"PAN: +0.0°   TILT: +0.0°")
        self.pan_tilt_label.setStyleSheet(
            f"color: {COLORS['accent_cyan']}; font-size: 11px; font-family: 'Courier New';"
        )
        layout.addWidget(self.pan_tilt_label)

        layout.addSpacing(20)

        # HOME butonu
        btn_home = QPushButton("⌂ HOME")
        btn_home.clicked.connect(self._go_home)
        btn_home.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['bg_dark']};
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border']};
                font-size: 10px;
                padding: 4px 10px;
            }}
        """)
        layout.addWidget(btn_home)

        return frame

    # ==========================================
    # KLAVYE KISAYOLLARI
    # ==========================================
    def _setup_shortcuts(self):
        # Acil durdur: Space veya F1
        QShortcut(QKeySequence(Qt.Key.Key_Space), self).activated.connect(
            self._emergency_stop
        )
        QShortcut(QKeySequence(Qt.Key.Key_F1), self).activated.connect(
            self._emergency_stop
        )
        # Ateş: F (manuel modda)
        QShortcut(QKeySequence(Qt.Key.Key_F), self).activated.connect(self._fire)
        # Mod değiştirme
        QShortcut(QKeySequence(Qt.Key.Key_M), self).activated.connect(
            lambda: self._set_mode("OTONOM" if self.current_mode == "MANUEL" else "MANUEL")
        )
        # Home
        QShortcut(QKeySequence(Qt.Key.Key_H), self).activated.connect(self._go_home)

    # ==========================================
    # TIMER (UI güncellemeleri)
    # ==========================================
    def _setup_timer(self):
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self._update_ui)
        self.ui_timer.start(100)  # 10 Hz UI güncellemesi

    def _update_ui(self):
        # Saat
        self.clock_label.setText(time.strftime("%H:%M:%S"))

        # Motor açıları
        self.pan_tilt_label.setText(
            f"PAN: {self.pan_angle:+.1f}°   TILT: {self.tilt_angle:+.1f}°"
        )
        self.motor_gauge.set_angles(self.pan_angle, self.tilt_angle)
        self.camera_widget.pan_angle = self.pan_angle
        self.camera_widget.tilt_angle = self.tilt_angle

    # ==========================================
    # EYLEM FONKSİYONLARI
    # ==========================================
    def _emergency_stop(self):
        """
        Şartname zorunluluğu: Acil Durdur.
        Tüm hareketi ve ateşi durdurur.
        """
        self.emergency_active = True
        self.btn_fire.setEnabled(False)
        self.btn_arm.setChecked(False)

        # Buton rengi kırmızıya dön
        self.btn_emergency.setStyleSheet("""
            QPushButton#BtnEmergency {
                background-color: #8a0020;
                color: #ffffff;
                border: 3px solid #ff0040;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
                letter-spacing: 3px;
                min-height: 60px;
            }
        """)

        self.log.log("ACİL DURDUR AKTIVE EDİLDİ!", "ERROR")
        self.log.log("Tüm motorlar durduruldu", "WARN")

        # Seri porta gönder
        self._send_serial({"cmd": "STOP"})

        # 2 saniye sonra normal renge dön
        QTimer.singleShot(2000, self._reset_emergency_button)

    def _reset_emergency_button(self):
        self.emergency_active = False
        self.btn_emergency.setStyleSheet("")
        self.btn_emergency.setObjectName("BtnEmergency")
        self.btn_emergency.setStyleSheet(f"""
            QPushButton#BtnEmergency {{
                background-color: #3a0010;
                color: {COLORS['accent_red']};
                border: 2px solid {COLORS['accent_red']};
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
                letter-spacing: 3px;
                min-height: 60px;
            }}
        """)

    def _set_mode(self, mode: str):
        """Manuel / Otonom mod geçişi"""
        if self.emergency_active:
            self.log.log("Acil durdur aktifken mod değiştirilemez!", "WARN")
            return

        self.current_mode = mode
        self.camera_widget.mode_text = mode
        self._update_mode_buttons()

        # Ateş butonu sadece manuel modda
        can_fire = (mode == "MANUEL" and self.system_armed)
        self.btn_fire.setEnabled(can_fire)

        self.log.log(f"Mod değiştirildi: {mode}", "OK")
        self._send_serial({"cmd": "MODE", "mode": mode})

    def _update_mode_buttons(self):
        if self.current_mode == "MANUEL":
            self.btn_manual.setStyleSheet(f"""
                QPushButton {{
                    background: #003010;
                    color: {COLORS['accent_green']};
                    border: 2px solid {COLORS['accent_green']};
                    letter-spacing: 2px;
                    font-weight: bold;
                }}
            """)
            self.btn_auto.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['bg_card']};
                    color: {COLORS['text_secondary']};
                    border: 1px solid {COLORS['border']};
                    letter-spacing: 2px;
                }}
            """)
        else:
            self.btn_auto.setStyleSheet(f"""
                QPushButton {{
                    background: #000a25;
                    color: {COLORS['accent_blue']};
                    border: 2px solid {COLORS['accent_blue']};
                    letter-spacing: 2px;
                    font-weight: bold;
                }}
            """)
            self.btn_manual.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['bg_card']};
                    color: {COLORS['text_secondary']};
                    border: 1px solid {COLORS['border']};
                    letter-spacing: 2px;
                }}
            """)

    def _on_arm_toggle(self, armed: bool):
        self.system_armed = armed
        if armed:
            self.arm_status.setText("● KURULUᵕ")
            self.arm_status.setStyleSheet(f"color: {COLORS['accent_green']}; font-size: 10px;")
            if self.current_mode == "MANUEL":
                self.btn_fire.setEnabled(True)
            self.log.log("Sistem kuruldu", "WARN")
        else:
            self.arm_status.setText("DEVRE DIŞI")
            self.arm_status.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px;")
            self.btn_fire.setEnabled(False)
            self.log.log("Sistem devre dışı bırakıldı", "INFO")

    def _fire(self):
        """Ateş komutu"""
        if self.emergency_active:
            return
        if not self.system_armed:
            self.log.log("Sistem kurulu değil!", "WARN")
            return
        if self.current_mode != "MANUEL":
            self.log.log("Ateş komutu sadece MANUEL modda!", "WARN")
            return

        # Yasak bölge kontrolü
        if self.forbidden_zone.is_fire_forbidden(self.pan_angle):
            self.log.log(f"ATIŞA YASAK BÖLGE! Pan={self.pan_angle:.1f}°", "ERROR")
            return

        self.log.log("ATEŞ!", "WARN")
        self._send_serial({"cmd": "FIRE"})

    def _go_home(self):
        """Home pozisyonuna git"""
        self.log.log("HOME pozisyonuna gidiliyor...", "INFO")
        self._send_serial({"cmd": "HOME"})

    def _set_stage(self, stage: int):
        self.current_stage = stage
        self.stage_label.setText(f"AŞAMA: {stage}")
        self.log.log(f"Aşama {stage} aktif edildi", "INFO")

    def _on_camera_click(self, x: int, y: int):
        """Kameraya fare tıklaması — hedef kilitleme"""
        if self.current_mode == "MANUEL":
            self.log.log(f"Manuel hedef seçimi: ({x}, {y})", "INFO")

    # ==========================================
    # SERİAL HABERLEŞME (Stub — SerialCommunicator ile entegre edilecek)
    # ==========================================
    def _send_serial(self, data: dict):
        """
        Gerçek sistemde SerialCommunicator.send_command() çağrılır.
        Şu an sadece log'a yazar.
        """
        self.log.log(f"→ {json.dumps(data)}", "INFO")

    def set_serial_communicator(self, serial_comm):
        """main.py'deki SerialCommunicator nesnesini bağla"""
        self.serial_comm = serial_comm
        self.serial_connected = True
        self.conn_label.setText("● BAĞLANDI")
        self.conn_label.setStyleSheet(
            f"color: {COLORS['accent_green']}; font-size: 11px; font-weight: bold;"
        )
        self.log.log(f"Arduino bağlandı: {serial_comm.port}", "OK")

    def update_motor_position(self, pan: float, tilt: float):
        """Arduino'dan gelen pozisyon güncelleme"""
        self.pan_angle = pan
        self.tilt_angle = tilt

    def update_detection(self, detection: dict):
        """YOLO tespitini arayüze yansıt"""
        self.classification_panel.update_detection(detection)

    def update_camera_frame(self, frame: np.ndarray, detections: list, fps: float):
        """Kamera frame'ini güncelle"""
        self.camera_widget.update_frame(frame, detections, fps)

    # ==========================================
    # PENCERE KAPATMA
    # ==========================================
    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "Çıkış",
            "Sistemi kapatmak istiyor musunuz?\nMotorlar durdurulacak.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._emergency_stop()
            event.accept()
        else:
            event.ignore()


# ==========================================
# UYGULAMA GİRİŞ NOKTASI
# ==========================================
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Çelik Kubbe")

    window = CelikKubbeMainWindow()
    window.showMaximized()

    # Demo: Simüle motor hareketleri
    demo_timer = QTimer()
    t = [0.0]
    def demo_update():
        t[0] += 0.05
        pan = 45 * __import__('math').sin(t[0])
        tilt = 20 * __import__('math').sin(t[0] * 0.7)
        window.update_motor_position(pan, tilt)

        # Örnek tespit (demo)
        if int(t[0] * 2) % 6 < 3:
            window.update_detection({
                'class_name': 'iha',
                'confidence': 0.87,
                'is_friend': False,
                'bbox': (200, 150, 400, 300)
            })
        else:
            window.update_detection(None)

    demo_timer.timeout.connect(demo_update)
    demo_timer.start(100)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()