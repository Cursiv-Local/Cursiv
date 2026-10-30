"""Images commands.

handle(runtime, text, cmd, cfg, history) returns a command result,
an intentional None (defer to chat), or UNHANDLED. Called in the
original precedence order by command_dispatch; no widgets are loaded.
"""
from __future__ import annotations

from cursiv_engine.core.command_api import CommandRuntime, UNHANDLED


def save_result(runtime, result, cfg):
    """Verified native cache write, stable across Retry; never writes notebooks."""
    from cursiv_engine.chat.activity import check_guard
    check_guard()
    import base64
    from cursiv_engine.core import atomic,private_store
    artifact=result.artifacts[0]
    data=base64.b64decode(artifact['base64'],validate=True)
    filename='generated_'+artifact['sha256']+'.png'
    target=runtime._image_folder(cfg)/filename
    if target.is_symlink() or (hasattr(target,'is_junction') and target.is_junction()):
        raise PermissionError('Linked image output is not allowed')
    if target.exists():
        if private_store.read_bytes(target) != data:
            raise OSError('Existing image cache differs; refusing overwrite')
    else:
        atomic.write_bytes(target,data)
    if private_store.read_bytes(target) != data:
        raise OSError('Image cache read-back failed')
    return str(target)


def handle(runtime: CommandRuntime, text: str, cmd: str, cfg: dict, history: list[dict]):
    img_prompt = runtime._image_request_prompt(text)
    if img_prompt is not None:
        prompt = img_prompt
        if not prompt:
            return runtime.TextResult("Usage: image <description>")
        from cursiv_engine.chat import provider_manager as manager
        cfg=dict(cfg)
        from cursiv_engine.core import turn_policy
        if not turn_policy.current().change:
            return runtime.TextResult('Image creation is disabled for this restricted turn.')
        list(manager.selected_infer([dict(role='user',content=prompt)],cfg=cfg,capability='image_generation'))
        result=manager.outcome()
        if result.error:
            return runtime.TextResult(result.error_message)
        path=save_result(runtime,result,cfg)
        return runtime.TextResult(result.text,image_path=path)
    return UNHANDLED
