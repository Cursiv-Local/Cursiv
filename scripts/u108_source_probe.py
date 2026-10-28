"""Inspect this checkout read-only, with disposable app state and citation validation."""
import ast
import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT/'bench/results/U108-own-source.json')
    args = parser.parse_args()
    home = Path(tempfile.mkdtemp(prefix='u108-source-', dir=ROOT/'reports'))
    os.environ.update(HOME=str(home), USERPROFILE=str(home), CURSIV_APP_DATA=str(home/'app'),
                      CURSIV_NO_ENGINE_START='1')
    sys.path[:0] = [str(ROOT), str(ROOT/'launcher')]
    from cursiv_engine.core import source_inspection
    rows = []
    for question in ('Trace what happens when a user sends a message.', 'Inspect Field Notebook retrieval code.'):
        reply = source_inspection.investigate(question, ROOT)
        references = re.findall(r'([\w/.-]+\.(?:py|md|mjs|js|ts)):(\d+)', reply.text)
        correct = sum((ROOT/name).is_file() and 1 <= int(line) <= len((ROOT/name).read_text(encoding='utf-8').splitlines())
                      for name, line in references)
        declarations = re.findall(r'([\w/.-]+\.py):(\d+) — declaration(?: candidate)? `([^`]+)`', reply.text)
        accurate = 0
        for name, line, symbol in declarations:
            tree = ast.parse((ROOT/name).read_text(encoding='utf-8'))
            accurate += any(getattr(node,'name',None)==symbol and node.lineno==int(line) for node in ast.walk(tree))
        rows.append(dict(question=question, answer=reply.text, file_references=len(references),
                         valid_file_references=correct, declarations=len(declarations),
                         valid_declarations=accurate, read_receipts=len(reply.receipts),
                         model_requests=0, code_execution=False,
                         limitation='Static excerpts, bounded discovery; no claim of complete runtime control flow.'))
    output = args.output
    if output.exists():
        raise SystemExit('Refusing to overwrite evidence')
    output.write_text(json.dumps(dict(rows=rows),indent=2)+'\n',encoding='utf-8')
    for row in rows:
        print({k:v for k,v in row.items() if k != 'answer'})


if __name__ == '__main__':
    main()
