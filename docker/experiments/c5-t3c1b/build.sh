#!/usr/bin/env bash
set -euo pipefail
root=$(pwd -P)
output=${1:?provide a new evidence directory}
mkdir "$output"
output=$(cd "$output" && pwd -P)
docker image inspect c5-b6b5-build:local --format '{{.Id}}' > "$output/image-id.txt"
docker run --rm --network none --workdir /repo -v "$root:/repo:ro" -v "$output:/build" c5-b6b5-build:local bash -ec '
 dpkg-query -W libignition-gazebo6-dev libignition-physics5-dev libdart-dev libssl-dev > /build/packages.tsv
 find docker/experiments/c5-t3c1a docker/experiments/c5-t3c1b -maxdepth 1 -type f -print0 | sort -z | xargs -0 sha256sum > /build/source-sha256.txt
 sha256sum docker/experiments/c5-b6b5/DiffDrive.cc docker/experiments/c5-b6b7/AuthorizedZero.hh >> /build/source-sha256.txt
 cmake -S docker/experiments/c5-t3c1b -B /build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE="-O2 -UNDEBUG"
 cmake --build /build -j2
 ctest --test-dir /build --output-on-failure
 sha256sum /build/*.so /build/native-zero-worker /build/split-server /build/split-recorder > /build/binary-sha256.txt
 ' > "$output/build-test.log" 2>&1
