# Script Parser

Parses video scripts with `[SLIDE N]` markers into structured segments for Kokoro TTS.

## Module

::: backend.services.script_parser

## Overview

The script parser converts raw video script text (output from Agent 3) into per-slide segments that can be individually synthesised by the TTS engine.

### Key Functions

- `parse_script(script_text, num_slides)` — parses `[SLIDE N]` markers; falls back to `distribute_script()` if no markers found
- `distribute_script(text, num_slides)` — distributes unmarked text proportionally across slides by paragraph character count

## Input Format

```text
[SLIDE 1: Introduction]
Welcome to this module on machine learning fundamentals.

[SLIDE 2: Key Concepts]
Today we'll cover supervised and unsupervised learning.
```

## Output Format

```python
[
    {"slide_num": 1, "text": "Welcome to this module..."},
    {"slide_num": 2, "text": "Today we'll cover..."},
]
```
