from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'hava_savunma_pkg'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='mert',
    maintainer_email='mert@teknofest.com',
    description='Teknofest Hava Savunma Sistemi - State Machine ve Hedef Tespit Paketi',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'balloon_detector=hava_savunma_pkg.nodes.balloon_detector:main',
        ],
    },
)

