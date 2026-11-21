#!/usr/bin/env python3
"""Apply frontend renderer choices for one session; restore emulator preferences on exit."""
from pathlib import Path
import json
import os
import shutil
import sys

STYLE_KEY = 'lichii_dlss_neural'
STRENGTH_KEY = 'lichii_dlss_neural_strength'
QUALITY_KEY = 'lichii_dlss_quality'
FRAME_GENERATION_KEY = 'lichii_frame_generation'
FRAME_GENERATION = {'off', '2', '3', '4'}
STYLES = {'off': '0', 'standard': '1', 'natural': '2', 'cinematic': '3'}
QUALITIES = {'game': '0', 'native': '1', 'quality': '2', 'balanced': '3',
             'performance': '4', 'ultra': '5'}
STRENGTHS = {'25', '50', '75', '100'}
STATE = '.batocera-neural-overrides.json'
ALLOWED = {'neural_rendering', 'neural_rendering_strength', 'nvidia_dlss', 'nvidia_dlss_quality',
           'frame_gen', 'frame_gen_type', 'frame_gen_multiplier', 'frame_gen_target_rate'}


def resolve(load_all, rom, emulator='lichii-dlss'):
    """Use Batocera's normal global/system/folder/game precedence and Auto inheritance."""
    if emulator not in ('lichii', 'lichii-dlss'):
        raise ValueError('Unsupported renderer-settings emulator')
    keys = {FRAME_GENERATION_KEY}
    if emulator == 'lichii-dlss':
        keys.update((STYLE_KEY, STRENGTH_KEY, QUALITY_KEY))
    game = Path(rom).name.replace('=', '').replace('#', '')
    result = {}
    for prefix in ('global', 'switch2', f'switch2.folder["{Path(rom).parent}"]',
                   f'switch2["{game}"]'):
        for key, value in load_all(prefix).items():
            if key in keys and value not in ('', 'auto', 'default'):
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
    frame_generation = result.get(FRAME_GENERATION_KEY)
    if frame_generation is not None:
        if frame_generation not in FRAME_GENERATION:
            raise ValueError('Invalid Batocera frame-generation choice')
        updates['frame_gen'] = 'false' if frame_generation == 'off' else 'true'
        if frame_generation != 'off':
            updates.update(frame_gen_type='1', frame_gen_multiplier=frame_generation,
                           frame_gen_target_rate='0')
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
            raise ValueError('Unexpected renderer-settings recovery path')
        for key in entry['original']:
            if key.split('\\', 1)[0] not in ALLOWED:
                raise ValueError('Unexpected renderer-settings recovery key')
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
        emulator = sys.argv[4] if len(sys.argv) > 4 else 'lichii-dlss'
        updates = resolve(settings.load_all, sys.argv[3], emulator)
        apply(root, updates)
        if updates:
            print('Batocera renderer session preferences:', json.dumps(updates), flush=True)
    else:
        raise ValueError('Unknown renderer-settings action')


if __name__ == '__main__':
    main()
