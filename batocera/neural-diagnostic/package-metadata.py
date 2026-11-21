#!/usr/bin/env python3
"""Mark the packaging script's output unambiguously as a manual diagnostic artifact."""
import hashlib
import json
from pathlib import Path
import shutil

out = Path('out')
asset = out / 'lichii-nr-diagnostic-linux-x86_64.AppImage'
(out / 'lichii-dlss-linux-x86_64-pgo.AppImage').rename(asset)
digest = hashlib.file_digest(asset.open('rb'), 'sha256').hexdigest()
metadata = json.loads((out / 'build.json').read_text())
metadata.update(asset=asset.name, sha256=digest, diagnostic_only=True,
                release_published=False, automatic_install=False,
                runtime_source_patch='batocera/neural-diagnostic/runtime.patch',
                patch_sha256=hashlib.sha256(Path('batocera/neural-diagnostic/runtime.patch').read_bytes()).hexdigest(),
                options_sha256=hashlib.sha256(Path('batocera/neural-diagnostic/options.h').read_bytes()).hexdigest(),
                gpu_gameplay='Unvalidated until target-GPU tests complete')
(out / 'build.json').write_text(json.dumps(metadata, indent=2) + '\n')
(out / 'SHA256SUMS').write_text(digest + '  ' + asset.name + '\n')
(out / 'release-notes.txt').unlink()
shutil.copyfile('batocera/neural-diagnostic/README.md', out / 'README.md')
