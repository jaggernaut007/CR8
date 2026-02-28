"""Base judge using DeepSeek-V3 via OpenAI-compatible API."""

from __future__ import annotations

import json

from openai import OpenAI

from backend.evals.config import eval_settings
from backend.evals.datasets.schema import CriterionScore


class BaseJudge:
    """LLM-as-judge using DeepSeek-V3 (cross-family evaluation of GPT outputs)."""

    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
    ):
        self.model = model or eval_settings.judge_model
        self.temperature = temperature if temperature is not None else eval_settings.judge_temperature
        self.client = OpenAI(
            api_key=eval_settings.deepseek_api_key,
            base_url=eval_settings.deepseek_base_url,
        )

    def score(self, prompt: str) -> list[CriterionScore]:
        """Send a rubric prompt to the judge and parse scored criteria."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=eval_settings.judge_max_tokens,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        return self._parse_scores(raw)

    def _parse_scores(self, raw_json: str) -> list[CriterionScore]:
        """Parse judge JSON response into CriterionScore objects."""
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            return [CriterionScore(
                criterion_name="PARSE_ERROR",
                score=1,
                weight=1.0,
                rationale=f"Failed to parse judge response: {raw_json[:200]}",
            )]

        scores = []
        for entry in data.get("scores", []):
            scores.append(CriterionScore(
                criterion_name=entry.get("criterion", "UNKNOWN"),
                score=max(1, min(5, int(entry.get("score", 1)))),
                weight=float(entry.get("weight", 0.0)),
                rationale=entry.get("rationale", ""),
            ))
        return scores
