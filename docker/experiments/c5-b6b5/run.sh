#!/usr/bin/env bash
set -euo pipefail
# Run from the main worktree root. Output must be a new directory.
root=$(pwd)
out=${1:?provide a new evidence directory}
mkdir "$out"
base=$(docker image inspect ros2-fleet-c5-validation:humble-fortress --format '{{.Id}}')
test "$base" = sha256:7fb7e7fc4aebe0d2b4097752e9b470e30d8ea7a8126bb1dee87d03f30330609d
printf '%s\n' "$base" > "$out/base-image.txt"
docker build --pull=false -t c5-b6b5-build:local docker/experiments/c5-b6b5 > "$out/image-build.log" 2>&1
image=$(docker image inspect c5-b6b5-build:local --format '{{.Id}}')
printf '%s\n' "$image" > "$out/build-image.txt"
docker run --rm --network none -e IGN_PARTITION=c5-b6b5-zero \
  -v "$root/docker/experiments/c5-b6b5:/src:ro" -v "$root/$out:/evidence" \
  "$image" bash /src/build-test.sh > "$out/build-test.log" 2>&1
