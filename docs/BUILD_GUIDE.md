# macOS ネイティブアプリ ビルド & 配布ガイド

## 概要

このドキュメントでは、ParakeetTDT SwiftUI アプリケーションのビルドから配布までの手順を説明します。

## 前提条件

- macOS 13.0 (Ventura) 以降
- Xcode 15.0 以降
- Apple Developer アカウント（配布用）
- Python 3.13 以降
- uv パッケージマネージャ

## 開発環境のセットアップ

### 1. 初回セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/ymuichiro/parakeet-tdt-ui.git
cd parakeet-tdt-ui

# セットアップスクリプトを実行
./scripts/dev-setup.sh
```

このスクリプトは以下を実行します：
- 必要なツールの確認
- Python 仮想環境の作成
- Python 依存関係のインストール
- Python ライブラリパスの検出

### 2. 環境変数の設定

セットアップスクリプトが出力する環境変数を設定します：

```bash
export PYTHON_LIBRARY="/Library/Frameworks/Python.framework/Versions/3.13"
export PYTHON_MODULE_PATH="/path/to/parakeet-tdt-ui"
```

## 開発ビルド

### コマンドラインから

```bash
cd ParakeetTDT
swift build
swift run ParakeetTDT
```

### Xcode から

1. `ParakeetTDT/Package.swift` を Xcode で開く
2. Product → Scheme → Edit Scheme を選択
3. Run → Arguments → Environment Variables に以下を追加：
   - `PYTHON_LIBRARY`: Python.framework のパス
   - `PYTHON_MODULE_PATH`: リポジトリのルートパス
4. ⌘R でビルド＆実行

## 配布用ビルド

### Phase 5 で実装予定の項目

配布可能な .app バンドルを作成するには、以下の手順が必要です：

#### 1. Python ランタイムの埋め込み

```bash
# アプリバンドル内に Python 環境を作成
python3 -m venv ParakeetTDT.app/Contents/Resources/python/venv

# 依存関係をインストール
source ParakeetTDT.app/Contents/Resources/python/venv/bin/activate
pip install parakeet-mlx sounddevice soundfile
```

#### 2. Python モジュールのコピー

```bash
# app モジュールをバンドルに含める
cp -r app ParakeetTDT.app/Contents/Resources/python/
```

#### 3. Info.plist の設定

`ParakeetTDT/Info.plist` に必要な権限を追加：

- `NSMicrophoneUsageDescription`: マイクアクセスの説明
- `LSMinimumSystemVersion`: 最小 macOS バージョン

#### 4. コード署名

```bash
# 開発証明書で署名（開発用）
codesign --deep --force --verify --verbose \
  --sign "Apple Development: your-name@example.com" \
  ParakeetTDT.app

# 配布証明書で署名（配布用）
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: Your Name (TEAM_ID)" \
  --options runtime \
  --entitlements ParakeetTDT/Entitlements.plist \
  ParakeetTDT.app
```

#### 5. Notarization（公証）

```bash
# アプリを ZIP で圧縮
ditto -c -k --keepParent ParakeetTDT.app ParakeetTDT.zip

# Apple に提出
xcrun notarytool submit ParakeetTDT.zip \
  --apple-id "your-apple-id@example.com" \
  --team-id "TEAM_ID" \
  --password "app-specific-password" \
  --wait

# Notarization チケットをステープル
xcrun stapler staple ParakeetTDT.app
```

#### 6. DMG の作成

```bash
# DMG を作成
hdiutil create -volname "ParakeetTDT" \
  -srcfolder ParakeetTDT.app \
  -ov -format UDZO \
  ParakeetTDT.dmg
```

## ビルドスクリプトの使用

基本的なアプリバンドル作成には、提供されているスクリプトを使用できます：

```bash
./scripts/build-app.sh
```

このスクリプトは：
1. Swift アプリケーションをリリースモードでビルド
2. .app バンドル構造を作成
3. Python ランタイムと依存関係を埋め込み
4. Python モジュールをコピー

**注意**: このスクリプトは基本的なバンドルを作成しますが、署名と公証は含まれていません。

## トラブルシューティング

### Python ライブラリが見つからない

症状: `Could not find Python library` エラー

解決策:
1. `dev-setup.sh` を実行して正しいパスを確認
2. `PYTHON_LIBRARY` 環境変数を正しく設定

### Python モジュールのインポートエラー

症状: `Failed to import Python modules` エラー

解決策:
1. `PYTHON_MODULE_PATH` がリポジトリルートを指しているか確認
2. `app/` ディレクトリが存在するか確認
3. Python 依存関係がインストールされているか確認（`uv pip install -e .`）

### マイク権限エラー

症状: マイクへのアクセスが拒否される

解決策:
1. `Info.plist` に `NSMicrophoneUsageDescription` が含まれているか確認
2. macOS の設定 → プライバシーとセキュリティ → マイク でアプリの権限を確認

### MLX モデルのロードが遅い

初回起動時はモデルのダウンロードが必要です：

- モデルは `~/.cache/huggingface/` にキャッシュされます
- 初回は数分かかる場合があります
- 2回目以降はキャッシュから高速にロード

## CI/CD

### GitHub Actions での自動ビルド

`.github/workflows/build-macos.yml` を作成して自動ビルドを設定できます：

```yaml
name: Build macOS App

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: macos-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.13'
    
    - name: Install uv
      run: pip install uv
    
    - name: Install Python dependencies
      run: uv pip install -e .
    
    - name: Build Swift app
      run: |
        cd ParakeetTDT
        swift build -c release
```

## 配布チェックリスト

Phase 5 で完了すべき項目：

- [ ] Python ランタイムの埋め込み手順を文書化
- [ ] 依存関係のバンドル方法を文書化
- [ ] Entitlements.plist の作成
- [ ] コード署名スクリプトの作成
- [ ] Notarization 手順の自動化
- [ ] DMG/PKG インストーラの作成スクリプト
- [ ] 配布前チェックリストの作成
- [ ] エンドユーザー向けインストールガイドの作成

## 参考リンク

- [Apple Developer Documentation - Distributing Your App](https://developer.apple.com/documentation/xcode/distributing-your-app-for-beta-testing-and-releases)
- [PythonKit GitHub](https://github.com/pvieito/PythonKit)
- [Code Signing Guide](https://developer.apple.com/library/archive/documentation/Security/Conceptual/CodeSigningGuide/Introduction/Introduction.html)
- [Notarizing macOS Software](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
