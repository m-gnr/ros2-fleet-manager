"""Run one documented experiment variant on generated assets only."""
import os
from xml.etree import ElementTree as ET
import yaml
import serve

original=serve.generate

def generate(*args,**kwargs):
    cfg=original(*args,**kwargs);out=args[1]
    variant=os.environ.get('STAGE12_VARIANT','baseline')
    sdf=out/'warehouse.sdf';tree=ET.parse(sdf)
    if variant=='timestep':
        tree.getroot().find('.//physics/max_step_size').text='0.001'
    elif variant in ('effective_track','nominal_track'):
        for r in cfg.robots:
            model=tree.getroot().find(f".//model[@name='{r.id}']")
            model.find("plugin[@name='ignition::gazebo::systems::DiffDrive']/wheel_separation").text='0.36' if variant=='effective_track' else '0.4'
    elif variant=='footprint':
        for r in cfg.robots:
            path=out/f'nav2-{r.id}.yaml';p=yaml.safe_load(path.read_text())
            for layer in ('local_costmap','global_costmap'):
                cost=p[layer][layer]['ros__parameters'];cost['robot_radius']=0.30
            path.write_text(yaml.safe_dump(p,sort_keys=False))
    elif variant!='baseline':raise ValueError(variant)
    tree.write(sdf,encoding='utf-8',xml_declaration=True)
    (out/'variant.txt').write_text(variant+'\n')
    return cfg

serve.generate=generate
if __name__=='__main__':raise SystemExit(serve.main())
