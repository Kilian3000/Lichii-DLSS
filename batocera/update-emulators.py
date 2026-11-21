#!/usr/bin/env python3
from pathlib import Path
import datetime
import fcntl
import hashlib
import json
import os
import shutil
import sys
import tempfile
import urllib.request

common = Path('/userdata/system/lichii')
repositories = {'lichii': 'zortos293/Lichii', 'eglantine': 'Eglantine-Community/Eglantine',
                'lichii-dlss': 'Kilian3000/Lichii-DLSS'}

def request(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={
        'User-Agent': 'Batocera-Switch2-Updater', 'Accept': 'application/vnd.github+json'}), timeout=60)

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while block := f.read(8 * 1024 * 1024):
            h.update(block)
    return h.hexdigest()

def point(path, target):
    temporary = path.with_name('.' + path.name + '.' + str(os.getpid()))
    temporary.symlink_to(target.name)
    os.replace(temporary, path)

def backup(app_dir):
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    target = app_dir / 'backups' / stamp
    target.mkdir(parents=True)
    shutil.copytree(app_dir / 'profile/config', target / 'config', symlinks=True)
    shutil.copytree(common / 'profile/data/eden/nand', target / 'nand', symlinks=True)
    if (app_dir / 'install.json').exists():
        shutil.copy2(app_dir / 'install.json', target / 'install.json')
    return target

def update(name, check_only=False):
    repo = repositories[name]
    app_dir = Path('/userdata/system') / name
    with request('https://api.github.com/repos/' + repo + '/releases?per_page=100') as f:
        releases = json.load(f)
    def compatible_release(release):
        if release['draft']:
            return False
        if name == 'eglantine':
            return release['tag_name'].startswith(('daily-', 'v0.'))
        if name == 'lichii-dlss':
            return release['tag_name'].startswith('dlss-build-')
        return release['name'].lower().startswith('lichii nx2 build ')
    eligible = [r for r in releases if compatible_release(r)]
    eligible.sort(key=lambda r: r['published_at'], reverse=True)
    wanted = [f'{name}-linux-x86_64-pgo.AppImage', f'{name}-linux-x86_64.AppImage']
    selected = None
    for release in eligible:
        for filename in wanted:
            asset = next((a for a in release['assets'] if a['name'] == filename), None)
            if asset:
                selected = (release, asset)
                break
        if selected:
            break
    if selected is None:
        raise RuntimeError('No compatible official release found for ' + name)
    release, asset = selected
    expected = asset.get('digest', '')
    if not expected or not expected.startswith('sha256:'):
        raise RuntimeError('Release has no published SHA256 checksum')
    expected = expected.removeprefix('sha256:')
    print(name.title() + ': ' + release['name'], flush=True)
    state_path = app_dir / 'install.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    rejected = state.get('rejected_releases', {})
    failure = rejected.get(release['tag_name'], {})
    if failure.get('sha256') == expected:
        print('Skipped: this exact build failed testing on this PC.', flush=True)
        print(failure.get('reason', 'The previous build worked better.'), flush=True)
        print('Your working build is kept. A newer or rebuilt release can still update.\n', flush=True)
        return
    current = (app_dir / 'current.AppImage').resolve(strict=True)
    if digest(current) == expected:
        print('Already up to date.\n', flush=True)
        return
    if check_only:
        print('Update available; check only, nothing changed.\n', flush=True)
        return
    with tempfile.NamedTemporaryFile('wb', dir=app_dir, suffix='.part', delete=False) as f:
        temporary = Path(f.name)
        try:
            h = hashlib.sha256()
            total = 0
            previous = -1
            with request(asset['browser_download_url']) as response:
                while block := response.read(1024 * 1024):
                    f.write(block)
                    h.update(block)
                    total += len(block)
                    progress = total * 10 // asset['size']
                    if progress != previous:
                        print(f'Downloading: {min(progress * 10, 100)}%', flush=True)
                        previous = progress
            f.flush()
            os.fsync(f.fileno())
            if total != asset['size'] or h.hexdigest() != expected:
                raise RuntimeError('Download checksum or size differs; current build preserved')
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    with temporary.open('rb') as f:
        if f.read(4) != b'\x7fELF':
            temporary.unlink()
            raise RuntimeError('Download is not a Linux executable')
    temporary.chmod(0o755)
    saved = backup(app_dir)
    tag = ''.join(c if c.isalnum() or c in '-_.' else '_' for c in release['tag_name'])
    target = app_dir / f'{name}-{tag}-{expected[:12]}.AppImage'
    os.replace(temporary, target)
    point(app_dir / 'previous.AppImage', current)
    point(app_dir / 'current.AppImage', target)
    (app_dir / 'install.json').write_text(json.dumps({
        'repository': repo, 'tag': release['tag_name'], 'name': release['name'],
        'asset': asset['name'], 'sha256': expected, 'file': target.name,
        'previous': current.name, 'backup': str(saved), 'url': release['html_url'],
        'rejected_releases': rejected,
    }, indent=2))
    print('Installed. Previous build and settings backup retained.\n', flush=True)

def rollback(name):
    app_dir = Path('/userdata/system') / name
    previous = app_dir / 'previous.AppImage'
    if not previous.exists():
        print(name.title() + ': no previous build is available yet.')
        return
    old = (app_dir / 'current.AppImage').resolve(strict=True)
    target = previous.resolve(strict=True)
    backup(app_dir)
    point(app_dir / 'current.AppImage', target)
    point(previous, old)
    print(name.title() + ' now uses ' + target.name)
    print('Settings and saves were kept. The other build remains available.')

if __name__ == '__main__':
    try:
        with (common / 'profile/launch.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('Exit the Switch 2 emulator before updating')
            names = ['lichii', 'eglantine'] if sys.argv[1] == 'both' else [sys.argv[1]]
            for name in names:
                if name not in repositories:
                    raise RuntimeError('Unknown emulator')
                if '--rollback' in sys.argv:
                    rollback(name)
                else:
                    update(name, '--check' in sys.argv)
    except Exception as e:
        print('\n' + str(e), file=sys.stderr, flush=True)
        sys.exit(1)
