#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from prototip_msgs.msg import MotorCmd

from prototip_ros2.communication.serial_comm import SerialCommunicator, MotorCommand

class SerialNode(Node):
    def __init__(self):
        super().__init__('serial_node')
        
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
            MotorCmd,
            '/control/motor_command',
            self.motor_cmd_callback,
            10
        )

    def motor_cmd_callback(self, msg: MotorCmd):
        if self.serial and self.serial.is_connected():
            cmd = MotorCommand(
                pan_steps=msg.pan_steps,
                tilt_counts=msg.tilt_counts,
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
    node = SerialNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
