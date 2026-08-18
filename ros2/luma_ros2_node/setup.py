"""Install the Luma ROS 2 node."""

from setuptools import find_packages, setup

setup(
    name="luma_ros2_node",
    version="0.2.0",
    packages=find_packages(),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/luma_ros2_node"]),
        ("share/luma_ros2_node", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    entry_points={"console_scripts": ["luma-ros2-node = luma_ros2_node:main"]},
)
