from typing import Literal

from pydantic import BaseModel, Field

from app.agent.core.schemas.base_output_schema import BaseOutputSchema


class ClassifiedConversationTerm(BaseModel):
    expression: str = Field(description="会話中で使われた語または短いフレーズ")
    normalized_expression: str = Field(
        description="意味の重複判定に使う代表表現。表現違いでも同義なら同じ値に寄せる"
    )
    speaker: Literal["self", "other", "both"] = Field(
        description="この表現を使った話者。両者が使っている場合は both"
    )
    occurrence_count: int = Field(
        ge=1,
        description="会話履歴全体で同系統の表現が出現した回数",
    )
    source_quotes: list[str] = Field(
        default_factory=list,
        description="根拠となる発話引用。最大3件程度に絞る",
    )


class ConversationWordClassification(BaseModel):
    topic_terms: list[ClassifiedConversationTerm] = Field(
        default_factory=list,
        description="会話の対象そのものを表す Topic 語の一覧",
    )
    reaction_terms: list[ClassifiedConversationTerm] = Field(
        default_factory=list,
        description="感情・評価・反応を表す Reaction 語の一覧",
    )
    function_terms: list[ClassifiedConversationTerm] = Field(
        default_factory=list,
        description="会話の進行・構造を担う Function 語の一覧",
    )


class FinalReplyRewriteStructuredOutputSchema(BaseModel):
    rewritten_reply: str = Field(description="繰り返し感を抑えるように言いかえた最終返信")
    reasoning: str = Field(description="どの重複を避け、どう自然さを上げたかの説明")
    detected_repetition_risks: list[str] = Field(
        default_factory=list,
        description="会話履歴や元返信に見られた重複リスクの一覧",
    )
    word_classification: ConversationWordClassification = Field(
        default_factory=ConversationWordClassification,
        description="過去の会話履歴から作成した分類表",
    )


class FinalReplyRewriteOutputSchema(BaseOutputSchema):
    rewritten_reply: str = Field(description="最終的に採用する返信文")
    detected_repetition_risks: list[str] = Field(
        default_factory=list,
        description="検出した重複リスク",
    )
    word_classification: ConversationWordClassification = Field(
        default_factory=ConversationWordClassification,
        description="過去会話から作成した分類表",
    )