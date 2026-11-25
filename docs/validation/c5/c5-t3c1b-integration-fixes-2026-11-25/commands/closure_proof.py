from pathlib import Path
import json,hashlib,sqlite3
out=Path('/tmp/c5-t3c1b-recovery-20261124');frozen=json.loads((out/'frozen-source-1.json').read_text())
for path,digest in frozen['files'].items():assert hashlib.sha256((out/'frozen-source-1'/path).read_bytes()).hexdigest()==digest,path
cases=[]
for row in (out/'targeted-3.tsv').read_text().splitlines()[1:]:
 case,run,domain,code=row.split('\t');assert code=='0'
 p=out/run;s=json.loads((p/'summary.json').read_text());log=(p/'simulation.log').read_text()
 assert 'process has died' not in log and 'FORCED_KILL' not in log
 mappings=json.loads((p/'ros-library-mappings.json').read_text());robots=json.loads((p/'workers.json').read_text())
 for rid in robots:
  match=[r for r in mappings if r['robot_id']==rid and Path(r['argv'][0]).name in ('controller_server','planner_server')]
  assert len(match)==2,(rid,match)
  assert all(any('/build/lifecycle/libc5-costmap-cleanup.so' in line for line in r['libraries']) for r in match)
  assert all(not any('/build/install/nav2_costmap_2d/' in line for line in r['libraries']) for r in match)
 assert log.count('C5_CLEANUP_CALLBACKS_JOINED')>=2*len(robots)
 with sqlite3.connect(p/'fleet.sqlite3') as db:
  state=json.loads(db.execute('select snapshot from traffic_state').fetchone()[0])
  claims=state['state']['claims'];owned=[v for v in claims.values() if v['claim']['identity']==s['committed_ack']['identity']]
  assert owned and all(v['state'] in ('RESERVED','BLOCKED') for v in owned)
  assert {v[0] for v in db.execute('select state from traffic_outbox')}=={'PENDING'}
 assert json.loads((p/'scene-ready.json').read_text())['permit_authorized'] is False
 cases.append(dict(case=case,run=run,robot=s['robot_id'],domain=int(domain),physics_before=s['before']['post_completed_physics_updates'],
  physics_during=s['during']['post_completed_physics_updates'],reason=s['first_latched']['selection_reason'],
  cleanup_markers=log.count('C5_CLEANUP_CALLBACKS_JOINED'),claim_states=[v['state'] for v in owned],CLI=int(code)))
proof=dict(source_revision_sha256=frozen['source_revision_sha256'],source_files_verified=len(frozen['files']),cases=cases,
 full_14_matrix_run=False,physical_movement_enabled=False,commit_push_performed=False)
(out/'targeted-3-closure-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))
