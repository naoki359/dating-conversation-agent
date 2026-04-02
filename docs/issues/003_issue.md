# [FEATURE] LLMによる明示的な終了信号の実装

## 概要

現在のループ終了条件が `action_loop_count >= 4` のカウンタ上限のみとなっている。エージェント自身が「目標を達成した」と判断して終了するシグナルを `DecisionNode` の出力に追加し、不要なループを排除する。

## 背景

エージェンティックマニュフェストの行動指針「行動の経済性（Economy of Action）――最小限の計算負荷と認知負荷で最大の目標を達成すること――は、スケーラブルな自律性に不可欠である」に基づく。

現状では、`GENERATE_REPLY` が1回目で十分な返信を生成できた場合でも、`action_loop_count` が4に達するまで無駄なLLM呼び出しが発生する可能性がある。目標達成の判断をLLM自身に委ねることで、計算コストと応答時間を削減できる。

## 要件

- `DecisionNode` の出力スキーマ（`DecisionOutputSchema`）に `is_done: bool` フィールドを追加すること
- `is_done=True` のとき、グラフが `END` に遷移する条件分岐を追加すること
- `DecisionNode` のプロンプトに、目標達成の判断基準（返信文が生成・検証済みであること）を明示すること
- `is_done` の判断理由を `action_reasoning` または専用フィールドでログに残すこと

## 受け入れ条件

- `GENERATE_REPLY` と `CHECK_REPLY_PROFILE_FIT` が正常完了し、`fit_score` が閾値以上の場合、`DecisionNode` が `is_done=True` を返してループを終了すること
- `is_done=True` のとき4回未満でもグラフが `END` へ遷移すること
- `is_done=False` のとき、従来通り `ActionNode` へ進むこと

## 補足

- 対象ファイル:
  - `src/app/agent/core/nodes/decision/schema.py`（`is_done` フィールド追加）
  - `src/app/agent/core/nodes/decision/node.py`（プロンプト修正）
  - `src/app/agent/core/graph/build_graph.py`（条件分岐の修正）
- 002_issue（`fit_score` ループ）の実装後に着手することを推奨
- カウンタ上限（`action_loop_count >= 4`）はフォールバックとして残すこと
