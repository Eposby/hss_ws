from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'hss_localization_3d'

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
    description='HSS Aşama 2 SolvePnP ve 3B Poz Kestirimi Paketi',
    license='Proprietary',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'pnp_depth_estimator = hss_localization_3d.pnp_depth_estimator:main',
            'tf_broadcaster_node = hss_localization_3d.tf_broadcaster_node:main',
        ],
    },
)
