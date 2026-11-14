#!/usr/bin/env python3
"""Generate the frontend's offline warehouse scene from the validated fleet YAML."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fleet_config import load_config  # noqa: E402
from fleet_config.occupancy import profile_digest  # noqa: E402


SOURCE = ROOT / "config/fleet.warehouse-30x18.yaml"
OUTPUT = ROOT / "frontend/src/scene/warehouseProfile.generated.ts"


def generated_content():
    config = load_config(SOURCE)
    if config.warehouse is None:
        raise ValueError(f"{SOURCE}: expected a warehouse profile")
    payload = {
        "profile_id": config.fleet.name,
        "profile_digest": profile_digest(config),
        "layout": config.warehouse.scene_payload(),
    }
    return "export const staticWarehouse = " + json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + " as const\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the checked-in data is stale")
    args = parser.parse_args()
    content = generated_content()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != content:
            raise SystemExit(f"{OUTPUT.relative_to(ROOT)} is stale; regenerate it from {SOURCE.relative_to(ROOT)}")
    else:
        OUTPUT.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
