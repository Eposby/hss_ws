#!/usr/bin/env python3
"""
HSS Aşama 2 - Balistik ve Önleme Açısı (Lead Angle) Hesaplama Düğümü
-------------------------------------------------------------------
Hedef hareketli olduğunda, hedefin şu anki konumuna değil; lazerin/merminin
varış süresine göre hedefin gelecekteki önleme noktasına (Intercept Point)
nişan alır. Yerçekimi düşümü ve sistem gecikmesini kompanse eder.
"""

import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point
from hss_interfaces.msg import TrackedTarget, FireControlCommand


class BallisticCalculator(Node):
    def __init__(self):
        super().__init__('ballistic_calculator')

        # Parametreler
        self.declare_parameter('guidance.mode', 'laser') # 'laser' veya 'ballistic'
        self.declare_parameter('guidance.projectile_velocity_mps', 80.0)
        self.declare_parameter('guidance.system_latency_sec', 0.04) # 40 ms gecikme
        self.declare_parameter('guidance.gravity_mps2', 9.81)

        self.mode = self.get_parameter('guidance.mode').value
        self.v_proj = self.get_parameter('guidance.projectile_velocity_mps').value
        self.latency = self.get_parameter('guidance.system_latency_sec').value
        self.g = self.get_parameter('guidance.gravity_mps2').value

        # Publisher
        self.pub_cmd = self.create_publisher(FireControlCommand, '/guidance/fire_command', 10)

        # Subscriber
        self.sub_target = self.create_subscription(
            TrackedTarget,
            '/tracking/primary_target',
            self.target_callback,
            10
        )

        self.get_logger().info(f'Balistik Önleme Hesaplayıcı aktif. Mod: {self.mode}')

    def target_callback(self, msg: TrackedTarget):
        # Dost hedef ise atış izni yok
        if msg.is_friendly:
            return

        x = msg.position.x
        y = msg.position.y
        z = max(msg.position.z, 0.20)
        vx = msg.velocity.x
        vy = msg.velocity.y
        vz = msg.velocity.z

        range_m = math.sqrt(x**2 + y**2 + z**2)

        # Mermi/Lazer uçuş süresi hesabı (Time of Flight)
        if self.mode == 'laser':
            t_flight = self.latency
        else:
            t_flight = (range_m / max(self.v_proj, 1.0)) + self.latency

        # Gelecekteki Önleme Noktası (Intercept Point)
        x_intercept = x + (vx * t_flight)
        z_intercept = max(z + (vz * t_flight), 0.20)

        # Balistik mermi ise yerçekimi düşümü telafisi (Y ekseni aşağı pozitif)
        if self.mode == 'ballistic':
            gravity_drop = 0.5 * self.g * (t_flight ** 2)
            y_intercept = (y + (vy * t_flight)) - gravity_drop
        else:
            y_intercept = y + (vy * t_flight)

        # Taret için Hedef Açıları (Derece)
        # Pan (Yaw): X sağa pozitif, Z ileri
        target_pan_deg = math.degrees(math.atan2(x_intercept, z_intercept))

        # Tilt (Pitch): Y aşağı pozitif, bu yüzden -y_intercept yukarı bakıştır
        ground_dist = math.sqrt(x_intercept**2 + z_intercept**2)
        target_tilt_deg = math.degrees(math.atan2(-y_intercept, ground_dist))

        # Komut mesajı oluştur
        cmd = FireControlCommand()
        cmd.header.stamp = self.get_clock().now().to_msg()
        cmd.header.frame_id = 'turret_base_link'
        cmd.target_track_id = msg.track_id
        cmd.intercept_point = Point(x=x_intercept, y=y_intercept, z=z_intercept)
        cmd.target_pan_deg = float(target_pan_deg)
        cmd.target_tilt_deg = float(target_tilt_deg)
        cmd.time_to_impact_sec = float(t_flight)
        cmd.fire_permission = True
        cmd.status = 'LOCKED' if not msg.is_coasting else 'COASTING_AIM'

        self.pub_cmd.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    node = BallisticCalculator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
