#!/usr/bin/env python3
"""Apply frontend neural choices for one session; restore emulator preferences on exit."""
from pathlib import Path
import json
import os
import shutil
import sys

STYLE_KEY = 'lichii_dlss_neural'
STRENGTH_KEY = 'lichii_dlss_neural_strength'
QUALITY_KEY = 'lichii_dlss_quality'
STYLES = {'off': '0', 'standard': '1', 'natural': '2', 'cinematic': '3'}
QUALITIES = {'game': '0', 'native': '1', 'quality': '2', 'balanced': '3',
             'performance': '4', 'ultra': '5'}
STRENGTHS = {'25', '50', '75', '100'}
STATE = '.batocera-neural-overrides.json'
ALLOWED = {'neural_rendering', 'neural_rendering_strength', 'nvidia_dlss', 'nvidia_dlss_quality'}


def resolve(load_all, rom):
    """Use Batocera's normal global/system/folder/game precedence and Auto inheritance."""
    game = Path(rom).name.replace('=', '').replace('#', '')
    result = {}
    for prefix in ('global', 'switch2', f'switch2.folder["{Path(rom).parent}"]',
                   f'switch2["{game}"]'):
        for key, value in load_all(prefix).items():
            if key in (STYLE_KEY, STRENGTH_KEY, QUALITY_KEY) and value not in ('', 'auto', 'default'):
                result[key] = value
    style, strength = result.get(STYLE_KEY), result.get(STRENGTH_KEY)
    if style is not None and style not in STYLES:
        raise ValueError('Invalid Batocera neural-rendering choice')
    if strength is not None and strength not in STRENGTHS:
        raise ValueError('Invalid Batocera neural-rendering strength')
    quality = result.get(QUALITY_KEY)
    if quality is not None and quality not in QUALITIES:
        raise ValueError('Invalid Batocera DLSS quality choice')
    updates = {}
    if style is not None:
        updates['neural_rendering'] = STYLES[style]
        if style != 'off':
            updates['nvidia_dlss'] = 'true'
    if strength is not None:
        updates['neural_rendering_strength'] = strength
    if quality is not None:
        updates['nvidia_dlss_quality'] = QUALITIES[quality]
    return updates


def renderer_lines(path):
    lines = path.read_text().splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if line.strip() == '[Renderer]'), None)
    if start is None:
        return lines, len(lines), len(lines)
    end = next((i for i in range(start+1, len(lines)) if lines[i].lstrip().startswith('[')), len(lines))
    return lines, start+1, end


def read_keys(path, keys):
    lines, start, end = renderer_lines(path)
    result = dict.fromkeys(keys)
    for line in lines[start:end]:
        key, sep, value = line.rstrip('\r\n').partition('=')
        if sep and key.strip() in keys:
            result[key.strip()] = value
    return result


def write_keys(path, updates):
    lines, start, end = renderer_lines(path)
    if start == end == len(lines) and not any(x.strip() == '[Renderer]' for x in lines):
        if lines and not lines[-1].endswith('\n'):
            lines[-1] += '\n'
        lines.extend(['\n', '[Renderer]\n'])
        start = end = len(lines)
    section, seen = [], set()
    for line in lines[start:end]:
        key = line.partition('=')[0].strip()
        if key in updates:
            if key not in seen and updates[key] is not None:
                section.append(key+'='+updates[key]+'\n')
            seen.add(key)
        else:
            section.append(line)
    if section and not section[-1].endswith('\n'):
        section[-1] += '\n'
    section.extend(key+'='+value+'\n' for key, value in updates.items()
                   if key not in seen and value is not None)
    lines[start:end] = section
    temporary = path.with_name(path.name+'.batocera-new')
    temporary.write_text(''.join(lines))
    shutil.copystat(path, temporary)
    os.replace(temporary, path)


def restore(root):
    state = root/STATE
    if not state.exists():
        return
    entries = json.loads(state.read_text())
    for entry in entries:
        path = root/entry['path']
        if path.parent not in (root, root/'custom') or path.suffix != '.ini':
            raise ValueError('Unexpected neural-settings recovery path')
        for key in entry['original']:
            if key.split('\\', 1)[0] not in ALLOWED:
                raise ValueError('Unexpected neural-settings recovery key')
        if path.exists():
            write_keys(path, entry['original'])
    state.unlink()


def apply(root, updates):
    restore(root)  # Also recovers a session interrupted by power loss.
    if not updates:
        return
    plans = []
    global_updates = {}
    for key, value in updates.items():
        global_updates[key] = value
        global_updates[key+'\\default'] = 'false'
    plans.append((root/'qt-config.ini', global_updates))
    inherit = {key+'\\use_global': 'true' for key in updates}
    plans.extend((p, inherit) for p in sorted((root/'custom').glob('*.ini')))
    entries = [dict(path=str(p.relative_to(root)), original=read_keys(p, values))
               for p, values in plans]
    state = root/STATE
    temporary = state.with_suffix('.new')
    temporary.write_text(json.dumps(entries, indent=2)+'\n')
    temporary.chmod(0o600)
    os.replace(temporary, state)  # Persist recovery before changing any preference.
    try:
        for path, values in plans:
            write_keys(path, values)
    except BaseException:
        restore(root)
        raise


def main():
    action, folder = sys.argv[1:3]
    root = Path(folder)
    if action == 'restore':
        restore(root)
    elif action == 'apply':
        from configgen.settings.unixSettings import UnixSettings
        settings = UnixSettings('/userdata/system/batocera.conf')
        updates = resolve(settings.load_all, sys.argv[3])
        apply(root, updates)
        if updates:
            print('Batocera DLSS session preferences:', json.dumps(updates), flush=True)
    else:
        raise ValueError('Unknown renderer-settings action')


if __name__ == '__main__':
    main()
