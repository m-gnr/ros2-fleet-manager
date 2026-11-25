"""Opt-in health branch of the existing 1A world/supervisor, with the same single writer."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import yaml

from backend.fleet_manager.domain.robot_health import observation_budgets

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('split_world',ROOT/'docker/experiments/c5-t3c1a/world.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
original_generate=base.server.generate;original_run=base.server.run_simulation
spec=importlib.util.spec_from_file_location('t3b_transports',ROOT/'docker/experiments/c5-t3b/world.py')
transports=importlib.util.module_from_spec(spec);spec.loader.exec_module(transports)
transports.original_run=original_run


def generate(*args,**kwargs):
    cfg=original_generate(*args,**kwargs)
    tree=ET.parse(args[1]/'warehouse.sdf')
    for robot in cfg.robots:
        driver=tree.find('.//model[@name="'+robot.id+'"]/plugin[@name="c5::test::SplitZeroDiffDrive"]')
        ET.SubElement(driver,'health_budget_sec').text=str(cfg.fleet.perception_safety.watchdog_gap_sec)
        # This opt-in fixture observes the real layer at the existing health
        # evaluation cadence. The stock 5 Hz layer plus 5 Hz scans can exhaust
        # the unchanged 0.5 s source budget before the verdict is transported.
        path=args[1]/('nav2-'+robot.id+'.yaml');params=yaml.safe_load(path.read_text())
        params['local_costmap']['local_costmap']['ros__parameters']['update_frequency']=1/cfg.fleet.perception_safety.timer_period_sec
        path.write_text(yaml.safe_dump(params,sort_keys=False))
    tree.write(args[1]/'warehouse.sdf',encoding='utf-8',xml_declaration=True)
    return cfg


def run(commands,namespaces,emit):
    real_popen=subprocess.Popen
    def popen(command,*args,**kwargs):
        if command[0]=='/b6b7-native/native-zero-worker':
            path=Path(command[1]);data=json.loads(path.read_text())
            budgets=observation_budgets(base.configuration.fleet.perception_safety)
            budgets['observation:local']=base.configuration.fleet.perception_safety.scan_age_sec
            data['health_sources']={k:int(v*1e9) for k,v in budgets.items()}
            base.atomic(path,data)
        return real_popen(command,*args,**kwargs)
    subprocess.Popen=popen
    try:return transports.run(commands,namespaces,emit)
    finally:subprocess.Popen=real_popen


base.server.generate=generate;base.server.run_simulation=run
if __name__=='__main__':raise SystemExit(base.server.main())
