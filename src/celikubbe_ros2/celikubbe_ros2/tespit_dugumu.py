#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from celikubbe_msgs.msg import TargetInfo
from cv_bridge import CvBridge
import cv2
import numpy as np

from celikubbe_ros2.detection.yolo_detector import YOLODetector

class TespitDugumu(Node):
    def __init__(self):
        super().__init__('tespit_dugumu')
        
        # Parametreler
        self.declare_parameter('model_path', 'yolov8n.pt')
        self.declare_parameter('confidence', 0.5)
        self.declare_parameter('device', 'auto')
        self.declare_parameter('target_classes', [])
        
        model_path = self.get_parameter('model_path').value
        conf = self.get_parameter('confidence').value
        device = self.get_parameter('device').value
        target_classes = self.get_parameter('target_classes').value
        
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
        self.subscription = self.create_subscription(
            Image,
            '/kamera/ham_goruntu',
            self.image_callback,
            10
        )
        self.target_pub = self.create_publisher(TargetInfo, '/tespit/hedef_bilgisi', 10)
        self.annotated_pub = self.create_publisher(Image, '/tespit/isaretli_goruntu', 10)

    def detect_color(self, frame, bbox):
        x1, y1, x2, y2 = bbox
        # Sınırları kontrol et
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(frame.shape[1], x2)
        y2 = min(frame.shape[0], y2)
        
        if x2 <= x1 or y2 <= y1:
            return "bilinmiyor"

        roi = frame[y1:y2, x1:x2]
        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # Kırmızı maskeleri
        lower_red1 = np.array([0, 70, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 70, 50])
        upper_red2 = np.array([180, 255, 255])
        mask_red1 = cv2.inRange(hsv_roi, lower_red1, upper_red1)
        mask_red2 = cv2.inRange(hsv_roi, lower_red2, upper_red2)
        mask_red = cv2.bitwise_or(mask_red1, mask_red2)
        
        # Mavi maskesi
        lower_blue = np.array([100, 150, 0])
        upper_blue = np.array([140, 255, 255])
        mask_blue = cv2.inRange(hsv_roi, lower_blue, upper_blue)
        
        red_pixels = cv2.countNonZero(mask_red)
        blue_pixels = cv2.countNonZero(mask_blue)
        
        if red_pixels > blue_pixels and red_pixels > 50:
            return "kirmizi"
        elif blue_pixels > red_pixels and blue_pixels > 50:
            return "mavi"
        return "bilinmiyor"

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        
        h, w = frame.shape[:2]
        frame_center = (w // 2, h // 2)
        
        annotated, detections = self.detector.detect_and_draw(frame)
        target = self.detector.get_primary_target(detections)
        
        target_msg = TargetInfo()
        if target:
            error_x, error_y = self.detector.calculate_error(target, frame_center)
            target_color = self.detect_color(frame, target.bbox)
            
            target_msg.is_tracked = True
            target_msg.target_type = target.class_name
            target_msg.target_color = target_color
            target_msg.confidence = float(target.confidence)
            target_msg.pixel_x = int(target.center[0])
            target_msg.pixel_y = int(target.center[1])
            target_msg.bbox_width = int(target.bbox[2] - target.bbox[0])
            target_msg.bbox_height = int(target.bbox[3] - target.bbox[1])
            target_msg.error_x = int(error_x)
            target_msg.error_y = int(error_y)
            target_msg.is_friendly = (target_color == "mavi")
            target_msg.target_id = int(target.class_id)
        else:
            target_msg.is_tracked = False
            
        self.target_pub.publish(target_msg)
        
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
