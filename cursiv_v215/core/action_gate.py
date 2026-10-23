"""Pure pre-dispatch refusal. No backend, source lookup, planner or model call."""
from __future__ import annotations

import re
from . import turn_policy


def refusal(text: str, history=()) -> str | None:
    policy = turn_policy.effective(text)
    if policy == turn_policy.Policy():
        return None
    from . import notebook_tools, file_access
    task = turn_policy.task_text(text)
    if re.match(r'(?i)^(?:how\b|what happens\b|where (?:do|does)\b|does cursiv\b)', task):
        return None  # workflow guidance is not a request to execute the workflow
    blocked = notebook_tools.blocked_message(text, list(history))
    if blocked:
        return blocked
    if file_access.is_request(task, list(history)):
        parsed = file_access._parse(task, list(history))
        operation = {'read': 'read_file', 'list': 'list_directory', 'verify': 'read_file'}.get(
            parsed[0] if parsed else '', 'write_file')
        if policy.blocks(operation):
            return turn_policy.DENIED
    from cursiv_v215.memory.intents import requested_operations
    operations = requested_operations(task)
    if any(policy.blocks(op) for op in operations):
        return 'Memory operation blocked this turn. No action was executed.'
    # Command families and unresolved imperative variants must not escape to
    # a model merely because their ordinary parser needs more arguments.
    t = re.sub(r'(?i)^(?:please\s+|(?:can|could|would) you\s+)', '', task)
    token = re.match(r'[A-Za-z_]+', t)
    names = {name.casefold(): name for name in turn_policy.READS | turn_policy.WRITES}
    names['file_create'] = 'create_file'
    operation = names.get(token[0].casefold()) if token else None
    if operation and policy.blocks(operation):
        return turn_policy.DENIED
    mutation = re.match(r'(?i)^(?:create|write|append|replace|delete|remove|edit|correct|amend|'
                        r'save|store|remember|record|add|import|export|share|install|execute|run)\b', t)
    command = re.match(r'(?i)^(?:field\s*(?:log|notebook)\s+(?:import|export|share)|'
                       r'demo(?:\s+(?:on|off))?$|(?:files|offline)\s+(?:on|off)$|workspace\s+\S)', t)
    lookup = re.match(r'(?i)^(?:read|list|search|browse|inspect|scan|open|retrieve|recall|'
                      r'look up|fetch|pull up|verify|check)\b', t)
    if ((not policy.change and (mutation or command)) or (not policy.inspect and lookup)):
        return turn_policy.DENIED
    return None
