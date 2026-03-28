# Dating Conversation Agent - GitHub Copilot用カスタム指示

## プロジェクト概要
これはLangGraphを使用したグラフベースのワークフローのPythonベースのデーティング会話エージェントです。コアアーキテクチャは`base_node.py`を継承したノードを中心に構成されています。

## コーディングパターン
- すべてのノードは`src/app/agent/core/nodes/base_node.py`を継承しなければなりません。
- 新しいノードの構造は以下の通り:
  - base_nodeのインポート: `from src.app.agent.core.nodes.base_node import BaseNode`
  - クラスの定義: `class MyNode(BaseNode):`
  - 必要なメソッドの実装（例: `run`, `validate`）。
- PEP 8スタイルガイドに従う。
- すべての関数パラメータと戻り値に型ヒントを使用。
- src/ディレクトリ内では相対インポートを優先。

## 避けるべきこと
- ベースクラスの直接インスタンス化。
- グローバル変数の使用；依存性注入を使用。
- ハードコードされた文字列；定数や設定ファイルを使用。

## ライブラリとフレームワーク
- グラフ構築にLangGraphを使用。
- I/O操作にはasync/awaitを優先。
- カスタムのjson_loggerユーティリティを使用してログを記録。