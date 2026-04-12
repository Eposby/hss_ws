#!/usr/bin/env python3
import math
import rclpy
from rclpy.node import Node
from celikkubbe_msgs.msg import TargetInfo, MotorSetpoint

from celikkubbe_ros2.control.pid_controller import DualAxisPIDController, PIDGains
from celikkubbe_ros2.control.motor_calculator import MotorCalculator, MotorConfig, CameraConfig

class KontrolDugumu(Node):
    def __init__(self):
        super().__init__('kontrol_dugumu')
        
        # ROS 2 Parametreleri pid.pan.kp şeklindeki noktalı ("." )yazım biçimi tam olarak yaml içindeki bu ağaca (pid -> pan -> kp) işaret eder.
        self.declare_parameter('pid.pan.kp', 0.15)
        self.declare_parameter('pid.pan.ki', 0.01)
        self.declare_parameter('pid.pan.kd', 0.08)
        self.declare_parameter('pid.tilt.kp', 0.15)
        self.declare_parameter('pid.tilt.ki', 0.01)
        self.declare_parameter('pid.tilt.kd', 0.08)
        self.declare_parameter('pid.output_min', -100.0)
        self.declare_parameter('pid.output_max', 100.0)
        self.declare_parameter('pid.deadband', 1.0)
        
        # Kamera ve Motor config
        self.declare_parameter('camera.width', 640)
        self.declare_parameter('camera.height', 480)
        self.declare_parameter('camera.fov_horizontal', 60.0)
        self.declare_parameter('camera.fov_vertical', 45.0)
        
        # Saha geometrisi parametreleri (Z-ekseni pitch ofseti için)
        self.declare_parameter('turret.height_m', 0.60)
        self.declare_parameter('turret.target_height_m', 1.30)
        self.declare_parameter('turret.known_target_size_m', 0.50)
        self.declare_parameter('turret.drone_target_size_m', 0.30)

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
        
        pan_motor = MotorConfig(motor_type="stepper", steps_per_revolution=200, microstepping=16, gear_ratio=1.0)
        tilt_motor = MotorConfig(motor_type="dc_encoder", encoder_ppr=11, gear_ratio=90.0)
        
        self.motor_calc = MotorCalculator(pan_motor=pan_motor, tilt_motor=tilt_motor, camera=cam_cfg)
        
        # Saha geometrisi değerlerini oku
        self.turret_height = self.get_parameter('turret.height_m').value
        self.target_height = self.get_parameter('turret.target_height_m').value
        self.known_target_size = self.get_parameter('turret.known_target_size_m').value
        self.drone_target_size = self.get_parameter('turret.drone_target_size_m').value
        self.cam_width = self.get_parameter('camera.width').value
        self.cam_fov_h = self.get_parameter('camera.fov_horizontal').value
        
        # Subs/Pubs
        self.subscription = self.create_subscription(
            TargetInfo,
            '/gorev/dogrulanmis_hedef',
            self.target_callback,
            10
        )
        self.motor_pub = self.create_publisher(MotorSetpoint, '/kontrol/motor_komutu', 10)
        
        self.get_logger().info("Kontrol Node başlatıldı.")

    def _estimate_pitch_offset(self, msg: TargetInfo) -> float:
        """
        Taret-hedef yükseklik farkından (70cm) kaynaklanan
        dinamik pitch offset hesabı.
        
        bbox_height (px) → tahmini mesafe (m) → atan2(Δh, mesafe) → derece
        """
        delta_h = self.target_height - self.turret_height  # 0.70 m
        
        if msg.bbox_height <= 0:
            return 4.0  # Varsayılan orta değer
        
        # Hedef tipine göre boyut seçimi
        if "drone" in msg.target_type.lower() or "iha" in msg.target_type.lower():
            real_size = self.drone_target_size
        else:
            real_size = self.known_target_size
        
        # Pin-hole kamera modeli: mesafe ≈ (gerçek_boyut × focal_px) / bbox_height_px
        focal_px = (self.cam_width / 2.0) / math.tan(math.radians(self.cam_fov_h / 2.0))
        estimated_range = (real_size * focal_px) / max(msg.bbox_height, 1)
        
        # Pitch offset: atan2(Δh, mesafe) → derece
        pitch_offset_deg = math.degrees(math.atan2(delta_h, max(estimated_range, 0.5)))
        
        return pitch_offset_deg

    def target_callback(self, msg: TargetInfo):
        if not msg.is_tracked:
            self.pid.reset()
            return
            
        error_x = float(msg.error_x)
        error_y = float(msg.error_y)
        
        pan_angle_error, tilt_angle_error = self.motor_calc.pixel_error_to_angle(error_x, error_y)
        
        # Z-ekseni dinamik pitch ofseti: namlu hedefin yüksekliğine göre yukarı bakar
        pitch_offset = self._estimate_pitch_offset(msg)
        tilt_angle_error -= pitch_offset  # Eksi çünkü yukarı = negatif Y
        
        pan_output, tilt_output = self.pid.update(pan_angle_error, tilt_angle_error)
        movement = self.motor_calc.calculate_movement(int(pan_output), int(tilt_output))
        
        cmd_msg = MotorSetpoint()
        cmd_msg.pan_steps = movement['pan_units']
        cmd_msg.tilt_steps = movement['tilt_units']
        cmd_msg.pan_speed = int(movement['pan_speed'])
        cmd_msg.tilt_speed = int(movement['tilt_speed'])
        cmd_msg.pan_angle_deg = movement['target_pan_degrees']
        cmd_msg.tilt_angle_deg = movement['target_tilt_degrees']
        
        self.motor_pub.publish(cmd_msg)
        self.motor_calc.update_position(movement['target_pan_degrees'], movement['target_tilt_degrees'])

def main(args=None):
    rclpy.init(args=args)
    node = KontrolDugumu()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
