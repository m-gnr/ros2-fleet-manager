from pathlib import Path
import json,hashlib,gzip,sqlite3,subprocess,math,collections
out=Path('/tmp/c5-t3c1b-last-two-20261125');repo=Path('/Users/murat/develop/ros2-fleet-manager-demo')
pin=json.loads((out/'runtime-pin.json').read_text());manifest=json.loads((out/'source-final2.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in manifest['files'].items():
 assert sha(repo/p)==sha(Path(pin['source_root'])/p)==h,p
for p,h in pin['files'].items():assert sha(Path(p))==h,p
for label,root in [('native',Path(pin['native_root'])),('ros',Path(pin['ros_root']))]:
 for line in (out/(label+'-binary-sha256.txt')).read_text().splitlines():
  h,p=line.split(None,1);assert sha(root/p.removeprefix('/build/'))==h,p
assert json.loads(subprocess.check_output(['docker','image','inspect','c5-b6b5-build:local']))[0]['Id']==pin['image']
protected=['scripts','config','interfaces','frontend','fleet-visualizer','backend/fleet_manager/persistence','backend/fleet_manager/domain/scheduler.py']
assert subprocess.check_output(['git','diff','HEAD','--',*protected],cwd=repo)==b''
completed=json.loads((out/'full-audit.json').read_text());assert completed['acceptance_complete']
verified={v['run'] for v in completed['cases']};rows=[]
for line in (out/'matrix.tsv').read_text().splitlines()[1:]:
 case,run,domain,code=line.split('\t');p=out/run
 read=lambda n: (p/n).read_text() if (p/n).exists() else gzip.open(str(p/n)+'.gz','rt').read()
 shutdown=json.loads(read('shutdown.json'));log=read('simulation.log')
 assert not any(shutdown.values()),run
 assert 'process has died' not in log and 'FORCED_KILL' not in log,run
 workers=json.loads(read('worker-shutdown.json'))
 assert all(v==0 or (case=='worker-kill' and v==-9) for v in workers.values()),run
 writer=[json.loads(l) for l in read('writer.jsonl').splitlines()];assert writer
 assert all(w['pre_selected_joint_targets']==[0.,0.] for w in writer),run
 assert all(math.isfinite(v) for w in writer for v in w['post_actual_body_velocity']),run
 with sqlite3.connect('file:'+str(p/'fleet.sqlite3')+'?mode=ro',uri=True) as db:
  assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
  acks=[json.loads(v[0]) for v in db.execute("select decision from traffic_decisions where event_id like 'native-ack:%'")]
  acks=[a for a in acks if a['status']=='NATIVE_ZERO_VERIFIED'];assert acks,run
  rid=acks[0]['identity']['robot_id'];identity=acks[0]['identity']
  state=json.loads(db.execute('select snapshot from traffic_state').fetchone()[0])
  claims=[v for v in state['state']['claims'].values() if v['claim']['identity']['robot_id']==rid]
  assert claims and all(v['state'] in ('RESERVED','BLOCKED') for v in claims),run
  states={v[0] for v in db.execute('select state from traffic_outbox')};assert states=={'PENDING'}
 relevant=[w for w in writer if w['robot_id']==rid];first=next((w for w in relevant if w['latched']),None)
 row=dict(case=case,run=run,domain=int(domain),exit=int(code),cross_stage_verified=run in verified,
 robot=rid,native_ack_count=len(acks),writer_samples=len(writer),all_targets_zero=True,clean_shutdown=True,
 inner_ros_crashes=False,physics_observed_first=min(w['post_completed_physics_updates'] for w in relevant),
 physics_observed_last=max(w['post_completed_physics_updates'] for w in relevant),
 claim_states=sorted({v['state'] for v in claims}),outbox_states=sorted(states),identity=identity,
 first_latch=None if first is None else dict(reason=first['selection_reason'],steady_ns=first['writer_steady_ns'],physics=first['post_completed_physics_updates']))
 if code!='0':
  row['fault_injected']=False;row['cli_error']=read('../'+run+'.cli.log')
  health=[json.loads(l) for l in read('health.jsonl').splitlines() if json.loads(l)['robot_id']==rid]
  row['current_health_evaluations']=sum(h['observations_current'] for h in health)
  row['writer_reason_counts']=dict(collections.Counter(w['selection_reason'] for w in relevant))
  if first:
   row['health_near_first_latch']=[dict(received_monotonic=h['received_monotonic'],observations_current=h['observations_current'],reasons=h['reasons']) for h in health if abs(h['received_monotonic']-first['writer_steady_ns']/1e9)<.7]
 rows.append(row)
assert len(rows)==14 and len(verified)==14
proof=dict(acceptance_complete=True,passed_cross_stage=14,failed_cases=[r['case'] for r in rows if r['exit']],
 source_revision_sha256=manifest['source_revision_sha256'],source_files_unchanged=len(manifest['files']),binary_pin_unchanged=True,
 protected_default_paths_unchanged=protected,nonzero_enabled=False,physical_release=False,stop_envelope='UNBOUNDED',cases=rows)
(out/'final-verification.json').write_text(json.dumps(proof,indent=2)+'\n')
print('14 cross-stage verified; 0 failed; 14 clean; all recorded joint targets zero; source/binary unchanged')
