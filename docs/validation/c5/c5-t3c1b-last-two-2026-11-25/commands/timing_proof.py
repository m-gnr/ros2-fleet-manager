from pathlib import Path
import json,gzip,hashlib
root=Path('/tmp/c5-t3c1b-last-two-20261125')
results=[]
for case in ('odometry-loss','observation-loss'):
 p=root/(case+'-targeted-final2');before=json.loads((p/'health-before.json').read_text());identity=before['actual_task_identity'];rid=identity['robot_id']
 body=before['packet']['body'];w=before['writer'];digest=w['health']['health_digest'];h=w['health']
 assert w['selection_reason']=='VERIFIED_ZERO' and not w['latched'] and body['observations_current']
 assert h['health_deadline_ns']==h['health_ticket_issued_ns']+h['health_remaining_ns']
 assert 0<w['writer_steady_ns']-h['health_ticket_issued_ns']<h['health_remaining_ns']
 with gzip.open(p/'health-sources.jsonl.gz','rt') as f:raw=[json.loads(l) for l in f]
 packet=next(x for x in raw if x['stream']=='health_veto_packet' and x['robot']==rid and hashlib.sha256(x['packet']['body'].encode()).hexdigest()==digest)
 publish=next(x for x in raw if x['stream']=='health_timing' and x['event']=='packet_published' and x['digest']==digest)
 with gzip.open(p/'native-verifier.jsonl.gz','rt') as f:native=[json.loads(l) for l in f]
 received=next(x['health_receiver'] for x in native if x['robot_id']==rid and x.get('health_receiver',{}).get('digest')==digest)
 assert received['sequence']==body['sequence'] and received['ticket']==body['ticket']
 originals=[]
 for index,stamp in enumerate(body['sources']['observation:local']['measurement_stamps_ns']):
  matching=[x for x in raw if x['stream']=='observation:local' and x['robot']==rid and x['value']['stamps'][index]==stamp]
  first=matching[0];originals.append(dict(index=index,measurement_stamp_ns=stamp,first_receipt_monotonic=first['received_monotonic'],
   first_layer_processed_ns=first['value']['processed_ns'],first_layer_sequence=first['value']['sequence']))
 inspection={x['event']:x['monotonic_ns'] for x in raw if x['stream']=='health_timing' and x['event'].startswith('library_inspection_')}
 assert inspection['library_inspection_end']<packet['received_monotonic']*1e9
 timing=h['ipc_timing'];fault=json.loads((p/'health-fault.json').read_text());summary=json.loads((p/'summary.json').read_text())
 assert summary['first_latched']['writer_steady_ns']>=summary['fault_started_observer_monotonic_ns']
 results.append(dict(case=case,robot=rid,healthy_digest=digest,source=body['sources']['observation:local'],
  original_measurements=originals,evaluated_monotonic_ns=int(packet['received_monotonic']*1e9),
  published_monotonic_ns=publish['monotonic_ns'],worker_health_received_ns=received['received_steady_ns'],
  writer_selected_ns=w['writer_steady_ns'],writer_ticket_issued_ns=h['health_ticket_issued_ns'],
  writer_deadline_ns=h['health_deadline_ns'],remaining_at_evaluation_ns=body['remaining_ns'],
  total_evaluation_to_writer_ns=w['writer_steady_ns']-int(packet['received_monotonic']*1e9),
  ipc_worker_received_to_verified_ns=timing['worker_verified_ns']-timing['worker_received_ns'],
  ipc_worker_verified_to_ready_ns=timing['worker_ready_ns']-timing['worker_verified_ns'],
  ipc_ready_to_writer_check_ns=timing['checked_ns']-timing['worker_ready_ns'],
  library_inspection=inspection,fault_started_ns=summary['fault_started_observer_monotonic_ns'],
  first_latch=summary['first_latched']['selection_reason'],physics_before=summary['before']['post_completed_physics_updates'],
  physics_during=summary['during']['post_completed_physics_updates'],fault_health_reasons=fault['health_during']['reasons']))
(root/'timing-proof.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
