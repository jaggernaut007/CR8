"""Judge for cross-output consistency evaluation."""

from __future__ import annotations

import json

from backend.evals.datasets.schema import CriterionScore
from backend.evals.judges.base_judge import BaseJudge
from backend.evals.judges.rubrics import CONSISTENCY_RUBRIC


class ConsistencyJudge(BaseJudge):

    def evaluate(
        self,
        module_md: str,
        ppt_json: str | dict,
        script: str,
        topic_name: str,
        gap_summary: dict,
    ) -> list[CriterionScore]:
        ppt_output = ppt_json if isinstance(ppt_json, str) else json.dumps(ppt_json, indent=2)
        prompt = CONSISTENCY_RUBRIC.format(
            topic_name=topic_name,
            gap_summary=json.dumps(gap_summary, indent=2),
            module_output=module_md,
            ppt_output=ppt_output,
            script_output=script,
        )
        return self.score(prompt)
