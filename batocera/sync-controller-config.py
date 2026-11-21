#!/usr/bin/env python3
"""Share controller preferences without sharing graphics or other emulator settings."""
from pathlib import Path
import os
import shutil
import sys


def section_bounds(lines, name):
    start = next((i for i, line in enumerate(lines) if line.strip() == f'[{name}]'), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith('[')), len(lines))
    return start, end


def replace_controls(source, target, required=False):
    source_lines = source.read_text().splitlines(keepends=True) if source.exists() else []
    bounds = section_bounds(source_lines, 'Controls')
    if required and bounds is None:
        raise RuntimeError('The shared Lichii controller settings are missing')
    controls = source_lines[bounds[0]:bounds[1]] if bounds else []
    old_text = target.read_text() if target.exists() else ''
    target_lines = old_text.splitlines(keepends=True)
    bounds = section_bounds(target_lines, 'Controls')
    if bounds is not None:
        target_lines[bounds[0]:bounds[1]] = controls
        # A final source section may not end in a newline; keep the following target
        # section separate without changing its keys or values.
        if controls and bounds[0] + len(controls) < len(target_lines):
            last = bounds[0] + len(controls) - 1
            if not target_lines[last].endswith('\n'):
                target_lines[last] += '\n'
    elif controls:
        if target_lines and not target_lines[-1].endswith('\n'):
            target_lines[-1] += '\n'
        target_lines.extend(['\n', *controls])
    new_text = ''.join(target_lines)
    if new_text == old_text:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + '.controls-new')
    temporary.write_text(new_text)
    if target.exists():
        shutil.copystat(target, temporary)
    os.replace(temporary, target)


def sync(source, target):
    # Validate the authoritative global profile before touching any other files.
    replace_controls(source, target, required=True)
    source_root, target_root = source.parent, target.parent
    source_custom, target_custom = source_root / 'custom', target_root / 'custom'
    names = {p.name for folder in (source_custom, target_custom) for p in folder.glob('*.ini')}
    for name in sorted(names):
        # Missing source controls mean inherit global controls, including when an
        # override was removed. Other per-game sections remain independent.
        replace_controls(source_custom / name, target_custom / name)

    source_input, target_input = source_root / 'input', target_root / 'input'
    profiles = {p.name: p for p in source_input.glob('*.ini') if p.is_file()}
    if profiles:
        target_input.mkdir(parents=True, exist_ok=True)
    for name, profile in profiles.items():
        destination = target_input / name
        if destination.is_file() and destination.read_bytes() == profile.read_bytes():
            continue
        temporary = destination.with_name(destination.name + '.controls-new')
        shutil.copy2(profile, temporary)
        os.replace(temporary, destination)
    for profile in target_input.glob('*.ini'):
        if profile.name not in profiles and (profile.is_file() or profile.is_symlink()):
            profile.unlink()


def main():
    source, target = map(Path, sys.argv[1:3])
    sync(source, target)


if __name__ == '__main__':
    main()
