from typing import Literal

from pydantic import Field

from app.agent.core.schemas.base_output_schema import BaseOutputSchema
from app.agent.core.nodes.action.tool_enum import ToolEnum


# ToolEnumのメンバーの名前をLiteral型として取得
TOOL_NAMES = tuple(tool.name for tool in ToolEnum)
DecidedActionLiteral = Literal[*TOOL_NAMES]


class DecisionOutputSchema(BaseOutputSchema):
    current_thought: str = Field(
        ...,
        description=(
            "現在の会話状況に対する解釈・状況理解。"
            "相手の興味、会話フェーズ、次に意識すべきことなどを簡潔にまとめる。"
        ),
    )

    required_tasks: list[str] = Field(
        default_factory=list,
        description=(
            "現在の状況に対して必要だと考えられるタスク一覧。"
            "今すぐ実行しない候補も含めて広めに洗い出す。"
        ),
    )

    decided_action: DecidedActionLiteral = Field(
        ...,
        description=(
            "required_tasks の中から、今回このステップで実際に実行すると判断したタスク。"
            f"利用可能なツール: {', '.join(TOOL_NAMES)}"
        ),
    )