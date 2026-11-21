#!/usr/bin/env bash
set -euo pipefail
test -s eglantine.profdata
profile="-fprofile-use=$PWD/eglantine.profdata -Wno-backend-plugin -Wno-profile-instr-unprofiled -Wno-profile-instr-out-of-date"
cmake -S . -B build/dlss -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=clang-23 -DCMAKE_CXX_COMPILER=clang++-23 \
  "-DCMAKE_EXE_LINKER_FLAGS=-B/usr/lib/llvm-23/bin -fuse-ld=lld" \
  "-DCMAKE_C_FLAGS=$profile" "-DCMAKE_CXX_FLAGS=$profile" \
  -DBUILD_TESTING=ON -DLICHII_TESTS=ON -DDYNARMIC_TESTS=OFF \
  -DLICHII_CMD=ON -DLICHII_ROOM=OFF -DLICHII_ROOM_STANDALONE=OFF \
  -DLICHII_USE_BUNDLED_QT=OFF -DENABLE_QT_TRANSLATION=ON \
  "-DCMAKE_PREFIX_PATH=$QT_ROOT_DIR" -DLICHII_USE_BUNDLED_SDL3=ON \
  -DVulkanHeaders_FORCE_BUNDLED=ON -DVulkanUtilityLibraries_FORCE_BUNDLED=ON \
  -DENABLE_NVIDIA_DLSS=ON -DENABLE_UPDATE_CHECKER=OFF \
  "-DLICHII_BUILD_TAG=$DLSS_TAG" -DLICHII_BUILD_PLATFORM=linux-x86_64-pgo \
  -DUSE_DISCORD_PRESENCE=OFF -DUSE_CCACHE=ON
cmake --build build/dlss --parallel 4
cmake --build build/dlss --target ngx_smoke --parallel 4
