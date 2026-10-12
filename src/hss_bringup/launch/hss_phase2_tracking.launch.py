from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # 1. TF2 Çerçeve Yayıncısı
        Node(
            package='hss_localization_3d',
            executable='tf_broadcaster_node',
            name='tf_broadcaster_node',
            output='screen'
        ),

        # 2. Aşama 2 - SolvePnP ve 3B Konumlama Düğümü
        Node(
            package='hss_localization_3d',
            executable='pnp_depth_estimator',
            name='pnp_depth_estimator',
            output='screen'
        ),

        # 3. Aşama 2 - 3B Kalman Filtresi ve Hedef Takip Düğümü
        Node(
            package='hss_tracking',
            executable='tracker_node',
            name='tracker_node',
            output='screen'
        ),

        # 4. Aşama 2 - Balistik ve Önleme Açısı (Lead Angle) Düğümü
        Node(
            package='hss_guidance_control',
            executable='ballistic_calculator',
            name='ballistic_calculator',
            output='screen'
        ),

        # 5. Çift Eksenli PID ve Motor Setpoint Düğümü
        Node(
            package='hss_guidance_control',
            executable='dual_axis_pid_node',
            name='dual_axis_pid_node',
            output='screen'
        )
    ])
