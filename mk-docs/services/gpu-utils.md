# GPU Utils

Central hardware detection for PyTorch devices and ffmpeg video encoders.

## Module

::: backend.services.gpu_utils

## Overview

Provides two detection functions used by the TTS engine and video builder to automatically select the best available hardware.

### `get_torch_device(preference="auto")`

Returns the best PyTorch device string:

| Priority | Device | When |
|----------|--------|------|
| 1 | `cuda` | NVIDIA GPU with CUDA support |
| 2 | `mps` | Apple Silicon (M1/M2/M3) |
| 3 | `cpu` | Always available fallback |

Pass `preference="cpu"` to force CPU even when GPU is available.

### `get_ffmpeg_encoder()`

Probes `ffmpeg -encoders` and runs a test encode to find the best H.264 encoder:

| Priority | Encoder | Platform |
|----------|---------|----------|
| 1 | `h264_videotoolbox` | macOS (Apple Silicon / Intel) |
| 2 | `h264_nvenc` | NVIDIA GPU |
| 3 | `h264_qsv` | Intel Quick Sync |
| 4 | `h264_amf` | AMD |
| 5 | `libx264` | Software fallback (always available) |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `VIDEO_DEVICE` | `auto` | Controls device selection: `auto`, `cpu`, `mps`, `cuda` |
