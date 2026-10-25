"""Limit working-tree snapshots; Git history still retains older revisions."""
import json
from pathlib import Path
import shutil
root = Path(__file__).parent / 'data'
current = json.loads((root/'current.json').read_text())['version']
folders = sorted((root/'versions').iterdir(), key=lambda p:p.name, reverse=True)
keep = {current}
for folder in folders:
    if folder.name != current:
        keep.add(folder.name)
        break
for folder in folders:
    if folder.is_dir() and folder.name not in keep:
        shutil.rmtree(folder)
