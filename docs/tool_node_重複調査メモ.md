# tool と node の重複調査メモ

## 目的

- `src/app/agent/core/tools` と `src/app/agent/core/nodes` にまたがって存在する類似処理を洗い出す
- `util` に切り出しやすい候補を優先度付きで整理する

## 結論

重複の中心は以下の 4 系統。

1. プロフィール整形
2. 会話履歴整形
3. LLM 実行の定型処理
4. ツール実行ノードの結果反映処理

最初に `util` 化しやすいのは 1 と 2。

## 重複候補の一覧

### 1. プロフィール整形処理

共通して以下のような情報を文字列化している。

- `name`
- `age`
- `meeting_timing_preference`
- `profile_summary`
- `raw_profile_text`

差分は主に以下。

- `raw_profile_text` を含めるかどうか
- 見出し名が `[基本情報]` か `[プロフィール基本情報]` か
- 自分プロフィール用か相手プロフィール用か
- 空データ時の文言

対象箇所:

- `DecisionNode._build_profile_text`
  - `src/app/agent/core/nodes/decision/node.py`
- `GenerateReplyTool._build_profile_text`
  - `src/app/agent/core/tools/generate_reply/tool.py`
- `GenerateReplyTool._build_self_profile_text`
  - `src/app/agent/core/tools/generate_reply/tool.py`
- `GenerateFirstMessageTool._build_profile_text`
  - `src/app/agent/core/tools/generate_first_message/tool.py`
- `GenerateFirstMessageTool._build_self_profile_text`
  - `src/app/agent/core/tools/generate_first_message/tool.py`
- `ExtractConversationFactsTool._build_profile_text`
  - `src/app/agent/core/tools/extract_conversation_facts/tool.py`
- `RefineReplyTool._build_profile_text`
  - `src/app/agent/core/tools/refine_reply/tool.py`
- `ReplyRuleCheckTool._build_profile_text`
  - `src/app/agent/core/tools/reply_rule_check/tool.py`
- `InviteDateReplyTool._build_profile_text`
  - `src/app/agent/core/tools/invite_date_reply/tool.py`

補足:

- `DEFAULT_MEETING_TIMING_PREFERENCE` の補完も複数箇所で重複している

### 2. 会話履歴整形処理

共通して `messages` を走査し、`sender` と `message` を LLM 向け文字列に整形している。

代表的な形式は以下の 3 種類。

- 簡易形式: `相手: ...` / `自分: ...`
- 詳細形式: `id`, `timestamp`, `sender`, `message` を含む形式
- 補足付き形式: `updated_at` を末尾に付与する形式

対象箇所:

- `DecisionNode._build_conversation_text`
  - `src/app/agent/core/nodes/decision/node.py`
- `FinalReplyRewriteNode._build_conversation_text`
  - `src/app/agent/core/nodes/final_reply_rewrite/node.py`
- `GenerateReplyTool._build_conversation_text`
  - `src/app/agent/core/tools/generate_reply/tool.py`
- `InviteDateReplyTool._build_conversation_text`
  - `src/app/agent/core/tools/invite_date_reply/tool.py`
- `ExtractConversationFactsTool._build_conversation_text`
  - `src/app/agent/core/tools/extract_conversation_facts/tool.py`
- `RefineReplyTool._build_conversation_text`
  - `src/app/agent/core/tools/refine_reply/tool.py`
- `ReplyRuleCheckTool._build_conversation_text`
  - `src/app/agent/core/tools/reply_rule_check/tool.py`
- `ReplySafetyCheckTool._build_conversation_text`
  - `src/app/agent/core/tools/reply_safety_check/tool.py`
- `ScoreReplyQualityTool._build_conversation_text`
  - `src/app/agent/core/tools/score_reply_quality/tool.py`

差分:

- 空メッセージや不正データをスキップする実装としない実装が混在している
- `sender` を `相手` / `自分` に変換するものと、生値をそのまま使うものがある
- `DecisionNode` は詳細フォーマットのため単純統合はしにくい

### 3. LLM 実行の定型処理

多くの node / tool で以下の流れが繰り返されている。

1. `get_chat_model_gpt5_4()` で LLM を取得
2. `load_prompt_from_yaml(...)` で prompt をロード
3. `prompt.invoke(...)` で変数を流し込む
4. `with_structured_output(...)` で structured output を使う
5. `invoke(...)` で結果を取得する

対象箇所:

- `src/app/agent/core/nodes/decision/node.py`
- `src/app/agent/core/nodes/final_reply_rewrite/node.py`
- `src/app/agent/core/tools/generate_reply/tool.py`
- `src/app/agent/core/tools/generate_first_message/tool.py`
- `src/app/agent/core/tools/extract_conversation_facts/tool.py`
- `src/app/agent/core/tools/invite_date_reply/tool.py`
- `src/app/agent/core/tools/refine_reply/tool.py`
- `src/app/agent/core/tools/reply_rule_check/tool.py`
- `src/app/agent/core/tools/reply_safety_check/tool.py`
- `src/app/agent/core/tools/score_reply_quality/tool.py`

注意点:

- 例外処理や canvas 更新まで含めて共通化すると抽象度が上がりすぎる可能性がある
- 最初の util 化対象としては整形関数より優先度は低い

### 4. ツール実行ノードの結果反映処理

`ActionNode` と `FixedToolNode` に以下の重複がある。

- `execution_id` の存在確認
- tool 実行
- `tool_result.model_dump()` の吸収
- `ActionOutputSchema` の組み立て
- `selected_tool`, `tool_result`, `action_loop_count` の state 反映

対象箇所:

- `src/app/agent/core/nodes/action/node.py`
- `src/app/agent/core/nodes/fixed_pipeline/node.py`

補足:

- こちらは `node` 専用 helper として切り出す余地がある
- ただし util 化の効果はプロフィール整形や会話履歴整形より小さい

## util 化の優先度

### 優先度高

1. プロフィール整形 util
2. 会話履歴整形 util

理由:

- 重複箇所が多い
- 差分が少なく引数で吸収しやすい
- LLM 入力品質のばらつきも揃えやすい

### 優先度中

1. canvas への `generated_reply` / `reply_reasoning` 反映 helper
2. `ActionNode` / `FixedToolNode` の共通 helper

### 優先度低

1. LLM 実行フローの抽象化

理由:

- 共通化しすぎると個別ツールの見通しを落としやすい
- 例外処理や schema 差分をどう吸収するか設計が必要

## 最初の切り出し案

候補配置:

- `src/app/agent/core/utils/prompt_text_builders.py`

候補関数:

- `build_profile_text(profile, *, include_raw_profile_text=True, header_style="basic")`
- `build_self_profile_text(profile)`
- `build_conversation_text(messages, *, mode="simple")`
- `build_conversation_text_with_metadata(conversation)`

## util 化を急がなくてよい箇所

以下は現時点では固有ロジックが強い。

- `InviteDateReplyTool` の店選定、時間帯推定、代替案作成
- `ObserveNode` の継続 / 終了判定
- `RefineReplyTool` のデバッグログ出力

## 次の作業候補

1. `profile_text` 系を先に util に切り出す
2. 続けて `conversation_text` 系を統合する
3. その後に node 側の実行 helper を検討する
