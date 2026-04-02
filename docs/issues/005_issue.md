# [FEATURE] Human-on-the-Loop の実装

## 概要

グラフに LangGraph の `interrupt()` を活用した中断ポイントを追加し、特定の条件下でエージェントが人間の確認を求めて処理を一時停止できるようにする。

## 背景

エージェンティックマニュフェストの行動指針「人間は介入者ではなく監督者として関与する（Human-on-the-Loop：必要時のみ介入する監視型の関与）」に基づく。

現在のグラフは完全自律で動作し、処理結果に問題があっても人間が介入できる仕組みがない。エージェントの自律性を高める一方で、重要な判断ポイントでは人間がレビューできる設計が求められる。

Human-in-the-Loop（毎回確認）ではなく Human-on-the-Loop（条件設定した上で必要時のみ確認）として実装することで、利便性とガバナンスを両立させる。

## 要件

- `fit_score` が一定閾値（例：40）を大幅に下回る場合、またはエラーが発生した場合に処理を中断し、人間の確認を求めること
- 中断時は LangGraph の `interrupt()` を使い、中断理由・現在の生成結果・スコアを含むペイロードを返すこと
- `POST /reply` に対して中断状態のレスポンス（`status: interrupted`、確認用情報を含む）を返すこと
- 中断後に人間が `approved` または `rejected` を通知する API エンドポイント（例：`POST /reply/{thread_id}/resume`）を追加すること
- `rejected` の場合はエージェントが再生成を試みること

## 受け入れ条件

- `fit_score` が閾値を大幅に下回るとき、グラフが中断されて `status: interrupted` が返ること
- `POST /reply/{thread_id}/resume` に `approved: true` を送ると処理が再開されること
- `POST /reply/{thread_id}/resume` に `approved: false` を送るとエージェントが再生成を試みること
- 通常ケース（`fit_score` ≥ 閾値）では中断なしで自律完了すること

## 補足

- 対象ファイル:
  - `src/app/agent/core/graph/build_graph.py`（`interrupt()` の追加、checkpointer の設定）
  - `src/app/agent/entrypoint.py`（`/reply/{thread_id}/resume` エンドポイント追加）
- LangGraph の `interrupt()` は checkpointer（`MemorySaver` または `SqliteSaver`）が必要
- 002_issue（`fit_score` ループ）・004_issue（ガードレール設計）の実装後に着手することを推奨
- Human-on-the-Loop の介入条件は 004_issue で定義する「人間介入ルール」と連動させること
