#!/usr/bin/env python3
"""
Teknofest Hava Savunma Sistemi - Main Launch File
Tüm sistemı başlatır: State Machine + Turret Controller + Target Detector
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    # Parameters
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    
    # Package directories
    hss_gazebo_dir = get_package_share_directory('hss_gazebo_sim')
    
    # Include Gazebo simulation launch
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(hss_gazebo_dir, 'launch', 'simulation.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )
    
    # State Machine Node
    state_machine_node = Node(
        package='hava_savunma_pkg',
        executable='state_machine',
        name='state_machine_node',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}]
    )
    
    # Turret Controller Node
    turret_controller_node = Node(
        package='hava_savunma_pkg',
        executable='turret_controller',
        name='turret_controller_node',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'pan_min': -3.14159,
            'pan_max': 3.14159,
            'tilt_min': -0.785,
            'tilt_max': 1.047,
        }]
    )
    
    # Target Detector Node
    target_detector_node = Node(
        package='hava_savunma_pkg',
        executable='target_detector',
        name='target_detector_node',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'detection_rate': 10.0,
            'min_area': 500.0,
            'max_area': 50000.0,
            'friend_color': 'green',
            'foe_color': 'red',
        }]
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation time from Gazebo'
        ),
        gazebo_launch,
        state_machine_node,
        turret_controller_node,
        target_detector_node,
    ])
