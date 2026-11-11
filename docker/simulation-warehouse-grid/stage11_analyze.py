"""Analyze timestamped localization trials and committed product progress."""
import argparse
from datetime import datetime, timezone
import json
from math import atan2, cos, hypot, sin
from pathlib import Path
import statistics
from stage11_metrics import aligned_displacement_error


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence',type=Path)
    args=parser.parse_args()
    trials=[]
    for path in sorted((args.evidence/'localization').glob('trial-*/localization.json')):
        raw=json.loads(path.read_text());a,b=raw['initial'],raw['stopped']
        # Odom is a local frame. Compare displacements only after aligning its
        # initial heading to the independently measured world heading.
        drift=aligned_displacement_error(a,b)
        yaw_drift=abs(atan2(sin((b['physical'][2]-a['physical'][2])-(b['odom_pose'][2]-a['odom_pose'][2])),
                            cos((b['physical'][2]-a['physical'][2])-(b['odom_pose'][2]-a['odom_pose'][2]))))
        trial=dict(trial=path.parent.name,nav2_terminal=raw['nav2_terminal'],result=raw['result'],
            initial=a,terminal=raw['terminal'],stopped=b,reset=raw['reset'],
            aligned_odom_displacement_error_m=drift,aligned_odom_yaw_drift_rad=yaw_drift,
            scan_samples=len(raw['scan_map_samples']),scan_last=raw['scan_map_samples'][-1],contacts=raw['contacts'])
        trials.append(trial)
    errors=[r['stopped']['physical_target_error_m'] for r in trials]
    report=dict(utc=datetime.now(timezone.utc).isoformat(),trials=trials,
        count=len(errors),threshold_m=.35,passed=sum(v<=.35 for v in errors),
        min_m=min(errors),max_m=max(errors),mean_m=statistics.mean(errors),median_m=statistics.median(errors),
        stdev_m=statistics.stdev(errors) if len(errors)>1 else None,
        limits=['Pose comparisons use TF at the physical sample timestamp, with explicit interpolation brackets.',
                'AMCL covariance retains its own scan timestamp and age; it is not relabelled as terminal-time covariance.',
                'Scan residual is distance to static occupied rectangles, not calibrated lidar error or a likelihood score.',
                'The producer-v1 unaligned odometry delta is invalid across frames; use aligned_odom_displacement_error_m here.'])
    (args.evidence/'localization-analysis.json').write_text(json.dumps(report,indent=2))
    for name in ('scenario-a','scenario-b'):
        path=args.evidence/name/'committed-events.jsonl'
        if not path.exists():continue
        rows=[json.loads(line) for line in path.open()]
        progress={}
        for row in rows:
            for tid,state in row['transitions'].items():
                progress.setdefault(tid,[]).append(dict(utc=row['utc'],monotonic=row['monotonic'],state=state,source=row['kind']))
        (args.evidence/name/'authoritative-transitions.json').write_text(json.dumps(progress,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ('trials','limits')},indent=2))


if __name__=='__main__':
    main()
