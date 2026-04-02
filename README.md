# 💬 Dating Conversation Agent

**― マッチングアプリの会話を最適化するエージェント ―**

---

## 🟦 Overview

本プロジェクトは、マッチングアプリにおける
**初回デート成立までの会話を最適化するエージェントシステム**である。

従来の「返信を考える」という認知負荷の高い作業を支援し、
会話の継続率およびデート成立率の向上を目的とする。

また、本システムは単なるAIツールではなく、
**エージェントの振る舞いを継続的に改善する（Agentic）システム**として設計されている。

---

## 🟦 Application

### ■ Purpose

ユーザーはマッチングアプリにおいて以下の課題を抱えている：

* 何を返信すべきか分からない
* 会話が続かない
* デートに誘うタイミングが分からない

本システムはこれらの課題に対し、

* 会話文脈の理解
* 会話フェーズの推定
* 複数の返信候補生成
* 次のアクションの提案

を行うことで、

👉 **「会話の最適化」と「意思決定の支援」** を提供する。

---

### ■ Value Proposition

#### 1. 認知負荷の低減

返信内容を毎回考える必要をなくし、意思決定コストを削減する。

#### 2. 会話品質の向上

文脈・温度感・フェーズを考慮した返信により、会話継続率を向上させる。

#### 3. 成果への寄与

最終的なKPIである「初回デート成立率」の向上を目指す。

---

### ■ Target Users

* マッチングアプリ利用者
* 会話に苦手意識を持つユーザー
* 効率的に出会いを進めたいユーザー

---

### ■ KPI (Success Metrics)

本システムは以下の指標で評価される：

* 返信率
* 会話継続率
* 質問返し率
* デート打診成功率

---

## 🟦 System Design

### ■ Architecture

```text
Chrome Extension（UI / DOM操作）
        ↓
Local Agent Server（FastAPI）
        ↓
LLM / Logging DB / Evaluation Engine
```

---

### ■ Design Philosophy

本システムは、従来の決定的なロジックではなく、
**エージェントの振る舞い（Behavior）を中心に設計される。**

* 固定ロジックではなく、文脈に応じた振る舞い
* Pass/Failではなく、多軸評価
* 出力ではなく、意思決定過程の観測

---

### ■ Agent Behavior Flow

エージェントは以下のプロセスで動作する：

1. 会話履歴の取得
2. 会話状態の推定（フェーズ・温度感）
3. 次のアクションの目的設定
4. 複数の返信候補生成
5. リスク評価（距離の詰めすぎ等）

👉 **重要なのは「何を出すか」ではなく「どう考えて出したか」**

---

### ■ Behavior Tracing（意思決定の可視化）

各生成に対して以下をログとして保存する：

```json
{
  "phase": "rapport_building",
  "intent": "共通点の拡張",
  "strategy": "質問 + 共感",
  "candidates": ["...", "...", "..."],
  "risk": "距離を詰めすぎる可能性あり",
  "selected": 1
}
```

これにより以下を追跡可能とする：

* Agent reasoning（思考プロセス）
* Decision（選択）
* Action（実行）

---

### ■ Evaluation Design

本システムは、Pass/Failではなく
**多軸評価によるスコアリング**を採用する。

#### External Metrics（外部評価）

* 返信成功率
* 会話継続率
* デート成立率

#### Internal Metrics（内部評価）

* 候補採用率
* 手修正率
* 再生成率
* 応答速度

---

### ■ ADLC（Agentic Development Loop）

本システムは以下のループで継続的に改善される：

```text
Generate
  ↓
Log
  ↓
Evaluate
  ↓
Tune（Prompt / Strategy）
  ↓
Re-Generate
```

👉 **「完成するシステム」ではなく「成長するシステム」**

---

### ■ Human-in-the-Loop

本システムは完全自律ではなく、
**Human-in-the-Loop（監督型）**を採用する。

* ユーザーが最終送信を行う
* エージェントは意思決定を支援する

これにより：

* 安全性の確保
* 実運用データの取得
* 段階的な自律性の向上

を実現する。

---

## 🧠 Concept

本プロジェクトは、

👉 **「エージェントを作る」のではなく「エージェントを育てる」**

という思想に基づいている。

システムは完成するものではなく、
**運用を通じて価値が向上し続ける資産**として設計されている。

---

## 📌 Notes

* 本システムは自動送信を行わない（規約・倫理配慮）
* Chrome Extension による半自動支援を採用
* ローカル環境で動作可能

---

## 🧪 Standalone Tool Evaluation

`generate_reply` ツールを単体で実行し、ケースごとに簡易スコアを出力できます。

### 1. ケース定義

評価ケースは以下にあります。

* `eval/generate_reply_cases.yaml`

`user_id` に対応する `data/test_user/{user_id}.yaml` を読み込み、
生成された返信に対して以下を評価します。

* 最低文字数
* 必須キーワード（any / all）
* 禁止キーワード

### 2. 実行コマンド

```bash
uv run python scripts/eval_generate_reply.py
```

### 3. 出力

実行ごとにタイムスタンプ付きディレクトリが作成されます。

* `eval/results/{timestamp}/summary.json`
* `eval/results/{timestamp}/results.json`
* `eval/results/{timestamp}/results.csv`

### 4. オプション

```bash
uv run python scripts/eval_generate_reply.py \
  --cases eval/generate_reply_cases.yaml \
  --data-dir data/test_user \
  --output-dir eval/results
```

---

## 🧪 Standalone Tool Evaluation (score_reply_quality)

`score_reply_quality` ツールを単体で実行し、生成済み返信の品質判定をケースごとに評価できます。

### 1. ケース定義

評価ケースは以下にあります。

* `eval/score_reply_quality_cases.yaml`

`user_id` に対応する `data/test_user/{user_id}.yaml` を読み込み、
`generated_reply` を評価対象として `score_reply_quality` に渡します。

### 2. 実行コマンド

```bash
uv run python scripts/eval_score_reply_quality.py
```

### 3. 出力

実行ごとにタイムスタンプ付きディレクトリが作成されます。

* `eval/results/{timestamp}/summary.json`
* `eval/results/{timestamp}/results.json`
* `eval/results/{timestamp}/results.csv`

### 4. オプション

```bash
uv run python scripts/eval_score_reply_quality.py --cases eval/score_reply_quality_cases.yaml --data-dir data/test_user --output-dir eval/results
```

