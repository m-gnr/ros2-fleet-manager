"""Run from the repository root: python -m fleet_config config/fleet.yaml."""

import argparse
import json
import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from .loader import generated_schema, load_config


def main():
    parser = argparse.ArgumentParser(description="Validate fleet configuration without starting ROS or Docker")
    parser.add_argument("path", type=Path)
    parser.add_argument("--write-schema", action="store_true", help="Write generated JSON Schema to path")
    args = parser.parse_args()
    try:
        if args.write_schema:
            args.path.write_text(json.dumps(generated_schema(), indent=2) + "\n", encoding="utf-8")
        else:
            config = load_config(args.path)
            print(f"VALID: {len(config.robots)} robots; schema, semantic and file reference checks passed")
    except (OSError, ValueError, ValidationError, yaml.YAMLError) as error:
        print(f"INVALID: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
