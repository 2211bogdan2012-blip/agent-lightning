# ChartQA Example
[![chartqa workflow status](https://github.com/microsoft/agent-lightning/actions/workflows/badge-chartqa.yml/badge.svg)](https://github.com/microsoft/agent-lightning/actions/workflows/examples-chartqa.yml)

This example demonstrates training a visual reasoning agent on the ChartQA dataset using Agent-Lightning with the VERL algorithm. The agent uses a two-step pipeline to answer questions about charts:

1. **Extract** [model + image]: Read all relevant values from the chart
2. **Compute** [model text-only]: Calculate the final answer from extracted data

## Requirements

- Single node with 2 GPUs (40GB each recommended)

Install dependencies with:

```bash
uv sync --frozen \
    --group dev \
    --group experiment \
    --group image \
    --group langchain \
    --group vllm-0-10-2 \
    --group torch-gpu-stable
```

**Currently vLLM 0.10.2 is the only tested version. You might see issues like `cu_seqlens_q must be on CUDA` or flash-attn installation failures if you use other versions.** (See https://github.com/vllm-project/vllm/issues/27340)

## Dataset

Download the ChartQA dataset and prepare it for training:

```bash
cd examples/chartqa
python prepare_data.py
```

This downloads the ChartQA dataset from HuggingFace (`HuggingFaceM4/ChartQA`), saves images locally, and creates parquet files for training/testing. No HuggingFace token is required (public dataset).

**Dataset Statistics:**

- Training: ~18,000 chart question-answer pairs
- Test: ~2,500 pairs
- Chart types: Bar, line, pie, scatter, etc.

## Files

| File | Description |
|------|-------------|
| `chartqa_agent.py` | Two-step agent (extract → compute) |
| `prompts.py` | Prompt templates for extract and compute steps |
| `train_chartqa_agent.py` | Training script for Qwen2.5-VL-3B |
| `dev_chartqa_agent.py` | Development/debug script for quick smoke testing |
| `prepare_data.py` | Script to download and prepare the dataset |
| `multimodal_utils.py` | Image encoding utilities |
| `env_var.py` | Environment configuration |

## Training

**Step 1: Start the external store server** (in a separate terminal):
```bash
agl store --port 4747
```

**Step 2: Run training** (2 GPUs):
```bash
AGL_MANAGED_STORE=0 python train_chartqa_agent.py qwen --n-runners 32 --external-store-address http://localhost:4747
```

### Development/Debug Mode

For quick smoke testing during development:

```bash
AGL_MANAGED_STORE=0 python dev_chartqa_agent.py --n-runners 32 --external-store-address http://localhost:4747
```


