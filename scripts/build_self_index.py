"""Build the versioned public own-source index without reading untracked owner files."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cursiv_engine.core import self_index


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/self_index.NAME)
    args=parser.parse_args()
    version=re.search(r'^VERSION = "([^"]+)"', (ROOT/'cursiv_engine/core/selfknow.py').read_text(), re.M)[1]
    index=self_index.build(ROOT,version)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(index,separators=(',',':'))+'\n',encoding='utf-8')
    print(f"Indexed {len(index['files'])} public files and {sum(len(v['symbols']) for v in index['files'].values())} symbols; {version}; {index['snapshot'][:12]}")


if __name__=='__main__':
    main()
