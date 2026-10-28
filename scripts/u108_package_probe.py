"""Exercise the own-source packaging plan in a synthetic checkout, without building an app."""
from pathlib import Path
from unittest.mock import patch
import argparse
import json
import os
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Refusing to overwrite evidence')
    with tempfile.TemporaryDirectory(prefix='u108-package-') as folder:
        base = Path(folder)
        home = base/'home'
        home.mkdir()
        os.environ.update(HOME=str(home), USERPROFILE=str(home), CURSIV_APP_DATA=str(home/'app'))
        sys.path.insert(0,str(ROOT))
        from cursiv_engine.core import self_index
        sources = {
            'cursiv_engine/core/selfknow.py': 'VERSION = "package-test"\n',
            'cursiv_engine/core/example.py': 'def explain():\n    return "public code"\n',
            'docs/guide.md': '# Public guide\n',
            'launcher/example.py': 'def start():\n    return True\n',
            'README.md': '# Synthetic package\n',
        }
        for name, text in {**sources, 'docs/untracked-owner-note.md': 'PRIVATE_MARKER'}.items():
            path=base/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text,encoding='utf-8')
        spec=(ROOT/'launcher/build.spec').read_text(encoding='utf-8')
        prefix=spec.split('# ── Hidden imports')[0]
        assert 'a = Analysis(' not in prefix
        modules={name:types.ModuleType(name) for name in ('PyInstaller','PyInstaller.utils','PyInstaller.utils.hooks')}
        modules['PyInstaller.utils.hooks'].collect_data_files=lambda *a: []
        modules['PyInstaller.utils.hooks'].collect_submodules=lambda *a: []
        namespace=dict(SPECPATH=str(base/'launcher'))
        with patch.dict(sys.modules,modules), patch.object(self_index.subprocess,'check_output',return_value=('\0'.join(sources)+'\0').encode()):
            exec(compile(prefix,'launcher/build.spec','exec'),namespace)
        plan=namespace['datas']
        destinations=[]
        for source,directory in plan:
            path=Path(source)
            if not path.is_file():
                continue  # the existing icon directory is not created in this fixture
            destination=Path(directory)/path.name
            destinations.append(destination.as_posix())
            assert 'PRIVATE_MARKER' not in path.read_text(encoding='utf-8')
        assert set(sources).issubset(destinations)
        assert self_index.NAME in destinations
        manifest=json.loads((base/'build/own-source/own_source_index.json').read_text())
        assert set(manifest['files'])==set(sources)
        frozen=base/'frozen'
        for source,directory in plan:
            path=Path(source)
            if path.is_file():
                target=frozen/directory/path.name
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(path.read_bytes())
        installed=self_index.load(frozen,'package-test')
        assert 'public code' in self_index.text(frozen,installed,'cursiv_engine/core/example.py')
        receipt=dict(kind='synthetic packaging-plan and frozen-layout probe; no app build',
                     public_files=len(sources), packaged_files=len(destinations),
                     private_untracked_excluded=True, generated_manifest=True,
                     frozen_hash_checked_read=True, version='package-test')
        args.output.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(receipt))


if __name__=='__main__':
    main()
