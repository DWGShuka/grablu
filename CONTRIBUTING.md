# 開発ガイドライン

## ブランチ戦略

このプロジェクトはGit Flowに基づいたブランチ戦略を採用しています。

### ブランチの種類

#### `main` ブランチ
- **目的**: 本番環境リリース用
- **保護**: 直接プッシュ禁止
- **更新方法**: `develop`ブランチからのプルリクエストのみ

#### `develop` ブランチ（デフォルト）
- **目的**: 開発の中心ブランチ
- **保護**: 直接プッシュ推奨（小規模チーム）、または機能ブランチからのPR
- **テスト**: プッシュ時にCI自動実行

#### 機能ブランチ (`feature/*`)
- **目的**: 新機能の開発
- **作成元**: `develop`
- **マージ先**: `develop`
- **命名規則**: `feature/機能名` (例: `feature/add-export-function`)

#### バグ修正ブランチ (`fix/*`)
- **目的**: バグの修正
- **作成元**: `develop`
- **マージ先**: `develop`
- **命名規則**: `fix/バグ内容` (例: `fix/login-error`)

#### ホットフィックスブランチ (`hotfix/*`)
- **目的**: 本番環境の緊急バグ修正
- **作成元**: `main`
- **マージ先**: `main` と `develop` の両方
- **命名規則**: `hotfix/修正内容` (例: `hotfix/security-patch`)

## ワークフロー

### 新機能開発

```bash
# developブランチに切り替え
git checkout develop
git pull origin develop

# 機能ブランチを作成
git checkout -b feature/new-feature

# 開発・コミット
git add .
git commit -m "Add: 新機能の説明"

# リモートにプッシュ
git push origin feature/new-feature

# GitHubでdevelopブランチへのプルリクエストを作成
```

### バグ修正

```bash
# developブランチに切り替え
git checkout develop
git pull origin develop

# 修正ブランチを作成
git checkout -b fix/bug-description

# 修正・コミット
git add .
git commit -m "Fix: バグの説明"

# リモートにプッシュ
git push origin fix/bug-description

# GitHubでdevelopブランチへのプルリクエストを作成
```

### 本番リリース

```bash
# developが安定していることを確認
git checkout develop
git pull origin develop

# GitHubでdevelop → mainへのプルリクエストを作成
# レビュー後、マージ

# mainブランチを更新
git checkout main
git pull origin main

# タグを作成
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

### 緊急修正（ホットフィックス）

```bash
# mainブランチから作成
git checkout main
git pull origin main
git checkout -b hotfix/critical-bug

# 修正・コミット
git add .
git commit -m "Hotfix: 緊急修正の説明"

# mainにマージ
git checkout main
git merge hotfix/critical-bug
git push origin main

# developにもマージ
git checkout develop
git merge hotfix/critical-bug
git push origin develop

# タグを作成
git tag -a v1.0.1 -m "Hotfix v1.0.1"
git push origin v1.0.1

# ホットフィックスブランチを削除
git branch -d hotfix/critical-bug
```

## コミットメッセージ規約

コミットメッセージはプレフィックスで種類を明示してください：

- `Add:` - 新機能追加
- `Update:` - 既存機能の更新
- `Fix:` - バグ修正
- `Refactor:` - リファクタリング
- `Test:` - テスト追加・修正
- `Docs:` - ドキュメント更新
- `Style:` - コードスタイル修正（機能変更なし）
- `Chore:` - ビルド設定、依存関係更新など

**例:**
```
Add: ユーザー登録機能を実装
Fix: ログイン時のセッションタイムアウトエラーを修正
Update: データベーススキーマを最適化
Docs: READMEにセットアップ手順を追加
```

## プルリクエスト

### プルリクエストを作成する前に

1. **最新のdevelopを取り込む**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout your-branch
   git merge develop
   ```

2. **ローカルでテストを実行**
   ```bash
   pytest tests/ -v
   flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
   ```

3. **不要なファイルがコミットされていないか確認**
   ```bash
   git status
   ```

### プルリクエストのタイトル

コミットメッセージと同様の規約を使用：

- `[Add] ユーザー登録機能`
- `[Fix] ログインエラーの修正`
- `[Update] データベーススキーマの最適化`

### プルリクエストの説明

以下の内容を含めてください：

```markdown
## 変更内容
- 変更点1
- 変更点2

## 動作確認
- [ ] ローカルでテスト実行済み
- [ ] 新機能の動作確認済み
- [ ] 既存機能への影響なし

## スクリーンショット（該当する場合）
[画像を添付]

## 関連Issue
Closes #123
```

## コードレビュー

### レビュアー向け

- **機能**: 実装が要件を満たしているか
- **テスト**: 適切なテストが含まれているか
- **コード品質**: 可読性、保守性が高いか
- **パフォーマンス**: 性能上の問題がないか
- **セキュリティ**: 脆弱性がないか

### レビュイー向け

- フィードバックは建設的に受け止める
- 質問や議論は歓迎
- 必要に応じて追加コミットで修正

## CI/CD

### 自動テスト

プッシュ時に自動実行されるテスト：

1. **Linting** (flake8)
2. **Unit Tests** (pytest)
3. **Code Coverage** (pytest-cov)

詳細は[CI.md](CI.md)を参照。

### テスト失敗時

1. CIのログを確認
2. ローカルで同じテストを実行
3. 修正してプッシュ

```bash
# CIと同じコマンドでローカル実行
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
pytest tests/ -v --cov=. --cov-report=term-missing
```

## ローカル開発環境

詳細は[LOCAL_DEV.md](LOCAL_DEV.md)を参照してください。

## 質問やサポート

- **Issues**: バグ報告や機能要望
- **Discussions**: 質問や議論
- **Pull Requests**: コード提案

開発に貢献していただきありがとうございます！
