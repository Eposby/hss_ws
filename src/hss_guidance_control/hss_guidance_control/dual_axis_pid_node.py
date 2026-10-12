#!/usr/bin/env python3
"""
HSS Çift Eksenli (Dual-Axis) PID Kontrol Düğümü
-----------------------------------------------
Hedef açılar ile taretin anlık açıları arasındaki hatayı kapalı çevrim
PID algoritmasıyla sıfırlar; Anti-Windup ve Deadband filtreleri uygulayarak
hassas motor adım komutlarına (MotorSetpoint) dönüştürür.
"""

import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from hss_interfaces.msg import FireControlCommand, MotorFeedback, MotorSetpoint


class PIDAxis:
    def __init__(self, kp: float, ki: float, kd: float, deadband: float, max_out: float):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.deadband = deadband
        self.max_out = max_out

        self.integral = 0.0
        self.prev_error = 0.0
        self.last_time = time.time()

    def update(self, error: float) -> float:
        now = time.time()
        dt = max(now - self.last_time, 0.001)
        self.last_time = now

        # Ölü bölge (Deadband) kontrolü
        if abs(error) < self.deadband:
            self.integral = 0.0
            self.prev_error = error
            return 0.0

        # Oransal (P)
        p_term = self.kp * error

        # İntegral (I) + Anti-Windup sınırlandırması
        self.integral += error * dt
        i_limit = self.max_out / max(self.ki, 1e-4) if self.ki > 0 else 0.0
        self.integral = max(-i_limit, min(i_limit, self.integral))
        i_term = self.ki * self.integral

        # Türev (D)
        d_term = self.kd * ((error - self.prev_error) / dt)
        self.prev_error = error

        # Toplam çıkış
        output = p_term + i_term + d_term
        return max(-self.max_out, min(self.max_out, output))

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0


class DualAxisPIDNode(Node):
    def __init__(self):
        super().__init__('dual_axis_pid_node')

        # Parametreler
        self.declare_parameter('pid.pan.kp', 0.25)
        self.declare_parameter('pid.pan.ki', 0.01)
        self.declare_parameter('pid.pan.kd', 0.12)
        self.declare_parameter('pid.tilt.kp', 0.25)
        self.declare_parameter('pid.tilt.ki', 0.01)
        self.declare_parameter('pid.tilt.kd', 0.12)
        self.declare_parameter('pid.deadband_deg', 0.30)
        self.declare_parameter('pid.output_max_deg_per_sec', 90.0)

        self.declare_parameter('hardware.steps_per_rev_pan', 3200)
        self.declare_parameter('hardware.steps_per_rev_tilt', 3200)
        self.declare_parameter('hardware.gear_ratio_pan', 3.0)
        self.declare_parameter('hardware.gear_ratio_tilt', 1.0)

        # PID Eksenleri
        deadband = self.get_parameter('pid.deadband_deg').value
        max_out = self.get_parameter('pid.output_max_deg_per_sec').value

        self.pid_pan = PIDAxis(
            kp=self.get_parameter('pid.pan.kp').value,
            ki=self.get_parameter('pid.pan.ki').value,
            kd=self.get_parameter('pid.pan.kd').value,
            deadband=deadband,
            max_out=max_out
        )
        self.pid_tilt = PIDAxis(
            kp=self.get_parameter('pid.tilt.kp').value,
            ki=self.get_parameter('pid.tilt.ki').value,
            kd=self.get_parameter('pid.tilt.kd').value,
            deadband=deadband,
            max_out=max_out
        )

        # Taret donanım dönüşüm oranları (adım / derece)
        steps_pan = self.get_parameter('hardware.steps_per_rev_pan').value
        gear_pan = self.get_parameter('hardware.gear_ratio_pan').value
        self.steps_per_deg_pan = (steps_pan * gear_pan) / 360.0

        steps_tilt = self.get_parameter('hardware.steps_per_rev_tilt').value
        gear_tilt = self.get_parameter('hardware.gear_ratio_tilt').value
        self.steps_per_deg_tilt = (steps_tilt * gear_tilt) / 360.0

        # Anlık taret durumu
        self.current_pan_deg = 0.0
        self.current_tilt_deg = 0.0
        self.e_stop_active = False

        # Publisher
        self.pub_motor = self.create_publisher(MotorSetpoint, '/kontrol/motor_komutu', 10)

        # Subscribers
        self.sub_fire_cmd = self.create_subscription(
            FireControlCommand,
            '/guidance/fire_command',
            self.fire_cmd_callback,
            10
        )
        self.sub_feedback = self.create_subscription(
            MotorFeedback,
            '/donanim/motor_geri_bildirim',
            self.feedback_callback,
            10
        )
        self.sub_estop = self.create_subscription(
            Bool,
            '/arayuz/acil_dur',
            self.estop_callback,
            10
        )

        self.get_logger().info('Dual-Axis PID Kontrol Düğümü hazır.')

    def estop_callback(self, msg: Bool):
        self.e_stop_active = msg.data
        if self.e_stop_active:
            self.pid_pan.reset()
            self.pid_tilt.reset()
            # Durma komutu gönder
            stop_cmd = MotorSetpoint()
            stop_cmd.pan_speed_sps = 0
            stop_cmd.tilt_speed_sps = 0
            self.pub_motor.publish(stop_cmd)
            self.get_logger().warn('ACİL DURDURMA AKTİF: Motorlar kilitlendi!')

    def feedback_callback(self, msg: MotorFeedback):
        self.current_pan_deg = msg.current_pan_deg
        self.current_tilt_deg = msg.current_tilt_deg
        if msg.e_stop_active:
            self.e_stop_active = True

    def fire_cmd_callback(self, msg: FireControlCommand):
        if self.e_stop_active or not msg.fire_permission:
            return

        # Açısal hatalar (Hata = Hedef - Mevcut)
        err_pan = msg.target_pan_deg - self.current_pan_deg
        err_tilt = msg.target_tilt_deg - self.current_tilt_deg

        # PID Çıkışları (İstenen açısal hız derece/sn)
        speed_pan_deg_s = self.pid_pan.update(err_pan)
        speed_tilt_deg_s = self.pid_tilt.update(err_tilt)

        # Hızları adım/saniyeye çevir
        pan_speed_sps = int(abs(speed_pan_deg_s) * self.steps_per_deg_pan)
        tilt_speed_sps = int(abs(speed_tilt_deg_s) * self.steps_per_deg_tilt)

        # Hedef adım değerleri
        pan_steps = int(msg.target_pan_deg * self.steps_per_deg_pan)
        tilt_steps = int(msg.target_tilt_deg * self.steps_per_deg_tilt)

        setpoint = MotorSetpoint()
        setpoint.pan_angle_deg = float(msg.target_pan_deg)
        setpoint.tilt_angle_deg = float(msg.target_tilt_deg)
        setpoint.pan_steps = pan_steps
        setpoint.tilt_steps = tilt_steps
        setpoint.pan_speed_sps = pan_speed_sps
        setpoint.tilt_speed_sps = tilt_speed_sps

        self.pub_motor.publish(setpoint)


def main(args=None):
    rclpy.init(args=args)
    node = DualAxisPIDNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
