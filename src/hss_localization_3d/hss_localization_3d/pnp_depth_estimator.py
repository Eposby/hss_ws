#!/usr/bin/env python3
"""
HSS Aşama 2 - SolvePnP ve 3B Poz / Derinlik Kestirim Düğümü
-----------------------------------------------------------
Bu düğüm, 2B tespit kutularını (Bounding Box) ve bilinen hedef CAD ölçülerini
kullanarak OpenCV solvePnP ve Monoküler Dikey Geometri benzerliği ile hedefin
3B uzaydaki gerçek metrik koordinatlarını (X, Y, Z), menzilini ve açılarını hesaplar.
"""

import math
import numpy as np
import cv2
import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Point
from hss_interfaces.msg import Detection2D, Detection2DArray, Target3D

# Geriye dönük uyumluluk için celikkubbe_msgs varsa import edelim
try:
    from celikkubbe_msgs.msg import TargetInfo
    HAS_CELIKKUBBE_MSGS = True
except ImportError:
    HAS_CELIKKUBBE_MSGS = False


class PnPDepthEstimator(Node):
    def __init__(self):
        super().__init__('pnp_depth_estimator')

        # Parametre Tanımlamaları
        self.declare_parameter('camera.fx', 620.0)
        self.declare_parameter('camera.fy', 620.0)
        self.declare_parameter('camera.cx', 320.0)
        self.declare_parameter('camera.cy', 240.0)
        self.declare_parameter('camera.frame_id', 'camera_optical_frame')

        # Hedef gerçek dünya CAD ölçüleri (metre) [Genişlik (X), Yükseklik (Y), Uzunluk (Z)]
        self.target_dimensions = {
            'iha': {'w': 0.40, 'h': 0.20, 'l': 0.40},
            'f16': {'w': 0.50, 'h': 0.15, 'l': 0.70},
            'balon': {'w': 0.25, 'h': 0.25, 'l': 0.25},
            'helikopter': {'w': 0.45, 'h': 0.25, 'l': 0.50},
            'balistik_fuze': {'w': 0.12, 'h': 0.65, 'l': 0.12},
            'default': {'w': 0.35, 'h': 0.20, 'l': 0.35}
        }

        self.fx = self.get_parameter('camera.fx').value
        self.fy = self.get_parameter('camera.fy').value
        self.cx = self.get_parameter('camera.cx').value
        self.cy = self.get_parameter('camera.cy').value
        self.frame_id = self.get_parameter('camera.frame_id').value

        # Kamera Matrisi K ve Distorsiyon Katsayıları
        self.camera_matrix = np.array([
            [self.fx, 0.0, self.cx],
            [0.0, self.fy, self.cy],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)
        self.dist_coeffs = np.zeros((5, 1), dtype=np.float64)

        # Publisher
        self.target_3d_pub = self.create_publisher(Target3D, '/localization/target_3d', 10)

        # Subscribers
        self.sub_detections = self.create_subscription(
            Detection2DArray,
            '/perception/detections',
            self.detections_callback,
            10
        )

        if HAS_CELIKKUBBE_MSGS:
            self.sub_legacy = self.create_subscription(
                TargetInfo,
                '/tespit/hedef_bilgisi',
                self.legacy_target_callback,
                10
            )

        self.get_logger().info(
            f'PnP 3B Konumlama Düğümü başlatıldı. fx={self.fx}, fy={self.fy}, cx={self.cx}, cy={self.cy}'
        )

    def get_target_dim(self, class_name: str):
        key = class_name.lower().strip()
        return self.target_dimensions.get(key, self.target_dimensions['default'])

    def estimate_pose_pnp(self, class_name: str, bbox_x: int, bbox_y: int, bbox_w: int, bbox_h: int):
        """
        OpenCV solvePnP kullanarak hedefin 3B rotasyon ve öteleme vektörünü hesaplar.
        """
        dim = self.get_target_dim(class_name)
        w, h = dim['w'], dim['h']

        # Hedef koordinat çerçevesinde 3B köşe noktaları (Merkez orijin)
        # Sol-Üst, Sağ-Üst, Sağ-Alt, Sol-Alt
        obj_points = np.array([
            [-w / 2.0, -h / 2.0, 0.0],
            [ w / 2.0, -h / 2.0, 0.0],
            [ w / 2.0,  h / 2.0, 0.0],
            [-w / 2.0,  h / 2.0, 0.0]
        ], dtype=np.float64)

        # Görüntüdeki karşılık gelen 2B piksel köşeleri
        img_points = np.array([
            [float(bbox_x), float(bbox_y)],
            [float(bbox_x + bbox_w), float(bbox_y)],
            [float(bbox_x + bbox_w), float(bbox_y + bbox_h)],
            [float(bbox_x), float(bbox_y + bbox_h)]
        ], dtype=np.float64)

        success, rvec, tvec = cv2.solvePnP(
            obj_points,
            img_points,
            self.camera_matrix,
            self.dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )

        if success and tvec[2][0] > 0.1:
            X = float(tvec[0][0])
            Y = float(tvec[1][0])
            Z = float(tvec[2][0])
            return X, Y, Z, 'solve_pnp'

        # PnP başarısız olursa dikey monoküler benzerlik yöntemine geç
        return self.estimate_pose_monocular(class_name, bbox_x, bbox_y, bbox_w, bbox_h)

    def estimate_pose_monocular(self, class_name: str, bbox_x: int, bbox_y: int, bbox_w: int, bbox_h: int):
        """
        Dikey yükseklik benzerliği ve optik merkez izdüşümü ile mesafe ve (X, Y, Z) hesabı.
        Z = (fy * real_height) / bbox_height
        """
        dim = self.get_target_dim(class_name)
        real_h = max(dim['h'], 0.10)
        pixel_h = max(bbox_h, 2)

        # Derinlik (Z ekseni mesafesi - metre)
        Z = (self.fy * real_h) / float(pixel_h)

        # Piksel merkezleri
        cx_pix = bbox_x + (bbox_w / 2.0)
        cy_pix = bbox_y + (bbox_h / 2.0)

        # Metrik koordinat izdüşümü
        X = ((cx_pix - self.cx) * Z) / self.fx
        Y = ((cy_pix - self.cy) * Z) / self.fy

        return float(X), float(Y), float(Z), 'monocular_focal'

    def process_and_publish(self, target_id: int, class_name: str, color: str,
                            is_friendly: bool, confidence: float,
                            bbox_x: int, bbox_y: int, bbox_w: int, bbox_h: int,
                            stamp):
        if bbox_w <= 2 or bbox_h <= 2:
            return

        X, Y, Z, method = self.estimate_pose_pnp(class_name, bbox_x, bbox_y, bbox_w, bbox_h)

        # Radyal menzil R = sqrt(X^2 + Y^2 + Z^2)
        range_m = math.sqrt(X**2 + Y**2 + Z**2)

        # Açısal sapmalar (Derece)
        # Azimuth (Yatay Yaw): X pozitif sağa, Z ileri
        azimuth_deg = math.degrees(math.atan2(X, Z))
        # Elevation (Dikey Pitch): Y pozitif aşağı (kamera ekseni), bu yüzden -Y yukarı
        elevation_deg = math.degrees(math.atan2(-Y, math.sqrt(X**2 + Z**2)))

        # Target3D mesajı oluşturma
        msg = Target3D()
        msg.header.stamp = stamp
        msg.header.frame_id = self.frame_id
        msg.target_id = target_id
        msg.class_name = class_name
        msg.color = color
        msg.is_friendly = is_friendly
        msg.position.x = X
        msg.position.y = Y
        msg.position.z = Z
        msg.range_m = range_m
        msg.azimuth_deg = azimuth_deg
        msg.elevation_deg = elevation_deg
        msg.confidence = confidence
        msg.estimation_method = method

        self.target_3d_pub.publish(msg)

    def detections_callback(self, msg: Detection2DArray):
        stamp = msg.header.stamp
        for idx, det in enumerate(msg.detections):
            self.process_and_publish(
                target_id=idx + 1,
                class_name=det.class_name,
                color=det.color,
                is_friendly=det.is_friendly,
                confidence=det.confidence,
                bbox_x=det.bbox_x,
                bbox_y=det.bbox_y,
                bbox_w=det.bbox_width,
                bbox_h=det.bbox_height,
                stamp=stamp
            )

    def legacy_target_callback(self, msg):
        """Mevcut celikkubbe_msgs/TargetInfo mesajları için köprü."""
        self.process_and_publish(
            target_id=getattr(msg, 'target_id', 1),
            class_name=getattr(msg, 'target_type', 'iha'),
            color=getattr(msg, 'target_color', 'kirmizi'),
            is_friendly=getattr(msg, 'is_friendly', False),
            confidence=getattr(msg, 'confidence', 0.85),
            bbox_x=getattr(msg, 'bbox_x_min', 0),
            bbox_y=getattr(msg, 'bbox_y_min', 0),
            bbox_w=getattr(msg, 'bbox_width', 50),
            bbox_h=getattr(msg, 'bbox_height', 50),
            stamp=self.get_clock().now().to_msg()
        )


def main(args=None):
    rclpy.init(args=args)
    node = PnPDepthEstimator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
