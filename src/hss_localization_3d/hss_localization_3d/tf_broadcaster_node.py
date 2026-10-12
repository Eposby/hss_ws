#!/usr/bin/env python3
"""
HSS TF2 Koordinat Çerçeveleri Yayıncısı (TF Broadcaster)
--------------------------------------------------------
turret_base_link -> turret_pitch_link -> camera_link -> camera_optical_frame
çerçeve dönüşümlerini statik ve dinamik olarak yayınlar.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
from tf2_ros import StaticTransformBroadcaster
import math


class TurretTFBroadcaster(Node):
    def __init__(self):
        super().__init__('tf_broadcaster_node')
        self.tf_static_broadcaster = StaticTransformBroadcaster(self)
        self.publish_static_transforms()
        self.get_logger().info('HSS TF2 Koordinat Çerçeve Yayıncısı aktif.')

    def publish_static_transforms(self):
        transforms = []

        # 1. turret_base_link -> camera_link
        t1 = TransformStamped()
        t1.header.stamp = self.get_clock().now().to_msg()
        t1.header.frame_id = 'turret_base_link'
        t1.child_frame_id = 'camera_link'
        t1.transform.translation.x = 0.0
        t1.transform.translation.y = 0.05
        t1.transform.translation.z = 0.35
        t1.transform.rotation.x = 0.0
        t1.transform.rotation.y = 0.0
        t1.transform.rotation.z = 0.0
        t1.transform.rotation.w = 1.0
        transforms.append(t1)

        # 2. camera_link -> camera_optical_frame (ROS REP-103 standardı: Z ileri, X sağa, Y aşağı)
        t2 = TransformStamped()
        t2.header.stamp = self.get_clock().now().to_msg()
        t2.header.frame_id = 'camera_link'
        t2.child_frame_id = 'camera_optical_frame'
        t2.transform.translation.x = 0.0
        t2.transform.translation.y = 0.0
        t2.transform.translation.z = 0.0
        # -90 deg yaw, -90 deg pitch dönüşümü (Kamera optik standardı)
        # q = [ -0.5, 0.5, -0.5, 0.5 ]
        t2.transform.rotation.x = -0.5
        t2.transform.rotation.y = 0.5
        t2.transform.rotation.z = -0.5
        t2.transform.rotation.w = 0.5
        transforms.append(t2)

        self.tf_static_broadcaster.sendTransform(transforms)


def main(args=None):
    rclpy.init(args=args)
    node = TurretTFBroadcaster()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
