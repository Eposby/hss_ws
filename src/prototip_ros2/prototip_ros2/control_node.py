#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from prototip_msgs.msg import TargetInfo, MotorCmd

from prototip_ros2.control.pid_controller import DualAxisPIDController, PIDGains
from prototip_ros2.control.motor_calculator import MotorCalculator, MotorConfig, CameraConfig

class ControlNode(Node):
    def __init__(self):
        super().__init__('control_node')
        
        # ROS 2 Parametreleri (Kısaltılmış config, detaylar params.yaml'dan gelecek)
        self.declare_parameter('pid.pan.kp', 0.15)
        self.declare_parameter('pid.pan.ki', 0.01)
        self.declare_parameter('pid.pan.kd', 0.08)
        self.declare_parameter('pid.tilt.kp', 0.15)
        self.declare_parameter('pid.tilt.ki', 0.01)
        self.declare_parameter('pid.tilt.kd', 0.08)
        self.declare_parameter('pid.output_min', -100.0)
        self.declare_parameter('pid.output_max', 100.0)
        self.declare_parameter('pid.deadband', 1.0)
        
        # Kamera ve Motor config (Örnek değerler, gerçekleri yaml'da)
        self.declare_parameter('camera.width', 640)
        self.declare_parameter('camera.height', 480)
        self.declare_parameter('camera.fov_horizontal', 60.0)
        self.declare_parameter('camera.fov_vertical', 45.0)

        # PID Sınıflarının Kurulumu
        pan_gains = PIDGains(
            kp=self.get_parameter('pid.pan.kp').value,
            ki=self.get_parameter('pid.pan.ki').value,
            kd=self.get_parameter('pid.pan.kd').value
        )
        tilt_gains = PIDGains(
            kp=self.get_parameter('pid.tilt.kp').value,
            ki=self.get_parameter('pid.tilt.ki').value,
            kd=self.get_parameter('pid.tilt.kd').value
        )
        
        self.pid = DualAxisPIDController(
            pan_gains=pan_gains,
            tilt_gains=tilt_gains,
            output_min=self.get_parameter('pid.output_min').value,
            output_max=self.get_parameter('pid.output_max').value,
            deadband=self.get_parameter('pid.deadband').value
        )
        
        cam_cfg = CameraConfig(
            width=self.get_parameter('camera.width').value,
            height=self.get_parameter('camera.height').value,
            fov_horizontal=self.get_parameter('camera.fov_horizontal').value,
            fov_vertical=self.get_parameter('camera.fov_vertical').value
        )
        
        # Şimdilik varsayılan motor ayarları (gerçek projede yaml'dan çekilir)
        pan_motor = MotorConfig(motor_type="stepper", steps_per_revolution=200, microstepping=16, gear_ratio=1.0)
        tilt_motor = MotorConfig(motor_type="dc_encoder", encoder_ppr=11, gear_ratio=90.0)
        
        self.motor_calc = MotorCalculator(pan_motor=pan_motor, tilt_motor=tilt_motor, camera=cam_cfg)
        
        # Subs/Pubs
        self.subscription = self.create_subscription(
            TargetInfo,
            '/detection/target_info',
            self.target_callback,
            10
        )
        self.motor_pub = self.create_publisher(MotorCmd, '~/motor_command', 10)
        
        self.get_logger().info("Control Node başlatıldı.")

    def target_callback(self, msg: TargetInfo):
        if not msg.is_tracked:
            # Hedef yoksa PID sıfırla
            self.pid.reset()
            return
            
        error_x = float(msg.error_x)
        error_y = float(msg.error_y)
        
        # Pikseller açılara (farkına) çevriliyor
        pan_angle_error, tilt_angle_error = self.motor_calc.pixel_error_to_angle(error_x, error_y)
        
        # PID çıktısı
        pan_output, tilt_output = self.pid.update(pan_angle_error, tilt_angle_error)
        
        # Motor birimlerine çevirme
        movement = self.motor_calc.calculate_movement(int(pan_output), int(tilt_output))
        
        cmd_msg = MotorCmd()
        cmd_msg.pan_steps = movement['pan_units']
        cmd_msg.tilt_counts = movement['tilt_units']
        cmd_msg.pan_speed = int(movement['pan_speed'])
        cmd_msg.tilt_speed = int(movement['tilt_speed'])
        
        self.motor_pub.publish(cmd_msg)
        
        # Dahili durumu güncelliyoruz
        self.motor_calc.update_position(movement['target_pan_degrees'], movement['target_tilt_degrees'])

def main(args=None):
    rclpy.init(args=args)
    node = ControlNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
