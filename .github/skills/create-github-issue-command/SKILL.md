---
name: create-github-issue-command
description: "gh issue create コマンドを構築・実行するときに使う。GitHub Issue の発行、gh コマンドの実行、issue の登録に関する知識を提供する。"
---

# GitHub Issue 作成コマンド リファレンス

## 基本コマンド形式

```bash
gh issue create --title "<タイトル>" --body-file docs/issues/NNN_issue.md
```

## ルール

- 使用できるオプションは `--title` と `--body-file` のみ
- `--body-file` には `docs/issues/` 配下のファイルパスをそのまま指定する
- コマンドはプロジェクトルート（`pyproject.toml` があるディレクトリ）から実行する
- タイトルは日本語で、Issue 概要から簡潔に抜粋する

## タイトルの決め方

1. Issue 本文の `## 概要` セクション冒頭から抜粋する
2. 40文字以内を目安にする
3. 機能名・対象・目的が分かる表現にする
4. 曖昧な表現（「改善」「追加」のみ）は避ける

## 実行例

```bash
gh issue create --title "RAGによるエージェント返信のパーソナライズ機能の実装" --body-file docs/issues/034_issue.md
```

## 前提条件

- GitHub CLI (`gh`) がインストール済みであること
- `gh auth login` で認証済みであること
- リモートリポジトリが設定済みであること

## エラー時の対処

| エラー | 原因 | 対処 |
|---|---|---|
| `gh: command not found` | gh 未インストール | `winget install GitHub.cli` |
| `not logged into any GitHub hosts` | 未認証 | `gh auth login` を実行 |
| `no git remote found` | リモート未設定 | `git remote add origin <URL>` |
| ファイルが見つからない | パス誤り | `docs/issues/` 配下のファイル名を確認 |
