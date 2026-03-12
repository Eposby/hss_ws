from setuptools import find_packages, setup

package_name = 'prototip_ros2'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/system_launch.py']),
        ('share/' + package_name + '/config', ['config/params.yaml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='mert',
    maintainer_email='uslumertali@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'camera_node = prototip_ros2.camera_node:main',
            'detection_node = prototip_ros2.detection_node:main',
            'control_node = prototip_ros2.control_node:main',
            'serial_node = prototip_ros2.serial_node:main'
        ],
    },
)
