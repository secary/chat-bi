from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class Metric:
    name: str
    code: str
    table: str
    formula: str
    caliber: str


@dataclass(frozen=True)
class Dimension:
    name: str
    field: str
    table: str
    expression: str


FilterCondition = Tuple[str, str, str]
TimeFilter = Tuple[str, str]


@dataclass
class SemanticPlan:
    question: str
    metric: Metric
    dimensions: List[Dimension]
    filters: List[FilterCondition]
    time_filter: Optional[TimeFilter]
    order_by_metric_desc: bool
    limit: Optional[int]
    sql: str
