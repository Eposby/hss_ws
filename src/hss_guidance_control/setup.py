from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'hss_guidance_control'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Mert',
    maintainer_email='mert@todo.todo',
    description='HSS Balistik Önleme, Kinematik ve Çift Eksenli PID Kontrol Paketi',
    license='Proprietary',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'ballistic_calculator = hss_guidance_control.ballistic_calculator:main',
            'dual_axis_pid_node = hss_guidance_control.dual_axis_pid_node:main',
        ],
    },
)
