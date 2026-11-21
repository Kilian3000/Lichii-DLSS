#!/usr/bin/env python3
from pathlib import Path
import configparser
import datetime
import fcntl
import hashlib
import json
import os
import shutil


def hashes(directory):
    return {str(p.relative_to(directory)): hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
            for p in directory.rglob('*') if p.is_file()}


def update_ini(path, changes):
    lines = path.read_text().splitlines(keepends=True)
    for section, updates in changes.items():
        start = next((i for i, line in enumerate(lines) if line.strip() == f'[{section}]'), None)
        if start is None:
            lines.extend(['\n', f'[{section}]\n'])
            start = len(lines) - 1
        end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith('[')), len(lines))
        seen = set()
        for i in range(start + 1, end):
            key = lines[i].split('=', 1)[0]
            if key in updates:
                lines[i] = key + '=' + updates[key] + '\n'
                seen.add(key)
        lines[end:end] = [key + '=' + value + '\n' for key, value in updates.items() if key not in seen]
    temporary = path.with_suffix('.new')
    temporary.write_text(''.join(lines))
    shutil.copystat(path, temporary)
    os.replace(temporary, path)


normal = Path('/userdata/system/lichii')
base = Path('/userdata/system/lichii-dlss')
lock = (normal/'profile/launch.lock').open('a')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
marker = base/'profile-ready.json'
if marker.exists():
    raise RuntimeError('DLSS profile already initialized; use the updater instead of recreating it')
stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
backup = base/'backups'/('before-dlss-setup-' + stamp)
backup.mkdir(parents=True)
for source in [normal/'launch.sh', normal/'update-emulators.py', normal/'update-emulators.sh',
               Path('/userdata/system/configs/emulationstation/es_systems_switch2.cfg'),
               Path('/userdata/system/configs/emulationstation/es_features_switch2.cfg')]:
    shutil.copy2(source, backup/source.name)
shutil.copytree(normal/'profile/config', backup/'normal-config', symlinks=True)
nand = (normal/'profile/data/lichii/nand').resolve(strict=True)
saves = hashes(nand)
shutil.copytree(nand, backup/'shared-nand', symlinks=True)
assert hashes(backup/'shared-nand') == saves
(backup/'shared-save-manifest.json').write_text(json.dumps(saves, indent=2)+'\n')
print('Backed up existing settings, integration and shared saves', flush=True)

profile = base/'profile'
shutil.copytree(normal/'profile/config/lichii', profile/'config/lichii', symlinks=True)
shutil.copytree(normal/'profile/data/lichii', profile/'data/lichii', symlinks=True)
for name in ('nand', 'keys', 'sdmc', 'load', 'amiibo', 'post_shaders', 'post_presets'):
    destination = profile/'data/lichii'/name
    if destination.is_symlink() or destination.is_file():
        destination.unlink()
    elif destination.is_dir():
        shutil.rmtree(destination)
    (normal/'profile/data/lichii'/name).mkdir(exist_ok=True)
    destination.symlink_to(normal/'profile/data/lichii'/name, target_is_directory=True)
migration = normal/'profile/data/lichii.migration'
if migration.exists():
    shutil.copytree(migration, profile/'data/lichii.migration', symlinks=True)
print('Connected shared saves, keys and installed game content', flush=True)
shutil.copytree(normal/'profile/cache/lichii', profile/'cache/lichii', symlinks=True)
print('Seeded a separate DLSS shader cache from the existing cache', flush=True)

config = profile/'config/lichii/qt-config.ini'
renderer = {'nvidia_dlss':'true', 'nvidia_dlss\\default':'false',
            'nvidia_dlss_quality':'0', 'nvidia_dlss_quality\\default':'false',
            'neural_rendering':'0', 'neural_rendering\\default':'false'}
storage = {}
for name in ('nand', 'sdmc', 'load', 'dump', 'tas'):
    storage[name+'_directory'] = str(profile/'data/lichii'/name)
    storage[name+'_directory\\default'] = 'false'
update_ini(config, {'Renderer':renderer, 'Data%20Storage':storage,
                   'UI':{'Screenshots\\screenshot_path':str(profile/'data/lichii/screenshots'),
                         'check_for_updates':'false', 'check_for_updates\\default':'false'}})
for custom in (profile/'config/lichii/custom').glob('*.ini'):
    update_ini(custom, {'Renderer':{'nvidia_dlss\\use_global':'true',
                                   'nvidia_dlss_quality\\use_global':'true',
                                   'neural_rendering\\use_global':'true'}})
assert (profile/'data/lichii/nand').resolve() == nand
assert hashes(nand) == saves
state = {'created':stamp, 'backup':str(backup), 'normal_profile':str(normal/'profile'),
         'shared_nand':str(nand), 'save_files':len(saves), 'saves_unchanged':True,
         'dlss_enabled':True, 'neural_rendering':'Off', 'shader_cache':'independent, seeded'}
marker.write_text(json.dumps(state, indent=2)+'\n')
print(json.dumps(state), flush=True)
