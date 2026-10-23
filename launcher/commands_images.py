"""Images commands.

handle(runtime, text, cmd, cfg, history) returns a command result,
an intentional None (defer to chat), or UNHANDLED. Called in the
original precedence order by command_dispatch; no widgets are loaded.
"""
from __future__ import annotations

from command_runtime import CommandRuntime, UNHANDLED


def handle(runtime: CommandRuntime, text: str, cmd: str, cfg: dict, history: list[dict]):
    img_prompt = runtime._image_request_prompt(text)
    if img_prompt is not None:
        prompt = img_prompt
        if not prompt:
            return runtime.TextResult("Usage: image <description>")
        from cursiv_engine.ui.chat_app import _saved_key
        oai_key = cfg.get("openai_key", "")
        cf_id = cfg.get("cf_account_id", "") or _saved_key("cf_account_id")
        cf_tok = cfg.get("cf_api_token", "") or _saved_key("cf_api_token")
        if not oai_key and not (cf_id and cf_tok):
            return runtime.TextResult(runtime.IMAGE_GEN_NEEDS_KEY)
        from cursiv_engine.core import atomic
        import uuid
        img_dir = runtime._image_folder(cfg)
        stamp = runtime.datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:8]
        img_path = img_dir / f"image_{stamp}.png"
        revised, used_model, errors = prompt, "", []
        if oai_key:
            import base64 as _img_b64
            import urllib.request as _img_req
            try:
                import openai as _oai_img
                img_client = _oai_img.OpenAI(api_key=oai_key)
                for model in runtime.IMAGE_GEN_MODELS:
                    try:
                        resp = img_client.images.generate(model=model, prompt=prompt, size="1024x1024", n=1)
                    except Exception as e:
                        errors.append(f"{model}: {e}")
                        continue
                    item = resp.data[0]
                    if getattr(item, "b64_json", None):
                        atomic.write_bytes(img_path, _img_b64.b64decode(item.b64_json))
                    else:
                        _img_req.urlretrieve(item.url, str(img_path))
                        received = img_path.read_bytes()
                        if not received:
                            raise OSError('Image download was empty')
                        atomic.write_bytes(img_path, received)
                    revised = getattr(item, "revised_prompt", None) or prompt
                    used_model = model
                    break
            except Exception as e:
                errors.append(f"OpenAI: {e}")
        if not used_model and cf_id and cf_tok:
            try:
                img_path = img_dir / f"image_{stamp}.jpg"
                atomic.write_bytes(img_path, runtime._cloudflare_image(prompt, cf_id, cf_tok))
                used_model = "FLUX.1-schnell (Cloudflare, free)"
            except Exception as e:
                errors.append(str(e))
        if not used_model:
            return runtime.TextResult("Image generation failed:\n" + "\n".join(errors[-3:]))
        if runtime._STRAND_OK:
            runtime._strand_save(f"image: {prompt[:200]}", f"Generated: {img_path}\nRevised prompt: {revised[:300]}",
                         tags=["image", used_model], score=0.70, territory_tag="creative", source="image", model=used_model)
        note = f"\n\nThe model revised the prompt to:\n{revised[:300]}" if revised != prompt else ""
        return runtime.TextResult(f"Image generated with {used_model}  ({img_path.name}){note}", image_path=str(img_path))
    return UNHANDLED
