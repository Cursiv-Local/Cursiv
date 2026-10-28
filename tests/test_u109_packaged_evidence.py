"""Read the actual public inventory from an isolated PyInstaller-shaped data root."""
import json
import shutil
import sys
from pathlib import Path
import pytest
from cursiv_engine.core import self_source, self_index, self_inspection as own


@pytest.fixture
def bundle(tmp_path,monkeypatch):
    root=self_source.root()
    index=self_index.load(root,self_source.version())
    staged=tmp_path/'_internal'
    for rel in [*index['files'],self_index.NAME]:
        target=staged/rel
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(root/rel,target)
    monkeypatch.setattr(sys,'frozen',True,raising=False)
    monkeypatch.setattr(sys,'_MEIPASS',str(staged),raising=False)
    assert self_source.root()==staged
    return staged


def test_ten_features_have_real_source_reads_from_bundle(bundle):
    corpus=json.loads((Path(__file__).resolve().parents[1]/'bench/u109-self-inspection.json').read_text())
    wanted={'notebook','chain','memory','pdf','documents','offline','ollama','portable','verification','permissions'}
    for case in corpus['development']:
        if case['id'] not in wanted:continue
        packet=own.prepare(case['question'])
        assert packet and not packet.error,case['id']
        assert packet.coverage['successful_reads']>0
        assert packet.coverage['scope']=='installed_application'
        assert all((bundle/s.path).is_file() for s in packet.snippets)
        wanted.remove(case['id'])
    assert not wanted


def test_changed_packaged_source_cannot_keep_verified_status(bundle):
    path=bundle/'cursiv_engine/core/documents.py'
    path.write_bytes(path.read_bytes()+b'\n# changed after packaging\n')
    packet=own.prepare('Locate the PDF importer in your installed code.')
    assert packet.error and packet.status=='UNKNOWN'
    assert packet.coverage['successful_reads']==0
    assert packet.coverage['unavailable']


def test_new_analyzer_is_in_public_build_inventory():
    assert 'cursiv_engine/core/source_analysis.py' in self_index.ADDITIONS
    assert 'cursiv_engine/core/source_analysis.py' in self_index.public_files(self_source.root())
    assert '_bundle.update(self_index.ADDITIONS)' in (self_source.root()/'launcher/build.spec').read_text()
