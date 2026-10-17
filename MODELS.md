# AI models and their licenses

Cursiv's own code is MIT-licensed. The AI models it downloads through Ollama
each have their own license. This is a plain summary, not legal advice: read
the license on each model's page before relying on it, especially before
selling anything that includes a model.

| Model (Ollama tag) | Used for | License | Selling or giving away |
|---|---|---|---|
| `qwen3:4b-instruct` | Chat (default on 4–6 GB cards) | Apache 2.0 | Allowed. Include the license. |
| `qwen3:4b`, `qwen3:8b` | Not recommended: they think out loud first (slow) | Apache 2.0 | Allowed. Include the license. |
| `qwen2.5:1.5b` | Chat (smallest) | Apache 2.0 | Allowed. Include the license. |
| `nomic-embed-text` | Memory search | Apache 2.0 | Allowed. Include the license. |
| `qwen2.5-coder:7b`, `:14b` | Coding help | Apache 2.0 | Allowed. Include the license. |
| `llama3.1`, `llama3.2:3b` | Chat | Llama 3.1 / 3.2 Community License | Allowed under the license's terms: include it and show "Built with Llama". |
| `gemma3:4b` | Reading images | Gemma Terms of Use | Allowed under Google's terms, which you must pass on, including its prohibited-use policy. |
| `deepseek-coder-v2:16b` | Coding review | DeepSeek License | Allows commercial use with use restrictions you must pass on. |
| `qwen2.5:3b`, `qwen2.5-coder:3b` | No longer offered | **Qwen Research License: research or evaluation only** | **Not allowed for commercial use.** Cursiv uses it only if nothing else is installed. |

Up to v3.14-U60, Cursiv's default model for 4–6 GB graphics cards was
`qwen2.5:3b`. From U61 it's `qwen3:4b-instruct` (llama3.1 on 8 GB+ cards), and
Cursiv USB drives include `qwen3:4b-instruct` (or `qwen2.5:1.5b`) instead. If you
have `qwen2.5:3b`, download qwen3 4B in Setup and remove the old one with
`ollama rm qwen2.5:3b`.

Ollama itself is MIT-licensed.

Sources: each model's page on ollama.com and huggingface.co (for example
huggingface.co/Qwen/Qwen2.5-3B-Instruct, huggingface.co/Qwen/Qwen3-4B-Instruct-2507).
