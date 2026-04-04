# 開発用のメモ

## よく使うコマンド

### サーバー起動

```bash
uv run python -m uvicorn app.agent.entrypoint:app --reload --app-dir src
```

### ツールの単独実行

```bash
uv run python scripts/eval_score_reply_quality.py --cases eval/score_reply_quality_cases.yaml --data-dir data/test_user --output-dir eval/results
```

### issueの生成
```bash
gh issue create --title "[BUG] モジュールグローバルな値の取り扱い方法検討" --body-file ".\docs\issues\011_issue.md"
```

## 課題

### 📊 テストデータ・会話品質
- テスト用の会話のバリエーションが少ない

### 📝 ログ・履歴管理
- プロンプトの内容も履歴に残したい
- 各ノード、ツールのスキーマが持つ情報の整理
- jsonログ確認用のUIが欲しい

### 🧪 テスト・評価
- ツールのテストを書きたい
- 評価用のツールをひとまとめにしたい。
- 

### 🏗️ アーキテクチャ・状態管理

### 🐛 バグより
- `observe_node`の観測結果をもっと詳細に書く必要がある。と思った