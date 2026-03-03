#!/usr/bin/env python3
"""
Teknofest Hava Savunma Sistemi - Gazebo Simulation Launch File
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    # Package paths
    pkg_hss_gazebo = get_package_share_directory('hss_gazebo_sim')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')
    
    # Paths
    world_file = os.path.join(pkg_hss_gazebo, 'worlds', 'defense_arena.sdf')
    bridge_config = os.path.join(pkg_hss_gazebo, 'config', 'ros_gz_bridge.yaml')
    model_path = os.path.join(pkg_hss_gazebo, 'models')
    
    # Set GZ_SIM_RESOURCE_PATH for model discovery
    gz_resource_path = os.environ.get('GZ_SIM_RESOURCE_PATH', '')
    if model_path not in gz_resource_path:
        os.environ['GZ_SIM_RESOURCE_PATH'] = f"{model_path}:{gz_resource_path}"
    
    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    
    # Gazebo Sim
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={
            'gz_args': f'-r {world_file}',
        }.items()
    )
    
    # ROS-Gazebo Bridge
    ros_gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='ros_gz_bridge',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'config_file': bridge_config,
        }],
    )
    
    # Image bridge for camera (separate node for better image handling)
    ros_gz_image = Node(
        package='ros_gz_image',
        executable='image_bridge',
        name='ros_gz_image_bridge',
        arguments=['/hss/camera'],
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation time'
        ),
        gz_sim,
        ros_gz_bridge,
        ros_gz_image,
    ])
