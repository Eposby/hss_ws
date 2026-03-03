#!/usr/bin/env python3
"""
Basit Balon Tespit Node'u
Kameradan görüntü alır ve kırmızı/mavi balonları tespit eder
"""

import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String

try:
    from cv_bridge import CvBridge
    HAS_CV_BRIDGE = True
except ImportError:
    HAS_CV_BRIDGE = False

from ..state_machine.machine import StateMachine
from ..state_machine import State
from ..state_machine import state_scanning


class BalloonDetectorNode(Node):
    """
    Basit Balon Tespit ROS2 Node
    
    Subscribers:
        /camera/image_raw - Kamera görüntüsü
        /hss/command - Komutlar (START, STOP)
    
    Publishers:
        /hss/state - Mevcut state
        /hss/balloons - Tespit edilen balonlar
        /hss/image_annotated - İşaretlenmiş görüntü
    """
    
    def __init__(self):
        super().__init__('balloon_detector')
        
        # State Machine
        self.sm = StateMachine(State.IDLE)
        
        # CV Bridge
        if HAS_CV_BRIDGE:
            self.bridge = CvBridge()
        
        # Publishers
        self.state_pub = self.create_publisher(String, '/hss/state', 10)
        self.balloon_pub = self.create_publisher(String, '/hss/balloons', 10)
        
        if HAS_CV_BRIDGE:
            self.image_pub = self.create_publisher(Image, '/hss/image_annotated', 10)
        
        # Subscribers
        self.image_sub = self.create_subscription(
            Image, '/camera/image_raw',
            self.image_callback, 10
        )
        self.cmd_sub = self.create_subscription(
            String, '/hss/command',
            self.command_callback, 10
        )
        
        # Timer (10 Hz)
        self.timer = self.create_timer(0.1, self.update_loop)
        
        self.get_logger().info('Balon Tespit Node başlatıldı')
        self.get_logger().info('Komutlar: START, STOP')
    
    def image_callback(self, msg):
        """Kamera görüntüsü callback"""
        if HAS_CV_BRIDGE:
            try:
                frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
                self.sm.set_frame(frame)
            except Exception as e:
                self.get_logger().error(f'Görüntü hatası: {e}')
    
    def command_callback(self, msg):
        """Komut callback"""
        cmd = msg.data.upper().strip()
        
        if cmd == 'START':
            self.sm.start()
            self.get_logger().info('Sistem BAŞLATILDI')
        elif cmd == 'STOP':
            self.sm.stop()
            self.get_logger().info('Sistem DURDURULDU')
    
    def update_loop(self):
        """Ana döngü"""
        # State machine güncelle
        current_state = self.sm.update()
        
        # State yayınla
        state_msg = String()
        state_msg.data = current_state.name
        self.state_pub.publish(state_msg)
        
        # Balonları yayınla
        balloons = self.sm.get_balloons()
        balloon_msg = String()
        balloon_msg.data = f"red:{len(balloons['red'])},blue:{len(balloons['blue'])}"
        self.balloon_pub.publish(balloon_msg)
        
        # İşaretlenmiş görüntü yayınla
        if HAS_CV_BRIDGE and 'frame' in self.sm.context:
            frame = self.sm.context['frame']
            annotated = state_scanning.draw_detections(frame, balloons)
            img_msg = self.bridge.cv2_to_imgmsg(annotated, 'bgr8')
            self.image_pub.publish(img_msg)


def main(args=None):
    rclpy.init(args=args)
    node = BalloonDetectorNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
