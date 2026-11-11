"""Reuse exact-stamp ray alignment with the matching isolated landmark geometry."""
import argparse
from pathlib import Path
from fleet_config.warehouse import WarehouseLayout
from stage12_scan_analysis import analyze
from stage13_server import landmark_obstacles, original_obstacles


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('root',type=Path)
    cli.add_argument('--profile',type=Path,default=Path('config/fleet.warehouse-30x18.yaml'))
    args=cli.parse_args()
    for group in sorted(args.root.iterdir()):
        if not group.is_dir():continue
        WarehouseLayout.obstacles=landmark_obstacles if group.name=='b-landmark' else original_obstacles
        for folder in sorted(group.glob('pickup-*')):
            if not (folder/'shutdown.json').exists():continue
            # The experiment profiles carry container-only absolute asset paths.
            # Geometry is identical to the source profile, except for the explicit
            # landmark override above; assert that identity before ray casting.
            import json
            from fleet_config import load_config
            cfg=load_config(args.profile)
            solids=[dict(name=n,bounds=b.model_dump(),height=h) for n,b,h in cfg.warehouse.obstacles()]
            assert solids==json.loads((folder/'generated/solids.json').read_text())
            rows=analyze(folder,args.profile)
            print(group.name,folder.name,'samples',len(rows),'last',rows[-1] if rows else None,flush=True)

if __name__=='__main__':main()
