"""Read-only real health probe around the existing T3A zero-only scenarios."""
from copy import deepcopy
from dataclasses import asdict
import importlib.util
import json
import os
from pathlib import Path
import signal
import sqlite3
import time
import xml.etree.ElementTree as ET

import yaml
from fleet_config.native_zero import compact,sha,load_key,decisions
from fleet_config.obstacle_sensors import pose,compose,shape_bound
from backend.fleet_manager.adapters.robot_health import RobotHealthProbe
from backend.fleet_manager.domain.stop_envelope import StopInputs,stop_envelope,reservation_check,relative_stop_check
from backend.fleet_manager.domain.traffic import Box

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('t3a_live',ROOT/'docker/experiments/c5-t3a/live.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)


def factory(node,cfg,args,database):
    def context(rid,native):
        try:
            with sqlite3.connect('file:'+str(database)+'?mode=ro',uri=True) as db:
                db.execute('BEGIN')
                row=db.execute("SELECT d.decision,o.payload FROM traffic_decisions d JOIN traffic_outbox o ON d.event_id=o.event_id "
                    "WHERE d.event_id LIKE 'native-transfer:%' AND json_extract(d.decision,'$.identity.robot_id')=? ORDER BY d.rowid DESC LIMIT 1",(rid,)).fetchone()
                if not row or row[0]!=row[1]:return None,None
                transfer=json.loads(row[0]);body=json.loads(transfer['body']);identity=transfer['identity']
                raw=body['command_context'];normalized={**raw,'operation':'INSTALL_ZERO'}
                permit,child=decisions(normalized)
                if (permit['identity']!=identity or sha(transfer['body'])!=transfer['command_sha256']
                        or body['source_session']!=identity['fm_session']
                        or body['permit_id']!=identity['permit_id'] or body['permit_generation']!=identity['generation']):return None,None
                assignment=db.execute('SELECT payload FROM outbox_events WHERE kind=? AND task_id=? AND assignment_epoch=? AND goal_uuid=?',
                    ('EXECUTE_TASK',identity['task_id'],identity['epoch'],identity['execute_uuid'])).fetchone()
                if not assignment or json.loads(assignment[0])['assigned_robot_id']!=rid:return None,None
                for label in ('permit','child'):
                    source=db.execute('SELECT payload FROM traffic_outbox WHERE event_id=?',(raw[label+'_event_id'],)).fetchone()
                    if not source or source[0]!=raw[label+'_decision']:return None,None
                state=json.loads(db.execute('SELECT snapshot FROM traffic_state WHERE singleton=1').fetchone()[0])
                reserved=any(v['claim']['identity']==identity and v['state']=='RESERVED' for v in state['state']['claims'].values())
                command=None
                if native:
                    digest=native['value']['status']['command_sha256']
                    known=db.execute("SELECT decision FROM traffic_decisions WHERE event_id LIKE 'native-transfer:%' "
                                     "AND json_extract(decision,'$.command_sha256')=?",(digest,)).fetchone()
                    if known:
                        known=json.loads(known[0])
                        if known['identity']==identity:command=digest,known['command_sequence']
                return dict(identity=identity,context_sha256=sha(compact(normalized)),claim_reserved=reserved),command
        except (sqlite3.OperationalError,KeyError,ValueError):return None,None
    params={r.id:yaml.safe_load((args.output/'generated'/('nav2-'+r.id+'.yaml')).read_text()) for r in cfg.robots}
    inventory={}
    tree=ET.parse(args.output/'generated/warehouse.sdf')
    for robot in cfg.robots:
        p=params[robot.id];radius=p['local_costmap']['local_costmap']['ros__parameters']['robot_radius']
        assert radius==p['global_costmap']['global_costmap']['ros__parameters']['robot_radius']
        model=tree.find('.//model[@name="'+robot.id+'"]');shapes=[]
        for link in model.findall('link'):
            for collision in link.findall('collision'):
                center,matrix=compose(pose(link),pose(collision));bound,aabb=shape_bound(collision.find('geometry'),center,matrix)
                assert bound<=radius+1e-12
                shapes.append(dict(link=link.get('name'),collision=collision.get('name'),enclosing_sphere_radius_m=bound,aabb=aabb))
        inventory[robot.id]=dict(nav2=p['controller_server']['ros__parameters']['FollowPath'],
            smoother=p['velocity_smoother']['ros__parameters'],footprint_radius_m=radius,collisions=shapes,
            link_masses_kg={link.get('name'):link.findtext('inertial/mass') for link in model.findall('link')},
            driver_settings=[dict(name=d.get('name'),library=d.get('filename'),
                fields={e.tag:e.text for e in d if e.tag!='authorization_file'})
                for d in model.findall('plugin') if 'DiffDrive' in d.get('name','')],
            contact_friction=[dict(link=link.get('name'),collision=collision.get('name'),
                surface=ET.tostring(collision.find('surface'),encoding='unicode') if collision.find('surface') is not None else None)
                for link in model.findall('link') for collision in link.findall('collision')],
            configured_limits_are_measured_braking=False,motion_envelope=cfg.fleet.perception_safety.motion_envelope)
    (args.output/'physical-config-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    probe=RobotHealthProbe(node,cfg,params,{r.id:load_key('/run/c5-b6b7/'+r.id+'.json') for r in cfg.robots},context,args.output)
    probe.t3b_inventory=inventory
    return probe


def process_matching(parts):
    found=[]
    for path in Path('/proc').glob('[0-9]*/cmdline'):
        try:args=path.read_bytes().decode().split('\0')
        except (OSError,UnicodeError):continue
        if all(any(part in arg for arg in args) for part in parts):found.append(int(path.parent.name))
    assert len(found)==1,(parts,found)
    return found[0]


def faults(case,c):
    probe,rid,until,pump=c['probe'],c['robot'].id,c['until'],c['pump']
    result={}
    def pause(pid,label,stream,budget):
        until(lambda:probe.latest.get(rid,{}).get('source_ages',{}).get(stream,{}).get('current'))
        before=deepcopy(probe.latest.get(rid));started=time.monotonic()
        os.kill(pid,signal.SIGSTOP)
        try:
            until(lambda: 'STALE_OR_UNKNOWN:'+stream in probe.latest.get(rid,{}).get('reasons',[]),budget+3.)
            # Wait beyond the full configured budget even if another defect was
            # already present, and prove local receipt age, not just a label.
            end=started+budget+.25
            while time.monotonic()<end:pump()
            value=deepcopy(probe.latest[rid]);age=value['source_ages'][stream]['receipt_age_sec']
            assert age is not None and age>=budget
            assert not value['movement_eligible'] and not value['ownership_release']
            result[label]=dict(pid=pid,signal='SIGSTOP',elapsed_sec=time.monotonic()-started,
                               source_receipt_age_sec=age,before=before,during=value)
        finally:os.kill(pid,signal.SIGCONT)
        end=time.monotonic()+.3
        while time.monotonic()<end:pump()
    if case=='sensor-loss':
        manifest=json.loads((c['args'].output/'fault-processes.json').read_text())
        pause(manifest['odometry_link']['pid'],'odometry_link_loss','odometry',probe.config.fleet.perception_safety.odometry_freshness_sec)
        pause(manifest['tf_helper']['pid'],
              'tf_producer_loss','tf',probe.config.fleet.perception_safety.odometry_freshness_sec)
        from std_srvs.srv import Empty
        client=c['node'].create_client(Empty,c['robot'].namespace+'/request_nomotion_update')
        until(client.service_is_ready)
        previous=probe.latest[rid]['source_ages']['amcl']['source_stamp_ns']
        future=client.call_async(Empty.Request());until(future.done)
        until(lambda:probe.latest[rid]['source_ages']['amcl']['source_stamp_ns']!=previous)
        pause(process_matching(['/nav2_amcl/amcl','__ns:='+c['robot'].namespace]),
              'amcl_process_delay','amcl',probe.config.fleet.perception_safety.observation_age_sec)
    elif case=='update-freeze':
        mappings=json.loads((c['args'].output/'native-loaded-mappings.json').read_text());assert len(mappings)==1
        pause(mappings[0]['pid'],'native_process_freeze','native',probe.config.fleet.perception_safety.watchdog_gap_sec)
        until(lambda:c['states'][rid]['state'] in ('TIMED_OUT','BLOCKED_REARM'))
        result['after_resume']=deepcopy(c['states'][rid])
        result['independent_braking_guarantee']=False
    elif case=='controller-inactive':
        from lifecycle_msgs.srv import ChangeState
        from lifecycle_msgs.msg import Transition
        client=c['node'].create_client(ChangeState,c['robot'].namespace+'/controller_server/change_state')
        until(client.service_is_ready)
        request=ChangeState.Request();request.transition.id=Transition.TRANSITION_DEACTIVATE
        future=client.call_async(request);until(future.done)
        assert future.result().success
        until(lambda:'LIFECYCLE_NOT_ACTIVE:controller_server' in probe.latest.get(rid,{}).get('reasons',[]))
        result['controller_inactive']=deepcopy(probe.latest[rid])
    (c['args'].output/'health-fault-results.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def validate(case,c):
    probe,rid=c['probe'],c['robot'].id
    if case in ('executor-loss','bridge-loss','fm-loss'):
        c['until'](lambda:'NATIVE_LEASE_NOT_ACTIVE' in probe.latest.get(rid,{}).get('reasons',[]))
    if case=='replan':
        c['until'](lambda:'PERMIT_NOT_RESERVED' in probe.latest.get(rid,{}).get('reasons',[]))
    latest=deepcopy(probe.latest[rid])
    assert latest['measured'].get('odometry') and latest['measured'].get('native')
    assert not latest['movement_eligible'] and latest['physical_stop']=='UNKNOWN' and not latest['ownership_release']
    position=latest['measured'].get('map_pose',[None,None])
    inputs=StopInputs()  # No physical braking/delay/error/margin calibration exists.
    observed=latest['derived']
    envelope=stop_envelope(x=position[0],y=position[1],linear_speed=observed.get('linear_speed_m_s'),
        angular_speed=observed.get('angular_speed_rad_s'),footprint_radius=probe.t3b_inventory[rid]['footprint_radius_m'],inputs=inputs)
    assert envelope['tube'] is None and not envelope['qualified']
    peers={}
    for other in c['config'].robots:
        view=probe.latest.get(other.id,{})
        point=view.get('measured',{}).get('map_pose',[None,None]);speed=view.get('derived',{})
        candidate=stop_envelope(x=point[0],y=point[1],linear_speed=speed.get('linear_speed_m_s'),
            angular_speed=speed.get('angular_speed_rad_s'),footprint_radius=probe.t3b_inventory[other.id]['footprint_radius_m'],inputs=StopInputs())
        peers[other.id]=dict(envelope=candidate,relative_to_assignee=relative_stop_check(envelope,candidate))
    output=dict(actual_robot=rid,health=latest,stop_envelope=envelope,peer_stop_assessments=peers,
                reservation_assessment=reservation_check(envelope,[]),motion_authorized=False)
    (c['args'].output/'health-summary.json').write_text(json.dumps(output,indent=2)+'\n')
    return output


if __name__=='__main__':
    base.main(extra_cases=('sensor-loss','update-freeze','controller-inactive'),observer_factory=factory,
              fault_handler=faults,case_validator=validate,world_path=Path(__file__).with_name('world.py'))
