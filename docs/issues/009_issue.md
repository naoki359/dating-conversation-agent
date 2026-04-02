## 概要

`CheckReplyProfileFitTool` の実行結果を `shared_canvas` に保持する。

## 背景

現在、`CheckReplyProfileFitTool.execute()` はプロフィール適合度の評価結果（`fit_score`、`reasons`、`improvement_suggestions`）を `BaseToolResult` として返すが、その結果が `shared_canvas` に書き込まれていない。

`shared_canvas` の `Canvas` TypedDict にはコメントアウト状態の `reply_check_result: dict[str, Any]` フィールドが存在しており、当初から結果を保持する設計が意図されていたことが伺える。結果を `shared_canvas` に保持しないと、後続ノードやツールがチェック結果を参照できず、ワークフロー全体での活用が困難となる。

## 要件

1. `Canvas` TypedDict に `reply_check_result: dict[str, Any]` フィールドを有効化（コメントアウトを解除）する。
2. `CheckReplyProfileFitTool.execute()` の成功時に、評価結果 (`result.model_dump()`) を `shared_canvas["reply_check_result"]` に書き込む。
3. 既存の `BaseToolResult` の返却仕様は変更しない。

## 受け入れ条件

- `CheckReplyProfileFitTool.execute()` が成功した場合、`shared_canvas["reply_check_result"]` に `fit_score`・`reasons`・`improvement_suggestions` を含む辞書が保存されること。
- `CheckReplyProfileFitTool.execute()` が失敗した場合（プロフィール未取得・返信文なし・例外）、`shared_canvas["reply_check_result"]` は更新されないこと。
- `Canvas` TypedDict の `reply_check_result` フィールドが正式に定義されており、型ヒントとして `dict[str, Any]` が付与されていること。

## 補足

- `shared_canvas` はプロセス内で更新される成果物を管理するグローバルオブジェクト（`src/app/agent/core/utils/shared_store.py`）。
- 評価スキーマは `CheckReplyProfileFitResultSchema`（`fit_score: int`、`reasons: list[str]`、`improvement_suggestions: list[str]`）。
- `Any` 型のインポートが未使用の場合、`Canvas` 側で `from typing import Any` を追加すること。
