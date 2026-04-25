## ML flowのインストール手順

### インストール

**インストールコマンド**

`uv add 'mlflow[genai]'`

**動作確認**

`uv run mlflow --version`

### Tracking Serverの起動

`uv run mlflow server --port 5000`

**画面項目の作成**

- メインエリア：中央の白色の部分
- ナビゲーションパネル：ページの切り替えを行うナビゲーション。GenAI/Model Trainingが選択可能。基本的はGenAIを利用する

### 簡単な画面の味方メモ

#### Trace - Details & TimeLine

- ChatPromptTemplateでプロンプトの内容を確認できる