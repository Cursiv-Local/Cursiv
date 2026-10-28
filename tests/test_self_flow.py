"""Static control slices retain source order and branch guards without execution."""
import ast
import json
import pytest
from cursiv_engine.core import self_index, self_inspection


def flow(text,topic='models',limit=4500):
    _,symbols=self_index._parse('cursiv_engine/core/example.py',text)
    return self_inspection._flow('cursiv_engine/core/example.py',symbols[0],text.splitlines(),topic,limit)


def test_return_does_not_move_a_stop_before_prior_provider_attempts():
    text=('def fallback(runtime, local_tried):\n'
          '    for provider in ("Groq", "Gemini"):\n'
          '        if runtime.allowed():\n'
          '            provider_call(provider)\n'
          '    if local_tried:\n'
          '        return\n'
          '    return runtime._local_stream()\n')
    value=flow(text)
    assert value['scope'].startswith('complete')
    tree=ast.parse(value['code']).body[0]
    assert isinstance(tree.body[0],ast.For)
    assert isinstance(tree.body[1],ast.If) and ast.unparse(tree.body[1].test)=='local_tried'
    assert isinstance(tree.body[2],ast.Return)


def test_confirmation_branch_keeps_early_return_and_later_save_separate():
    text=('def command(preview):\n'
          '    if preview is not None:\n'
          '        return show(preview)\n'
          '    return save()\n')
    value=flow(text,'confirmation')
    tree=ast.parse(value['code']).body[0]
    assert isinstance(tree.body[0],ast.If)
    assert ast.unparse(tree.body[0].body[0])=='return show(preview)'
    assert ast.unparse(tree.body[1])=='return save()'


def test_nested_bodies_and_long_prose_are_marked_as_abbreviated():
    text=('def parent():\n'
          '    """Misleading prose does not establish behavior."""\n'
          '    def later():\n'
          '        secret_operation()\n'
          '    message = '+repr('prose '*200)+'\n'
          '    return later\n')
    value=flow(text)
    assert 'Misleading prose' not in value['code']
    assert 'secret_operation' not in value['code']
    assert set(value['abbreviated'])=={'long string literal','nested definition body'}


def test_large_functions_keep_whole_selected_blocks_and_label_gaps():
    text=('def route(runtime, condition):\n'
          '    unused = '+repr('a long irrelevant value')+'\n'
          '    if condition:\n'
          '        return runtime._local_stream()\n'
          '    unrelated_call('+', '.join('parameter_'+str(n) for n in range(60))+')\n')
    value=flow(text,limit=100)
    assert value and value['scope'].startswith('partial') and value['omitted_blocks']
    tree=ast.parse(value['code'])
    assert isinstance(tree.body[0],ast.If) and isinstance(tree.body[0].body[0],ast.Return)
    assert len(value['code'])<=100


def test_real_source_context_exposes_decisive_confirmation_and_fallback_order():
    token=self_inspection._active.set(None)
    try:
        confirmation=self_inspection.prepare('Where does your code enforce confirmation?')
        assert confirmation and not confirmation.error
        code=next(f['code'] for f in confirmation.flows if f['symbol']=='command')
        assert "return Result(CREATE, 'preview'" in code
        assert 'execute(VERIFY' not in code
        fallback=self_inspection.prepare('What happens if your local model fails?')
        assert fallback and not fallback.error
        code=next(f['code'] for f in fallback.flows if f['symbol']=='_fallback_chain')
        assert code.index('for label, field, fn')<code.index('if local_tried:')
        assert len(fallback.prompt().encode('utf-8'))<=4900
        assert not self_inspection.problems('The offline branch calls `_without_model()`.')
    finally:
        self_inspection._active.reset(token)
