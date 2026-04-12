#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from celikkubbe_msgs.msg import MotorSetpoint, MotorFeedback

from celikkubbe_ros2.communication.serial_comm import SerialCommunicator, MotorCommand

class DonanimDugumu(Node):
    def __init__(self):
        super().__init__('donanim_dugumu')
        
        self.declare_parameter('port', '/dev/ttyUSB0')
        self.declare_parameter('baudrate', 115200)
        self.declare_parameter('auto_reconnect', True)
        
        port = self.get_parameter('port').value
        baudrate = self.get_parameter('baudrate').value
        auto_reconnect = self.get_parameter('auto_reconnect').value
        
        self.serial = SerialCommunicator(
            port=port,
            baudrate=baudrate,
            auto_reconnect=auto_reconnect
        )
        
        if not self.serial.connect():
            self.get_logger().warning("Serial bağlantı kurulamadı, simülasyon modunda devam ediliyor...")
        else:
            self.serial.start_reading()
            self.get_logger().info(f"Serial bağlantı kuruldu: {port}")
            
        self.subscription = self.create_subscription(
            MotorSetpoint,
            '/kontrol/motor_komutu',
            self.motor_cmd_callback,
            10
        )
        
        self.feedback_pub = self.create_publisher(MotorFeedback, '/donanim/motor_geri_bildirim', 10)
        
        # Publish feedback periodically (or base it on serial read callback in real hardware)
        self.timer = self.create_timer(0.1, self.publish_feedback)

    def publish_feedback(self):
        feedback = MotorFeedback()
        # In a real implementation we would read from self.serial
        feedback.current_pan_angle = 0.0
        feedback.current_tilt_angle = 0.0
        feedback.current_pan_steps = 0
        feedback.current_tilt_steps = 0
        feedback.estimated_range = 10.0 # simulated 10m range
        feedback.is_moving = False
        feedback.is_homed = True
        
        self.feedback_pub.publish(feedback)

    def motor_cmd_callback(self, msg: MotorSetpoint):
        if self.serial and self.serial.is_connected():
            cmd = MotorCommand(
                pan_steps=msg.pan_steps,
                tilt_counts=msg.tilt_steps,
                pan_speed=msg.pan_speed,
                tilt_speed=msg.tilt_speed
            )
            self.serial.send_command(cmd)

    def destroy_node(self):
        if hasattr(self, 'serial') and self.serial:
            self.serial.disconnect()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = DonanimDugumu()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
