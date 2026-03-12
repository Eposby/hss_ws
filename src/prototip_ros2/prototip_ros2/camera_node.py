#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

from prototip_ros2.camera.capture import CameraCapture

class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')
        
        # ROS 2 Parametreleri
        self.declare_parameter('camera_id', 0)
        self.declare_parameter('width', 640)
        self.declare_parameter('height', 480)
        self.declare_parameter('fps', 30)
        self.declare_parameter('use_picamera', False)
        self.declare_parameter('stream_url', '')

        # Parametreleri al
        cam_id = self.get_parameter('camera_id').value
        w = self.get_parameter('width').value
        h = self.get_parameter('height').value
        fps = self.get_parameter('fps').value
        use_pi = self.get_parameter('use_picamera').value
        stream_url = self.get_parameter('stream_url').value
        stream_url = stream_url if stream_url else None
        
        # Kamera Nesnesi
        self.camera = CameraCapture(
            camera_id=cam_id, width=w, height=h, fps=fps,
            use_picamera=use_pi, stream_url=stream_url
        )
        
        if not self.camera.start():
            self.get_logger().error("Kamera başlatılamadı!")
            return
            
        self.get_logger().info("Kamera başlatıldı.")
        
        self.publisher_ = self.create_publisher(Image, '~/image_raw', 10)
        self.bridge = CvBridge()
        
        # Timer (FPS bazlı)
        timer_period = 1.0 / fps
        self.timer = self.create_timer(timer_period, self.timer_callback)

    def timer_callback(self):
        ret, frame = self.camera.read()
        if not ret:
            self.get_logger().warning("Frame okunamadı!")
            return
            
        # Görüntüyü ROS 2 Image mesajına çevir ve yayınla
        msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'camera_link'
        self.publisher_.publish(msg)

    def destroy_node(self):
        if hasattr(self, 'camera'):
            self.camera.stop()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
