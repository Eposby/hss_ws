from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'hss_tracking'

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
    description='HSS Aşama 2 3B Hedef Takip, Kalman Filtresi ve Hız Kestirim Paketi',
    license='Proprietary',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'tracker_node = hss_tracking.tracker_node:main',
        ],
    },
)
