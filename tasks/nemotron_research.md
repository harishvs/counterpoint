# Nemotron 3 Nano Omni 30B-A3B — Research Findings

## CONFIRMED: Fully multimodal (video + audio + image + text)

The model supports all four input modalities we need. This is not text-only.

## Modality Details

| Modality | Formats | Limits |
|----------|---------|--------|
| Video | mp4 | **2 minutes max**; 1080p@1FPS/128 frames, 720p@2FPS/256 frames |
| Audio | wav, mp3 | Up to 1 hour; 8kHz+ sampling rate; **English speech only** |
| Image | JPEG, PNG (RGB) | 2D input |
| Text | String | 256k token context window |
| Output | Text only | JSON, chain-of-thought reasoning, tool calling, word-level timestamps |

## Critical Limitations for Our Use Case

1. **Video capped at 2 minutes** — bodycam videos are typically 5-60+ minutes. We'll need to segment videos into chunks and process them per-claim. This validates the claim-first pipeline design (retrieve relevant 2-min segments, then verify).

2. **Audio is English speech only** — "audio other than speech is out of scope." Gunshots, sirens, ambient noise won't be processed as meaningful audio. The model can transcribe speech and understand spoken words.

3. **Noisy audio may be limited** — "Performance on far-field microphone audio and noisy environments (SNR below 10 dB) may be limited." Bodycam audio is often noisy (wind, traffic, radio chatter).

4. **No PDF input** — pages must be rendered to PNG. Not an issue since we work with text reports.

## Architecture

- Mamba2-Transformer hybrid Mixture of Experts (MoE)
- 31B total parameters, ~3B active per token
- Components: Nemotron 3 Nano LLM backbone + C-RADIOv4-H vision encoder + Parakeet speech encoder

## Precision Variants

| Precision | Size | Notes |
|-----------|------|-------|
| BF16 | 61.5 GB | Full quality |
| FP8 | 32.8 GB | Within 1pt of BF16 on multimodal benchmarks |
| NVFP4 | 20.9 GB | Within 1pt of BF16; fits on single RTX 5090 or DGX Spark |

## DGX Spark Deployment

- Spark has ~128 GB unified LPDDR5X memory (shared CPU/GPU)
- NVFP4 variant at 20.9 GB fits easily
- Needs tuning: lower `--gpu-memory-utilization` and `--max-model-len` to avoid OOM
- Use vLLM 0.20.0 to serve

## Deployment: vLLM (Primary)

```bash
vllm serve nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-NVFP4 \
  --host 0.0.0.0 \
  --max-model-len 131072 \
  --tensor-parallel-size 1 \
  --trust-remote-code \
  --video-pruning-rate 0.5 \
  --media-io-kwargs '{"video": {"fps": 2, "num_frames": 256}}' \
  --reasoning-parser nemotron_v3 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --kv-cache-dtype fp8
```

Audio support: `pip install "vllm[audio]"`

## API Format: OpenAI-Compatible

Standard `/v1/chat/completions` endpoint. Video/audio sent as URL references:

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="")

response = client.chat.completions.create(
    model="nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-NVFP4",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Describe what happens in this video."},
            {"type": "video_url", "video_url": {"url": "file:///path/to/clip.mp4"}},
        ],
    }],
    max_tokens=1024,
    temperature=1.0,
    extra_body={"top_k": 1, "chat_template_kwargs": {"enable_thinking": False}},
)
```

Audio uses `"type": "audio_url"`, images use `"type": "image_url"`.

## License

NVIDIA Open Model Agreement — **commercial use allowed**.

## Impact on Pipeline Design

1. **Video segmentation is required.** The retrieve stage must cut relevant 2-min clips per claim before sending to the model. This is exactly what our claim-first pipeline does — the single-pass baseline will hit the 2-min limit on full videos.

2. **The OpenAI-compatible API means our adapter is simple.** Just swap the base_url and model name. The `openai` Python SDK works directly.

3. **Reasoning mode is valuable.** Chain-of-thought can explain why a claim conflicts with evidence, which maps directly to `evidence_observations` in our prediction schema.

4. **The 256k context window is generous.** Long transcripts fit easily.

## Nemotron Adapter Implementation Plan

```python
# pipeline/adapters/nemotron.py — updated design
from openai import OpenAI

class NemotronAdapter(ModelAdapter):
    def __init__(self, endpoint="http://localhost:8000/v1"):
        self._client = OpenAI(base_url=endpoint, api_key="not-needed")
        self._model = "nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-NVFP4"
    
    def complete(self, prompt, media=None):
        content = [{"type": "text", "text": prompt}]
        for path in (media or []):
            if path.suffix == ".mp4":
                content.append({"type": "video_url", "video_url": {"url": f"file://{path}"}})
            elif path.suffix in (".wav", ".mp3"):
                content.append({"type": "audio_url", "audio_url": {"url": f"file://{path}"}})
            elif path.suffix in (".jpg", ".jpeg", ".png"):
                # base64 encode
                ...
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": content}],
            max_tokens=4096,
            extra_body={"top_k": 1, "chat_template_kwargs": {"enable_thinking": False}},
        )
        return response.choices[0].message.content
```
