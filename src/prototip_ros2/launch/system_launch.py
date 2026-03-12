import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    config = os.path.join(
        get_package_share_directory('prototip_ros2'),
        'config',
        'params.yaml'
    )

    return LaunchDescription([
        Node(
            package='prototip_ros2',
            executable='camera_node',
            name='camera_node',
            parameters=[config]
        ),
        Node(
            package='prototip_ros2',
            executable='detection_node',
            name='detection_node',
            parameters=[config]
        ),
        Node(
            package='prototip_ros2',
            executable='control_node',
            name='control_node',
            parameters=[config]
        ),
        Node(
            package='prototip_ros2',
            executable='serial_node',
            name='serial_node',
            parameters=[config]
        )
    ])
