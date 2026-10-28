"""Reviewed critical-behavior explanations, conditional on inspected source.

AST witnesses anchor these maintained contracts; this is not a general Python
theorem prover. Changed/missing witnesses fail closed. No inspected code executes
and no notebook data is opened. A model never certifies these rules.
"""
from __future__ import annotations
import ast
import re
from . import self_index, self_source


def _nodes(function, kind):
    return [n for n in ast.walk(function) if isinstance(n,kind)]


def _has(function, text):
    return any(ast.unparse(n)==text for n in ast.walk(function))


def _returns(node):
    return any(isinstance(n,ast.Return) for n in node.body)


def answer(packet, question):
    topic=packet.topic
    if topic not in ('confirmation','correction','models'):
        return None
    if topic=='models' and not re.search(r'(?i)fail|fallback|local_tried|unavailable',question):
        return None
    try:
        base=self_source.root()
        index=self_index.load(base,packet.version)
        if index['snapshot']!=packet.snapshot:
            raise ValueError('source snapshot changed')
        trees={}
        def function(path,name):
            if not any(s.path==path for s in packet.snippets):
                raise ValueError('required implementation was not selected')
            if path not in trees:
                trees[path]=ast.parse(self_index.text(base,index,path))
            matches=[n for n in ast.walk(trees[path]) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name]
            if len(matches)!=1:
                raise ValueError('implementation declaration is ambiguous')
            return matches[0]
        def require(condition):
            if not condition:
                raise ValueError('reviewed behavior no longer matches its source witnesses')
        if topic=='correction':
            path='cursiv_engine/core/fieldlog.py'
            correct=function(path,'correct'); add=function(path,'add')
            append=function(path,'_append'); current=function(path,'current')
            require(_has(correct,'add(**base, corrects=entry_id, reason=reason)'))
            require(_has(add,'_append(**fields)'))
            require(_has(append,'private_store.write_text(log_file(), text + line)'))
            require(_has(append,"log_file().open('a', encoding='utf-8')"))
            require(_has(current,"{e['corrects'] for e in all_entries if e.get('corrects')}"))
            require(_has(current,"[e for e in all_entries if e['id'] not in replaced]"))
            return ('A correction appends a new record linked to the original by `corrects`, with a reason. '
                    'The original stays in the stored log; `current()` hides superseded entries in the current view. '
                    '`correct()` calls `add()`, which calls `_append()`; storage retains the old text plus the new line. '
                    'These are checked implementation rules; your notebook records were not opened.')
        if topic=='confirmation':
            command=function('cursiv_engine/core/notebook_tools.py','command')
            run=function('launcher/chat_panel.py','_run_turn')
            approve=function('launcher/chat_actions.py','_answer_intent')
            previews=[n for n in _nodes(command,ast.If) if ast.unparse(n.test)=='preview is not None']
            require(any(_returns(n) and any(isinstance(r.value,ast.Call) and ast.unparse(r.value.func)=='Result'
                        and len(r.value.args)>1 and isinstance(r.value.args[1],ast.Constant) and r.value.args[1].value=='preview'
                        for r in n.body if isinstance(r,ast.Return)) for n in previews))
            require(any(ast.unparse(n.test)=='proposal.ok and (not proposal.needs_confirm)' and _returns(n) for n in _nodes(run,ast.If)))
            guards=[n for n in _nodes(approve,ast.If) if ast.unparse(n.test)=="what != 'save' or not proposal.ok" and _returns(n)]
            executions=[n for n in _nodes(approve,ast.Call) if ast.unparse(n)=='self._begin_turn(proposal.command)']
            require(len(guards)==1 and len(executions)==1 and guards[0].lineno<executions[0].lineno)
            return ('Some valid read-only proposals run immediately; proposals needing confirmation wait for you. '
                    '`notebook_tools.command()` returns a preview before writing when confirmation is requested. '
                    'In the desktop, `_answer_intent()` stops unless you choose Save and the proposal is valid; '
                    'Edit or Cancel does not execute it. Explicit native log commands retain their direct-save behavior. '
                    'These source checks did not save an observation.')
        fallback=function('cursiv_engine/chat/routing.py','_fallback_chain')
        conversation=function('cursiv_engine/chat/conversation.py','_chat_inner')
        loops=[n for n in fallback.body if isinstance(n,ast.For) and '_call_groq_direct' in ast.unparse(n.iter)
               and '_call_gemini_direct' in ast.unparse(n.iter)]
        stops=[n for n in fallback.body if isinstance(n,ast.If) and ast.unparse(n.test)=='local_tried' and _returns(n)]
        require(len(loops)==len(stops)==1 and loops[0].lineno<stops[0].lineno)
        require(_has(loops[0],"runtime._saved_key(field) if runtime.netgate.allowed() else ''"))
        offline=[n for n in _nodes(conversation,ast.If) if ast.unparse(n.test)=='not runtime._is_online()']
        require(len(offline)==1 and any(_returns(n) and isinstance(n.test,ast.BoolOp) and isinstance(n.test.op,ast.Or)
            and any(isinstance(v,ast.Name) and v.id=='_local_tried' for v in n.test.values)
            and _has(n,'not runtime._local_model_ready()') and _has(n,'runtime._without_model()')
            for n in offline[0].body if isinstance(n,ast.If)))
        require(_has(fallback,'runtime.cloud_enabled() and (not runtime._local_model_ready())'))
        return ('In `_fallback_chain()`, the Groq/Gemini saved-key loop comes before the `local_tried` return. '
                'That flag prevents retrying an already attempted local model; it does not block the earlier free-provider loop. '
                'Online attempts still require the network gate and usable configuration; normal chat reports unavailability '
                'when offline after local failure. Cursiv Cloud has a separate enabled-and-no-local-model condition. '
                'Forced-provider commands and this local-only source explanation use separate paths; no provider was tested here.')
    except (OSError,ValueError,TypeError,KeyError,SyntaxError,UnicodeError) as exc:
        return ('The critical behavior explanation is unavailable because '+str(exc)+'. '
                'I will not replace a failed source check with a model guess. No operation was performed.')
