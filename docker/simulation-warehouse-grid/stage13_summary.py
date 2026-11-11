"""Build report tables from all completed worlds, including failed measurements."""
from collections import defaultdict
import json
from pathlib import Path
import statistics
import sys


def number(value):return f'{value:.3f}' if value is not None else '—'

def main():
    root=Path(sys.argv[1]);rows=json.loads((root/'experiment-results.json').read_text());groups=defaultdict(list)
    for row in rows:groups[Path(row['folder']).parent.name].append(row)
    lines=['| Varyant | Koşu | Nav2 S/A | Fiziksel kriter | Temiz kabul | Fiziksel hatalar (m) |','|---|---:|---:|---:|---:|---|']
    performance=['| Varyant | Hedef penceresi medyan (sim s) | RTF medyan | Beta AMCL ortalama CPU (%) | Son covariance xx/yy/yaw medyan |','|---|---:|---:|---:|---|']
    individuals=['| Koşu | Nav2 | Fiziksel hata (m) | Map–fiziksel (m) | Yaw hata (rad) | Recovery max | Duruş | Probe / dünya |','|---|---|---:|---:|---:|---:|---|---|']
    for group,values in sorted(groups.items()):
        succeeded=sum(v.get('nav2_terminal')==4 for v in values);aborted=sum(v.get('nav2_terminal')==6 for v in values)
        lines.append(f"| {group} | {len(values)} | {succeeded}/{aborted} | {sum(bool(v.get('physical_criteria_passed')) for v in values)}/{len(values)} | {sum(bool(v.get('passed')) for v in values)}/{len(values)} | "+' / '.join(number(v.get('physical_error_m')) for v in values)+' |')
        valid=[v for v in values if v.get('measurement_valid')]
        med=lambda key:statistics.median(v[key] for v in valid if v.get(key) is not None) if any(v.get(key) is not None for v in valid) else None
        cpu=[v['beta_amcl_cpu_percent']['mean'] for v in valid if v.get('beta_amcl_cpu_percent')]
        cov=[statistics.median(v['covariance'][i] for v in valid) for i in range(3)] if valid else []
        performance.append(f"| {group} | {number(med('goal_window_sim_s'))} | {number(med('observed_rtf'))} | {number(statistics.mean(cpu) if cpu else None)} | "+' / '.join(number(c) for c in cov)+' |')
        for v in values:
            name=Path(v['folder']).parent.name+'/'+Path(v['folder']).name;sh=v.get('shutdown',{})
            state='GEÇTİ' if v.get('safe_stop') else 'DOĞRULANAMADI'
            individuals.append(f"| {name} | {v.get('nav2_terminal','—')} | {number(v.get('physical_error_m'))} | {number(v.get('map_physical_m'))} | {number(v.get('yaw_error_rad'))} | {v.get('max_recoveries','—')} | {state} | {sh.get('probe_exit','—')} / {sh.get('simulation_exit','—')} |")
    (root/'comparison-tables.md').write_text('\n'.join(lines)+'\n\n'+'\n'.join(performance)+'\n\n'+'\n'.join(individuals)+'\n')
    audit=dict(worlds=len(rows),measurement_invalid=sum(not v.get('measurement_valid') for v in rows),
        physical_criteria_passed=sum(bool(v.get('physical_criteria_passed')) for v in rows),clean_accepted=sum(bool(v.get('passed')) for v in rows),
        unclean_shutdowns=[v['folder'] for v in rows if v.get('shutdown',{}).get('simulation_exit')!=0],
        probe_failures=[v['folder'] for v in rows if v.get('shutdown',{}).get('probe_exit')!=0])
    (root/'summary-counts.json').write_text(json.dumps(audit,indent=2));print(json.dumps(audit,indent=2))

if __name__=='__main__':main()
