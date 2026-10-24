from glob import glob
import os
from setuptools import find_packages, setup

package_name = "fleet_robot_executor"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        (
            "share/ament_index/resource_index/packages",
            ["resource/" + package_name],
        ),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools", "pyyaml"],
    zip_safe=True,
    maintainer="Fleet Maintainer",
    maintainer_email="maintainer@example.com",
    description="Robot Executor state machine and ROS 2 action server for ROS 2 Fleet Manager",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "robot_executor_node = fleet_robot_executor.node:main",
        ],
    },
)
