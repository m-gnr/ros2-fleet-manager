"""Audit immutable physical/controller contracts and preserve initial user sources."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree as ET
import yaml


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root=Path(sys.argv[1]);baseline=json.loads((root/'baseline-hashes.json').read_text())
    expected_changes={'docker/simulation-warehouse-grid/stage12_probe.py','config/simulation-c2-3-params.template.yaml','docs/README.md','docs/validation/README.md'}
    changes=[];unexpected=[]
    for name,record in baseline.items():
        p=Path(name)
        if not p.is_file() or digest(p)!=record['sha256']:
            changes.append(name)
            if name not in expected_changes:unexpected.append(name)
    reference=yaml.safe_load((root/'a-baseline/pickup-1/generated/nav2-robot_beta.yaml').read_text())
    worlds=[]
    for file in sorted(root.glob('*/pickup-*/shutdown.json')):
        folder=file.parent;generated=folder/'generated';issues=[]
        for rid in ('robot_alpha','robot_beta'):
            params=yaml.safe_load((generated/f'nav2-{rid}.yaml').read_text())
            for layer in ('local_costmap','global_costmap'):
                if params[layer][layer]['ros__parameters']['robot_radius']!=.30:issues.append(f'{rid}/{layer}: unsafe radius')
            if params['controller_server']!=reference['controller_server']:issues.append(f'{rid}: changed controller')
            for key in ('planner_server','smoother_server','behavior_server','velocity_smoother'):
                # Robot-specific odom names are expected; compare each robot to its own baseline.
                own=yaml.safe_load((root/f'a-baseline/pickup-1/generated/nav2-{rid}.yaml').read_text())
                if params[key]!=own[key]:issues.append(f'{rid}: changed {key}')
        tree=ET.parse(generated/'warehouse.sdf')
        for rid in ('robot_alpha','robot_beta'):
            model=tree.getroot().find(f".//model[@name='{rid}']")
            track=float(model.find("plugin[@name='ignition::gazebo::systems::DiffDrive']/wheel_separation").text)
            if track!=.36:issues.append(f'{rid}: changed effective track')
            size=model.find("link[@name='base_link']/collision/geometry/box/size").text
            if list(map(float,size.split()))!=[.5,.3,.1]:issues.append(f'{rid}: changed physical body')
        report=json.loads((folder/'localization.json').read_text())
        if report.get('target_id')=='pick_A2' and report.get('target')!={'x':2.25,'y':5.75,'yaw':1.5707963267948966}:issues.append('changed pick_A2 goal')
        worlds.append(dict(run=str(folder),issues=issues))
    image=json.loads(subprocess.check_output(['docker','image','inspect','ros2-fleet-c5-validation:humble-fortress'],text=True))
    containers=[]
    names=subprocess.check_output(['docker','ps','-a','--filter','name=fleet-c5-stage13-','--format','{{.Names}}'],text=True).splitlines()
    for name in names:
        data=json.loads(subprocess.check_output(['docker','inspect',name],text=True))[0]
        containers.append(dict(name=name,image=data['Image'],state=data['State'],command=data['Config']['Cmd'],env=data['Config']['Env'],mounts=data['Mounts'],extra_hosts=data['HostConfig'].get('ExtraHosts'),port_bindings=data['HostConfig'].get('PortBindings')))
    result=dict(changed_initial_files=changes,unexpected_initial_changes=unexpected,worlds=worlds,
        contract_violations=sum(bool(w['issues']) for w in worlds),containers=containers,image_id=image[0]['Id'])
    (root/'preservation-and-contract-audit.json').write_text(json.dumps(result,indent=2))
    print('initial changes:',changes,'unexpected:',unexpected,'worlds:',len(worlds),'contract violations:',result['contract_violations'])
    raise SystemExit(1 if unexpected or result['contract_violations'] else 0)

if __name__=='__main__':main()
