from setuptools import setup

package_name = "fleet_battery_simulator"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    maintainer="Fleet Maintainer",
    maintainer_email="maintainer@example.com",
    description="Simulation-time battery energy accounting for ROS 2 Fleet Manager",
    license="Apache-2.0",
    entry_points={"console_scripts": ["battery_simulator = fleet_battery_simulator.node:main"]},
)
