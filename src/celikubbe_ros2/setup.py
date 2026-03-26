import os
from setuptools import find_packages, setup

package_name = 'celikubbe_ros2'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), ['launch/celikubbe_launch.py']),
        (os.path.join('share', package_name, 'config'), ['config/params.yaml']),
    ],
    install_requires=['setuptools', 'celikubbe_msgs'],
    zip_safe=True,
    maintainer='mert',
    maintainer_email='uslumertali@gmail.com',
    description='Çelikkubbe Hava Savunma Sistemi Nodes',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'kamera_dugumu = celikubbe_ros2.kamera_dugumu:main',
            'tespit_dugumu = celikubbe_ros2.tespit_dugumu:main',
            'kontrol_dugumu = celikubbe_ros2.kontrol_dugumu:main',
            'donanim_dugumu = celikubbe_ros2.donanim_dugumu:main',
            'gorev_dugumu = celikubbe_ros2.gorev_dugumu:main',
            'arayuz_dugumu = celikubbe_ros2.arayuz_dugumu:main'
        ],
    },
)
