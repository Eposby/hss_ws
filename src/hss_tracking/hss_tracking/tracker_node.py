#!/usr/bin/env python3
"""
HSS Aşama 2 - Çoklu Hedef Takip ve Durum Kestirim Düğümü
-------------------------------------------------------
3B Konumlama katmanından gelen ham hedefleri Kalman filtresiyle pürüzsüzleştirir,
hız vektörlerini (Vx, Vy, Vz) türetir, kayıp hedeflerde Coasting (Kestirim)
modunu yönetir ve en yüksek tehditli birincil hedefi (Primary Target) seçer.
"""

import math
import time
import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Point, Vector3
from hss_interfaces.msg import Target3D, TrackedTarget, TrackedTargetArray
from hss_tracking.ekf_filter_3d import EKFFilter3D


class TargetTrack:
    def __init__(self, track_id: int, target_msg: Target3D, q_pos: float, q_vel: float, r_meas: float):
        self.track_id = track_id
        self.class_name = target_msg.class_name
        self.color = target_msg.color
        self.is_friendly = target_msg.is_friendly
        self.confidence = target_msg.confidence

        init_pos = (target_msg.position.x, target_msg.position.y, target_msg.position.z)
        self.filter = EKFFilter3D(init_pos=init_pos, q_pos=q_pos, q_vel=q_vel, r_meas=r_meas)

        now = time.time()
        self.birth_time = now
        self.last_seen_time = now
        self.last_update_time = now
        self.is_coasting = False

    def update_measurement(self, target_msg: Target3D):
        now = time.time()
        dt = max(now - self.last_update_time, 0.001)
        self.filter.predict(dt)

        meas = (target_msg.position.x, target_msg.position.y, target_msg.position.z)
        self.filter.update(meas)

        self.last_seen_time = now
        self.last_update_time = now
        self.is_coasting = False
        self.confidence = target_msg.confidence
        self.color = target_msg.color
        self.is_friendly = target_msg.is_friendly

    def step_prediction(self):
        now = time.time()
        dt = max(now - self.last_update_time, 0.001)
        self.filter.predict(dt)
        self.last_update_time = now
        self.is_coasting = True


class TrackerNode(Node):
    def __init__(self):
        super().__init__('tracker_node')

        # Parametreler
        self.declare_parameter('tracker.update_rate_hz', 30.0)
        self.declare_parameter('tracker.coasting_timeout_sec', 1.2)
        self.declare_parameter('tracker.max_lost_timeout_sec', 3.0)
        self.declare_parameter('tracker.process_noise_pos', 0.05)
        self.declare_parameter('tracker.process_noise_vel', 0.50)
        self.declare_parameter('tracker.measurement_noise', 0.10)

        rate = self.get_parameter('tracker.update_rate_hz').value
        self.coasting_timeout = self.get_parameter('tracker.coasting_timeout_sec').value
        self.max_lost_timeout = self.get_parameter('tracker.max_lost_timeout_sec').value
        self.q_pos = self.get_parameter('tracker.process_noise_pos').value
        self.q_vel = self.get_parameter('tracker.process_noise_vel').value
        self.r_meas = self.get_parameter('tracker.measurement_noise').value

        # Aktif izler (Track dictionary: track_id -> TargetTrack)
        self.tracks = {}

        # Publishers
        self.pub_targets = self.create_publisher(TrackedTargetArray, '/tracking/tracked_targets', 10)
        self.pub_primary = self.create_publisher(TrackedTarget, '/tracking/primary_target', 10)

        # Subscriber
        self.sub_target_3d = self.create_subscription(
            Target3D,
            '/localization/target_3d',
            self.target_3d_callback,
            10
        )

        # Düzenli güncelleme zamanlayıcısı
        timer_period = 1.0 / max(rate, 1.0)
        self.timer = self.create_timer(timer_period, self.track_loop_callback)

        self.get_logger().info('HSS 3B Kalman Hedef Takip Düğümü (TrackerNode) hazır.')

    def target_3d_callback(self, msg: Target3D):
        tid = msg.target_id if msg.target_id > 0 else 1

        if tid in self.tracks:
            self.tracks[tid].update_measurement(msg)
        else:
            self.tracks[tid] = TargetTrack(
                track_id=tid,
                target_msg=msg,
                q_pos=self.q_pos,
                q_vel=self.q_vel,
                r_meas=self.r_meas
            )

    def calculate_threat_score(self, track: TargetTrack):
        """
        Tehdit Skoru Hesabı (0.0 - 100.0):
        1. Menzil: Yakındaki hedefler daha yüksek puan.
        2. Yaklaşma Hızı: Tarete doğru gelen hedefler (+Vz yaklaşma) daha yüksek puan.
        3. Dost hedefler: 0.0 puan (Angajman dışı).
        """
        if track.is_friendly:
            return 0.0

        x, y, z = track.filter.position
        vx, vy, vz = track.filter.velocity
        range_m = math.sqrt(x**2 + y**2 + z**2)

        # 1. Mesafe puanı (15 metreye kadar normalize)
        dist_score = max(0.0, min(100.0, (15.0 - range_m) * (100.0 / 15.0)))

        # 2. Yaklaşma hızı puanı (vz < 0 bize doğru geliyorsa)
        approach_speed = -vz
        speed_score = max(0.0, min(100.0, approach_speed * 20.0))

        # Ağırlıklı toplam
        threat = (0.6 * dist_score) + (0.4 * speed_score)
        return float(max(1.0, min(100.0, threat)))

    def track_loop_callback(self):
        now = time.time()
        active_tracked_msgs = []
        highest_threat = -1.0
        primary_msg = None

        to_remove = []

        for tid, track in list(self.tracks.items()):
            time_since_seen = now - track.last_seen_time

            if time_since_seen > self.max_lost_timeout:
                to_remove.append(tid)
                continue

            # Eğer anlık veri gelmediyse ama süre sınırındaysa Coasting yap
            if time_since_seen > 0.05 and time_since_seen <= self.coasting_timeout:
                track.step_prediction()

            # Mesajı hazırla
            x, y, z = track.filter.position
            vx, vy, vz = track.filter.velocity
            speed = track.filter.speed
            range_m = math.sqrt(x**2 + y**2 + z**2)
            threat = self.calculate_threat_score(track)
            age = float(now - track.birth_time)

            t_msg = TrackedTarget()
            t_msg.header.stamp = self.get_clock().now().to_msg()
            t_msg.header.frame_id = 'camera_optical_frame'
            t_msg.track_id = tid
            t_msg.class_name = track.class_name
            t_msg.color = track.color
            t_msg.is_friendly = track.is_friendly
            t_msg.position = Point(x=x, y=y, z=z)
            t_msg.velocity = Vector3(x=vx, y=vy, z=vz)
            t_msg.speed_mps = speed
            t_msg.range_m = range_m
            t_msg.threat_score = threat
            t_msg.is_coasting = track.is_coasting
            t_msg.track_age_sec = age

            active_tracked_msgs.append(t_msg)

            if not track.is_friendly and threat > highest_threat:
                highest_threat = threat
                primary_msg = t_msg

        # Silinecekleri temizle
        for tid in to_remove:
            del self.tracks[tid]

        # Toplu takip dizisini yayınla
        array_msg = TrackedTargetArray()
        array_msg.header.stamp = self.get_clock().now().to_msg()
        array_msg.targets = active_tracked_msgs
        self.pub_targets.publish(array_msg)

        # Birincil hedefi yayınla
        if primary_msg is not None:
            self.pub_primary.publish(primary_msg)


def main(args=None):
    rclpy.init(args=args)
    node = TrackerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
