#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from prototip_msgs.msg import TargetInfo
from cv_bridge import CvBridge

from prototip_ros2.detection.yolo_detector import YOLODetector

class DetectionNode(Node):
    def __init__(self):
        super().__init__('detection_node')
        
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
            '/camera/image_raw',
            self.image_callback,
            10
        )
        self.target_pub = self.create_publisher(TargetInfo, '~/target_info', 10)
        self.annotated_pub = self.create_publisher(Image, '~/annotated_image', 10)

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        
        # Frame merkezi hesaplama (CameraCapture get_center benzeri)
        h, w = frame.shape[:2]
        frame_center = (w // 2, h // 2)
        
        annotated, detections = self.detector.detect_and_draw(frame)
        target = self.detector.get_primary_target(detections)
        
        target_msg = TargetInfo()
        if target:
            error_x, error_y = self.detector.calculate_error(target, frame_center)
            target_msg.is_tracked = True
            target_msg.error_x = int(error_x)
            target_msg.error_y = int(error_y)
            target_msg.target_class = target.class_name
        else:
            target_msg.is_tracked = False
            target_msg.error_x = 0
            target_msg.error_y = 0
            target_msg.target_class = ""
            
        self.target_pub.publish(target_msg)
        
        # Annotated görüntüyü de yayınlayalım
        annotated_msg = self.bridge.cv2_to_imgmsg(annotated, encoding='bgr8')
        annotated_msg.header = msg.header
        self.annotated_pub.publish(annotated_msg)

def main(args=None):
    rclpy.init(args=args)
    node = DetectionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
