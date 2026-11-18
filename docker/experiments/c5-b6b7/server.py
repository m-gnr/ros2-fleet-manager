"""Opt-in native zero-only world, reusing the existing warehouse/Nav2 server.

Not imported by the product launcher. Every generated robot has one immutable
zero-only joint writer. No fixture here can authorize physical movement.
"""
import importlib.util
import json
import os
from pathlib import Path
import secrets
import sys
from uuid import uuid4
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("warehouse_server", ROOT / "docker/simulation-warehouse-grid/serve.py")
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)
original_generate = server.generate
original_run = server.run_simulation


def generate(profile, output, scenario, **kwargs):
    config = original_generate(profile, output, scenario, **kwargs)
    secret_dir = Path("/run/c5-b6b7")
    secret_dir.mkdir(mode=0o700, exist_ok=False)
    tree = ET.parse(output / "warehouse.sdf")
    public = {}
    for robot in config.robots:
        model = tree.find(f'.//model[@name="{robot.id}"]')
        plugins = [p for p in model.findall("plugin") if "DiffDrive" in p.get("name", "")]
        if len(plugins) != 1:
            raise ValueError("Exactly one existing differential drive is required")
        driver = plugins[0]
        driver.set("filename", "/b6b7-native/libc5-authorized-zero-drive.so")
        driver.set("name", "c5::test::AuthorizedZeroDiffDrive")
        driver.find("topic").text = robot.namespace + "/authorized_zero"
        manifest = dict(key_hex=secrets.token_hex(32), source_session=str(uuid4()),
            context=dict(identity=dict(robot_id=robot.id, task_id="zero-only-native-fixture", epoch=1,
                                       child_uuid=str(uuid4()))),
            permit_id=str(uuid4()), generation=1, lease_sec=.25, ticket_sec=.2, permit_sec=600.)
        path = secret_dir / (robot.id + ".json")
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(manifest, stream)
        ET.SubElement(driver, "authorization_file").text = str(path)
        ET.SubElement(driver, "actuator_state_topic").text = robot.namespace + "/native_actuator"
        public[robot.id] = {k: v for k, v in manifest.items() if k != "key_hex"}
    (output.parent / "native-fixtures-public.json").write_text(json.dumps(public, indent=2) + "\n")
    tree.write(output / "warehouse.sdf", encoding="utf-8", xml_declaration=True)
    if any(p.get("filename") != "/b6b7-native/libc5-authorized-zero-drive.so"
           for p in tree.findall(".//model/plugin") if "DiffDrive" in p.get("name", "")):
        raise ValueError("An alternate differential drive remains")
    return config


def run(commands, namespaces, emit):
    # Extend the existing bridge; raw cmd_vel can still be injected in this
    # negative test, but there is no stock driver subscribing to that input.
    for name, command in commands:
        if name == "bridge":
            additions = []
            for ns in namespaces:
                additions += [f"/{ns}/native_actuator@std_msgs/msg/String[ignition.msgs.StringMsg"]
            # Dock pose remappings already append --ros-args. Bridge mappings
            # must precede those flags. The test owns a separate command bridge
            # so its loss does not stop the physics or native state observer.
            index = command.index("--ros-args") if "--ros-args" in command else len(command)
            command[index:index] = additions
    return original_run(commands, namespaces, emit)


server.generate = generate
server.run_simulation = run
if __name__ == "__main__":
    raise SystemExit(server.main())
