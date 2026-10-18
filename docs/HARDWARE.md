# Hardware check

Measured 2026-10-18 with `scripts/hardware_check.py`: one fixed prompt (about 120 words out), second run reported (model already loaded). Load time is from cold.

## This computer

- Processor: 12th Gen Intel(R) Core(TM) i5-12450HX (12 threads)
- Memory: 32 GB
- Graphics: NVIDIA GeForce RTX 2050, Intel(R) UHD Graphics (4096 MB)
- System: Windows-11-10.0.26200-SP0

## Results

| Model | Running on | Load (cold) | Reading the prompt | Writing the answer | Whole answer |
|---|---|---|---|---|---|
| qwen3:4b-instruct | graphics card (as Cursiv sets it) | 7.1 s | 1320 tokens/s | 37.0 tokens/s | 3.7 s |
| qwen3:4b-instruct | processor only (no graphics card) | 4.6 s | 358 tokens/s | 10.1 tokens/s | 13.4 s |
| qwen2.5:1.5b | graphics card (as Cursiv sets it) | 5.7 s | 3990 tokens/s | 86.0 tokens/s | 2.6 s |
| qwen2.5:1.5b | processor only (no graphics card) | 2.3 s | 1500 tokens/s | 26.8 tokens/s | 8.3 s |

A token is about three quarters of a word. 'Processor only' is what a laptop without a usable graphics card gets; Cursiv falls back to it automatically.
