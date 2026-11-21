#!/usr/bin/env bash
set -euo pipefail
tools="$RUNNER_TEMP/linuxdeploy"
mkdir -p "$tools" out AppDir/usr/bin AppDir/usr/share/licenses/lichii-dlss
for tool in linuxdeploy linuxdeploy-plugin-qt; do
  curl -fsSL --retry 2 -o "$tools/$tool-x86_64.AppImage" \
    "https://github.com/linuxdeploy/$tool/releases/download/continuous/$tool-x86_64.AppImage"
  chmod +x "$tools/$tool-x86_64.AppImage"
done
cp dist/lichii.png "$RUNNER_TEMP/io.github.zortos293.lichii.png"
cp LICENSE.txt AppDir/usr/share/licenses/lichii-dlss/
cp -r externals/opendlss-nr/LICENSE externals/opendlss-nr/NOTICE \
  externals/opendlss-nr/UPSTREAM.json AppDir/usr/share/licenses/lichii-dlss/
cp build/dlss/bin/nx2_switches.txt AppDir/usr/bin/
strip build/dlss/bin/lichii build/dlss/bin/eden-cli build/dlss/bin/ngx_smoke
export APPIMAGE_EXTRACT_AND_RUN=1
export QMAKE="$QT_ROOT_DIR/bin/qmake"
export EXTRA_QT_MODULES=waylandcompositor
export EXTRA_PLATFORM_PLUGINS='libqwayland-egl.so;libqwayland-generic.so'
export LDAI_VERSION="$DLSS_TAG-${DLSS_SOURCE:0:7}"
export OUTPUT="$PWD/out/lichii-dlss-linux-x86_64-pgo.AppImage"
export LDAI_OUTPUT="$OUTPUT"
export ARCH=x86_64
"$tools/linuxdeploy-x86_64.AppImage" --appdir AppDir \
  --executable build/dlss/bin/lichii --executable build/dlss/bin/eden-cli \
  --executable build/dlss/bin/ngx_smoke \
  --desktop-file dist/io.github.zortos293.lichii.desktop \
  --icon-file "$RUNNER_TEMP/io.github.zortos293.lichii.png" \
  --exclude-library=libvulkan.so.1 --plugin qt --output appimage
test -s "$OUTPUT"
python3 - <<'PY'
import hashlib,json,os,pathlib
p=pathlib.Path('out/lichii-dlss-linux-x86_64-pgo.AppImage')
h=hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
metadata={'tag':os.environ['DLSS_TAG'],'base_release':os.environ['DLSS_BASE'],
 'source_commit':os.environ['DLSS_SOURCE'],'repository':os.environ['GITHUB_REPOSITORY'],
 'asset':p.name,'sha256':h,'size':p.stat().st_size,'native_linux_dlss':True,
 'official_self_updater':False,'proprietary_runtime_included':False,
 'unit_tests':'passed before packaging','gpu_gameplay':'requires target-PC validation'}
pathlib.Path('out/build.json').write_text(json.dumps(metadata,indent=2)+'\n')
pathlib.Path('out/SHA256SUMS').write_text(h+'  '+p.name+'\n')
pathlib.Path('out/release-notes.txt').write_text(
 'Experimental Linux NVIDIA DLSS/DLAA fork for Batocera, based on '+os.environ['DLSS_BASE']+'.\n\n'
 'Native DLSS integration by myshadowww (upstream PR #840), merged with newer Lichii fixes. '
 'Optional neural rendering stays disabled by default. DLSS supports recognized game passes; '
 'it does not enable DLSS in every game.\n\n'
 'This self-contained x86-64 PGO AppImage requires glibc 2.39+, a compatible NVIDIA driver '
 'and separately downloaded NVIDIA DLSS runtime. NVIDIA models are not included. '
 'The official self-updater is disabled in this experimental binary so normal Lichii and '
 'this fork can be updated independently.\n\nSource: https://github.com/'
 +os.environ['GITHUB_REPOSITORY']+'/tree/'+os.environ['DLSS_SOURCE']+'\n')
PY
