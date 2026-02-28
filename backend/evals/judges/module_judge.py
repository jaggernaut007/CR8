"""Judge for learning module evaluation."""

from __future__ import annotations

import json

from backend.evals.datasets.schema import CriterionScore
from backend.evals.judges.base_judge import BaseJudge
from backend.evals.judges.rubrics import MODULE_RUBRIC


class ModuleJudge(BaseJudge):

    def evaluate(
        self,
        module_md: str,
        topic_name: str,
        curriculum_scope: str,
        gap_summary: dict,
    ) -> list[CriterionScore]:
        prompt = MODULE_RUBRIC.format(
            output=module_md,
            topic_name=topic_name,
            curriculum_scope=curriculum_scope,
            gap_summary=json.dumps(gap_summary, indent=2),
        )
        return self.score(prompt)
