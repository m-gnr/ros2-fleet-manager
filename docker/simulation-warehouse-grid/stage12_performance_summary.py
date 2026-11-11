"""Compare only primary pickup windows under the same simulator/profile conditions."""
import json
from pathlib import Path
import statistics
import sys
from stage12_analyze import stamp


def main():
    root=Path(sys.argv[1]);rows=[]
    for directory,sampler in [('baseline-motion-rest','performance-baseline-rest.jsonl'),('effective-track','performance-effective.jsonl'),('footprint','performance-footprint.jsonl')]:
        samples=[json.loads(l) for l in (root/sampler).open()]
        for path in sorted((root/directory).glob('pickup-*/localization.json')):
            r=json.loads(path.read_text());lo=r['initial']['sim_ns'];hi=r['stopped']['sim_ns']
            events=[];stamps={kind:[] for kind in ('PHYSICAL','ODOMETRY','SCAN','AMCL')}
            for line in path.with_suffix('.jsonl').open():
                row=json.loads(line);m=row.get('message',{})
                if row['kind'] not in stamps:continue
                if row['kind']=='PHYSICAL' and row['robot']!='robot_beta':continue
                ns=stamp(m['header']['stamp'])
                if lo<=ns<=hi:
                    stamps[row['kind']].append(ns);events.append(row)
            first=min(e['monotonic'] for e in events);last=max(e['monotonic'] for e in events)
            ps=[s for s in samples if first<=s['monotonic']<=last]
            cpu=[];memory=[];total_memory=[]
            for sample in ps:
                amcl=[p for p in sample['processes'] if '/amcl ' in p['command']]
                cpu.append(sum(p['cpu_percent'] or 0 for p in amcl));memory.append(sum(p['rss_bytes'] for p in amcl))
                total_memory.append(sum(p['rss_bytes'] for p in sample['processes']))
            frequencies={k:(len(set(v))-1)/((max(v)-min(v))/1e9) if len(set(v))>1 else None for k,v in stamps.items()}
            rows.append(dict(group=directory,trial=path.parent.name,nav2_terminal=r['nav2_terminal'],
                sim_observation_s=(hi-lo)/1e9,wall_observation_s=last-first,real_time_factor=(hi-lo)/1e9/(last-first),
                physical_error_m=r['stopped']['physical_target_error_m'],amcl_cpu_two_processes_percent_mean=statistics.mean(cpu) if cpu else None,
                amcl_rss_two_processes_mib_mean=statistics.mean(memory)/2**20 if memory else None,
                sampled_selected_processes_rss_mib_max=max(total_memory)/2**20 if total_memory else None,
                process_samples=len(ps),frequencies_hz=frequencies))
    (root/'performance-summary.json').write_text(json.dumps(rows,indent=2))
    for row in rows:print(json.dumps(row))

if __name__=='__main__':main()
