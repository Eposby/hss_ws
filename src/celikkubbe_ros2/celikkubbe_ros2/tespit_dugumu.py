#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from celikkubbe_msgs.msg import TargetInfo, TargetInfoArray
from cv_bridge import CvBridge
import cv2
import numpy as np

from celikkubbe_ros2.detection.yolo_detector import YOLODetector, RangeEstimator
from celikkubbe_ros2.detection.color_classifier import VehicleColorClassifier

class TespitDugumu(Node):
    def __init__(self):
        super().__init__('tespit_dugumu')
        
        # YOLO Parametreleri
        self.declare_parameter('model_path', 'yolov8n.pt')
        self.declare_parameter('confidence', 0.5)
        self.declare_parameter('device', 'auto')
        self.declare_parameter('target_classes', [])
        
        # Kamera ve Estimator Parametreleri
        self.declare_parameter('camera.width', 640)
        self.declare_parameter('camera.fov_horizontal', 60.0)
        self.declare_parameter('turret.known_target_size_m', 0.50)
        self.declare_parameter('turret.drone_target_size_m', 0.30)
        
        # Engagement Parametreleri
        self.declare_parameter('engagement_rules.f16_min_range', 5.0)
        self.declare_parameter('engagement_rules.f16_max_range', 15.0)
        self.declare_parameter('engagement_rules.default_min_range', 0.0)
        self.declare_parameter('engagement_rules.default_max_range', 15.0)
        
        # Friend Foe Colors
        self.declare_parameter('friend_foe.friendly_colors', ["mavi", "yesil"])
        self.declare_parameter('friend_foe.enemy_colors', ["kirmizi"])
        
        model_path = self.get_parameter('model_path').value
        conf = self.get_parameter('confidence').value
        device = self.get_parameter('device').value
        target_classes = self.get_parameter('target_classes').value
        
        cam_w = self.get_parameter('camera.width').value
        cam_fov = self.get_parameter('camera.fov_horizontal').value
        sz_default = self.get_parameter('turret.known_target_size_m').value
        sz_drone = self.get_parameter('turret.drone_target_size_m').value
        
        known_sizes = {
            "default": sz_default,
            "f16": sz_default,
            "helikopter": sz_default,
            "balistik_fuze": sz_default,
            "iha": sz_drone,
            "drone": sz_drone
        }
        
        self.range_estimator = RangeEstimator(cam_w, cam_fov, known_sizes)
        
        # Engagement Rules Dict
        self.engagement_rules = {
            "f16": (self.get_parameter('engagement_rules.f16_min_range').value, self.get_parameter('engagement_rules.f16_max_range').value),
            "default": (self.get_parameter('engagement_rules.default_min_range').value, self.get_parameter('engagement_rules.default_max_range').value)
        }
        
        friendly_colors = self.get_parameter('friend_foe.friendly_colors').value
        enemy_colors = self.get_parameter('friend_foe.enemy_colors').value
        self.color_classifier = VehicleColorClassifier(friendly_colors=friendly_colors, enemy_colors=enemy_colors)
        
        self.detector = YOLODetector(
            model_path=model_path,
            confidence_threshold=conf,
            target_classes=target_classes,
            device=device
        )
        
        if not self.detector.load_model():
            self.get_logger().error("YOLO Modeli yüklenemedi!")
            return
            
        self.get_logger().info("YOLO Modeli başarıyla yüklendi.")
        self.bridge = CvBridge()
        
        # Subscriber and Publishers
        self.subscription = self.create_subscription(Image, '/kamera/ham_goruntu', self.image_callback, 10)
        self.target_pub = self.create_publisher(TargetInfo, '/tespit/hedef_bilgisi', 10)
        self.array_pub = self.create_publisher(TargetInfoArray, '/tespit/tum_hedefler', 10)
        self.annotated_pub = self.create_publisher(Image, '/tespit/isaretli_goruntu', 10)

    def get_red_mask(self, hsv_img):
        # Kırmızı HSV maskeleri (wrap-around: 0-10 ve 170-180)
        lower_red1 = np.array([0, 70, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 70, 50])
        upper_red2 = np.array([180, 255, 255])
        mask_red1 = cv2.inRange(hsv_img, lower_red1, upper_red1)
        mask_red2 = cv2.inRange(hsv_img, lower_red2, upper_red2)
        return cv2.bitwise_or(mask_red1, mask_red2)

    def detect_balloon_bbox(self, frame, bbox):
        """
        YOLO bbox'ının alt kısmında bağımsız kırmızı balon sınır kutusu bul.
        Returns:
            (balloon_cx, balloon_cy, bx1, by1, bx2, by2) or None
        """
        x1, y1, x2, y2 = bbox
        h_bbox = y2 - y1
        
        if h_bbox <= 0:
            return None
            
        # Alt %40 ROI (balon bölgesi + taşma payı)
        roi_y_start = max(0, y2 - int(h_bbox * 0.40))
        roi_y_end = min(frame.shape[0], y2 + int(h_bbox * 0.15))
        x1_roi = max(0, x1)
        x2_roi = min(frame.shape[1], x2)
        
        if x2_roi <= x1_roi or roi_y_end <= roi_y_start:
            return None
            
        roi = frame[roi_y_start:roi_y_end, x1_roi:x2_roi]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = self.get_red_mask(hsv)
        
        # Morfolojik temizlik
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
            
        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) < 100:  # minimum alan
            return None
            
        bx, by, bw, bh = cv2.boundingRect(largest)
        
        abs_x1 = x1_roi + bx
        abs_y1 = roi_y_start + by
        abs_x2 = abs_x1 + bw
        abs_y2 = abs_y1 + bh
        cx = (abs_x1 + abs_x2) // 2
        cy = (abs_y1 + abs_y2) // 2
        
        return (cx, cy, abs_x1, abs_y1, abs_x2, abs_y2)

    def to_target_msg(self, det, frame_center, target_id=0):
        msg = TargetInfo()
        msg.is_tracked = True
        msg.target_type = det.class_name
        msg.confidence = float(det.confidence)
        msg.pixel_x = int(det.center[0])
        msg.pixel_y = int(det.center[1])
        msg.bbox_width = int(det.bbox[2] - det.bbox[0])
        msg.bbox_height = int(det.bbox[3] - det.bbox[1])
        msg.bbox_x_min = int(det.bbox[0])
        msg.bbox_y_min = int(det.bbox[1])
        msg.bbox_x_max = int(det.bbox[2])
        msg.bbox_y_max = int(det.bbox[3])
        msg.target_id = target_id
        msg.estimated_range_m = float(det.estimated_range_m)
        msg.vehicle_color = det.vehicle_color
        msg.is_friendly = det.is_friendly
        msg.has_balloon = det.has_balloon
        
        if det.has_balloon and det.balloon_bbox:
            msg.balloon_detected = True
            msg.balloon_cx, msg.balloon_cy = det.balloon_center
            msg.balloon_bbox_x_min, msg.balloon_bbox_y_min = det.balloon_bbox[0], det.balloon_bbox[1]
            msg.balloon_bbox_x_max, msg.balloon_bbox_y_max = det.balloon_bbox[2], det.balloon_bbox[3]
            
            aim_x = msg.balloon_cx
            aim_y = msg.balloon_cy
        else:
            msg.balloon_detected = False
            aim_x = (msg.bbox_x_min + msg.bbox_x_max) // 2
            aim_y = msg.bbox_y_max
            
        msg.aim_x = aim_x
        msg.aim_y = aim_y
        msg.error_x = aim_x - frame_center[0]
        msg.error_y = aim_y - frame_center[1]
        
        return msg

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        h, w = frame.shape[:2]
        frame_center = (w // 2, h // 2)
        
        annotated = frame.copy()
        raw_detections = self.detector.detect(frame)
        
        processed_detections = []
        target_msgs = []
        
        for i, det in enumerate(raw_detections):
            # 1. Mesafe tahmini
            h_px = det.bbox[3] - det.bbox[1]
            det.estimated_range_m = self.range_estimator.estimate(det.class_name, h_px)
            
            # 2. Balon Bbox Tespiti
            balloon_data = self.detect_balloon_bbox(frame, det.bbox)
            if balloon_data:
                det.has_balloon = True
                det.balloon_center = (balloon_data[0], balloon_data[1])
                det.balloon_bbox = (balloon_data[2], balloon_data[3], balloon_data[4], balloon_data[5])
            else:
                det.has_balloon = False
                
            # 3. Renk ve Dost/Düşman Sınıflandırma
            dom_col, is_friend = self.color_classifier.classify(frame, det.bbox, det.balloon_bbox)
            det.vehicle_color = dom_col
            det.is_friendly = is_friend
            
            processed_detections.append(det)
            target_msgs.append(self.to_target_msg(det, frame_center, target_id=i))
            
            # Çizimler
            color = (255, 0, 0) if is_friend else (0, 0, 255)
            cv2.rectangle(annotated, (det.bbox[0], det.bbox[1]), (det.bbox[2], det.bbox[3]), color, 2)
            cv2.putText(annotated, f"{det.class_name}:{det.estimated_range_m:.1f}m - {dom_col}", (det.bbox[0], det.bbox[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            if det.has_balloon:
                bx1, by1, bx2, by2 = det.balloon_bbox
                cv2.rectangle(annotated, (bx1, by1), (bx2, by2), (0, 255, 255), 2)
                cv2.drawMarker(annotated, det.balloon_center, (0, 165, 255), cv2.MARKER_CROSS, 15, 2)
        
        # Tüm hedefleri yayınla
        array_msg = TargetInfoArray()
        array_msg.targets = target_msgs
        self.array_pub.publish(array_msg)
        
        # Priority Hedefi Bul
        priority_det = self.detector.get_priority_target(processed_detections, self.engagement_rules)
        priority_msg = TargetInfo()
        if priority_det:
            priority_msg = self.to_target_msg(priority_det, frame_center, target_id=999)
            
            # Priorty için AIM çizimi (diğerlerinden farkı görmek için)
            cv2.circle(annotated, (priority_msg.aim_x, priority_msg.aim_y), 8, (0, 255, 0), -1)
            cv2.putText(annotated, "PRIORITY", (priority_msg.bbox_x_max, priority_msg.bbox_y_min), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            priority_msg.is_tracked = False
            
        self.target_pub.publish(priority_msg)
        
        annotated_msg = self.bridge.cv2_to_imgmsg(annotated, encoding='bgr8')
        annotated_msg.header = msg.header
        self.annotated_pub.publish(annotated_msg)

def main(args=None):
    rclpy.init(args=args)
    node = TespitDugumu()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
