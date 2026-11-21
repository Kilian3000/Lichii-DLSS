#!/usr/bin/env python3
from pathlib import Path
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET

base = Path('/userdata/system/lichii-dlss')
setup = base/'setup'
normal = Path('/userdata/system/lichii')
lock = (normal/'profile/launch.lock').open('a')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
state = json.loads((base/'profile-ready.json').read_text())
backup = Path(state['backup'])
metadata = json.loads((base/'staging/build.json').read_text())
assert metadata['repository'] == 'Kilian3000/Lichii-DLSS'
assert metadata['native_linux_dlss'] and not metadata['official_self_updater']
asset = base/'staging/lichii-dlss-linux-x86_64-pgo.AppImage'
def digest(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
assert digest(asset) == metadata['sha256']
assert asset.stat().st_size == metadata['size']
with asset.open('rb') as stream:
    header = stream.read(20)
assert header[:4] == b'\x7fELF' and int.from_bytes(header[18:20], 'little') == 62
runtime = base/'profile/data/lichii/ngx/libnvidia-ngx-dlss.so.310.9.16'
assert digest(runtime) == '30982c937afed85c96b8d313323de9a650a2eec6de1bb0f714b21750f4ce98f6'
baseline = json.loads((setup/'baseline-integration.json').read_text())
destinations = {
    'launch.sh':normal/'launch.sh',
    'update-emulators.py':normal/'update-emulators.py',
    'update-emulators.sh':normal/'update-emulators.sh',
    'es_systems_switch2.cfg':Path('/userdata/system/configs/emulationstation/es_systems_switch2.cfg'),
    'es_features_switch2.cfg':Path('/userdata/system/configs/emulationstation/es_features_switch2.cfg'),
}
for name, path in destinations.items():
    assert path.read_text() == baseline[name], f'{name} changed since setup; merge it before installing'
for name in ('launch.sh','update-emulators.sh'):
    subprocess.run(['bash','-n',str(setup/name)],check=True)
for name in ('update-emulators.py','sync-controller-config.py','batocera-renderer.py'):
    compile((setup/name).read_text(),str(setup/name),'exec')
systems = ET.parse(setup/'es_systems_switch2.cfg')
assert [x.attrib['name'] for x in systems.findall('system/emulators/emulator')] == ['lichii','eglantine','lichii-dlss']
ET.parse(setup/'es_features_switch2.cfg')
normal_binary = (normal/'current.AppImage').resolve()
normal_sha = digest(normal_binary)
other = Path('/userdata/system/eglantine/current.AppImage').resolve()
other_sha = digest(other)
shutil.copy2('/userdata/system/batocera.conf',backup/'batocera.conf')
(backup/'batocera.conf').chmod(0o600)

target = base/f"{metadata['tag']}-{metadata['sha256'][:12]}.AppImage"
asset.chmod(0o755)
os.replace(asset,target)
temporary = base/'current.AppImage.new'
temporary.unlink(missing_ok=True)
temporary.symlink_to(target.name)
os.replace(temporary,base/'current.AppImage')
metadata.update(file=target.name,backup=str(backup),profile_name='lichii',
                previous=None,url='https://github.com/Kilian3000/Lichii-DLSS/releases/tag/'+metadata['tag'])
(base/'install.json').write_text(json.dumps(metadata,indent=2)+'\n')

def install(source, destination, mode):
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary = destination.with_name(destination.name+'.dlss-new')
    shutil.copyfile(source,temporary)
    temporary.chmod(mode)
    os.replace(temporary,destination)

for name,path in destinations.items():
    install(setup/name,path,0o755 if name.endswith(('.sh','.py')) else 0o644)
install(setup/'sync-controller-config.py',normal/'sync-controller-config.py',0o755)
install(setup/'batocera-renderer.py',normal/'batocera-renderer.py',0o755)
install(setup/'lichii-dlss-settings.desktop',Path('/userdata/system/.local/share/applications/lichii-dlss-settings.desktop'),0o644)
assert digest(normal_binary) == normal_sha and digest(other) == other_sha
assert (base/'profile/data/lichii/nand').resolve() == (normal/'profile/data/lichii/nand').resolve()
result = {'installed':metadata['tag'],'source_commit':metadata['source_commit'],
          'normal_lichii_binary_unchanged':True,'eglantine_binary_unchanged':True,
          'shared_saves':True,'shared_controller_preferences':True,'backup':str(backup),
          'emulator_choices':['lichii','eglantine','lichii-dlss']}
(base/'installation-check.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
