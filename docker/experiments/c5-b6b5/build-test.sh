#!/usr/bin/env bash
set -euo pipefail
export SOURCE_DATE_EPOCH=0
sha256sum /src/*.cc /src/*.hh /src/CMakeLists.txt /src/upstream/* > /evidence/source-sha256.txt
dpkg-query -W > /evidence/packages.tsv
c++ --version > /evidence/compiler.txt
for pass in 1 2; do
  cmake -S /src -B /tmp/build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE='-O2 -UNDEBUG'
  cmake --build /tmp/build -j2
  ctest --test-dir /tmp/build --output-on-failure
  sha256sum /tmp/build/libc5-actuator-diff-drive.so | cut -d' ' -f1 > "/evidence/binary-$pass.sha256"
  cp /tmp/build/libc5-actuator-diff-drive.so "/evidence/plugin-$pass.so"
  if [ "$pass" = 1 ]; then rm -rf /tmp/build; fi
done
cmp /evidence/binary-1.sha256 /evidence/binary-2.sha256
cmake --build /tmp/build -j2
sha256sum /tmp/build/libc5-actuator-diff-drive.so | cut -d' ' -f1 > /evidence/binary-incremental.sha256
cmp /evidence/binary-1.sha256 /evidence/binary-incremental.sha256
ldd /tmp/build/libc5-actuator-diff-drive.so > /evidence/ldd.txt
! grep -q 'not found' /evidence/ldd.txt
readelf -h -d /tmp/build/libc5-actuator-diff-drive.so > /evidence/elf.txt
IGN_GAZEBO_SYSTEM_PLUGIN_PATH=/tmp/build /tmp/build/load-plugin > /evidence/plugin-load.txt
set +e
IGN_GAZEBO_SYSTEM_PLUGIN_PATH=/nonexistent /tmp/build/load-plugin > /evidence/missing-path.txt 2>&1
status=$?
set -e
test "$status" = 3
printf 'PASS missing plugin path exit=%s\n' "$status" >> /evidence/missing-path.txt
