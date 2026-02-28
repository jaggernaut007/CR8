"""Judge for PPT slide structure evaluation."""

from __future__ import annotations

import json

from backend.evals.datasets.schema import CriterionScore
from backend.evals.judges.base_judge import BaseJudge
from backend.evals.judges.rubrics import PPT_RUBRIC


class PPTJudge(BaseJudge):

    def evaluate(
        self,
        ppt_json: str | dict,
        topic_name: str,
        curriculum_scope: str,
        gap_summary: dict,
    ) -> list[CriterionScore]:
        output = ppt_json if isinstance(ppt_json, str) else json.dumps(ppt_json, indent=2)
        prompt = PPT_RUBRIC.format(
            output=output,
            topic_name=topic_name,
            curriculum_scope=curriculum_scope,
            gap_summary=json.dumps(gap_summary, indent=2),
        )
        return self.score(prompt)
