import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    config = os.path.join(
        get_package_share_directory('celikubbe_ros2'),
        'config',
        'params.yaml'
    )

    return LaunchDescription([
        Node(
            package='celikubbe_ros2',
            executable='kamera_dugumu',
            name='kamera_dugumu',
            parameters=[config]
        ),
        Node(
            package='celikubbe_ros2',
            executable='tespit_dugumu',
            name='tespit_dugumu',
            parameters=[config]
        ),
        Node(
            package='celikubbe_ros2',
            executable='kontrol_dugumu',
            name='kontrol_dugumu',
            parameters=[config]
        ),
        Node(
            package='celikubbe_ros2',
            executable='donanim_dugumu',
            name='donanim_dugumu',
            parameters=[config]
        ),
        Node(
            package='celikubbe_ros2',
            executable='gorev_dugumu',
            name='gorev_dugumu',
            parameters=[config]
        ),
        Node(
            package='celikubbe_ros2',
            executable='arayuz_dugumu',
            name='arayuz_dugumu',
            parameters=[config]
        )
    ])
