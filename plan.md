# macOS ネイティブ化計画（SwiftUI + PythonKit）

## 目的
- 既存の Python コアロジック（録音制御・書き起こし）を活かしつつ、UI を macOS ネイティブ（SwiftUI）へ刷新する。
- 将来的な notarization・配布を見据えて、Python ランタイムと依存パッケージをアプリバンドル内に組み込める構成を整える。

## ゴール
1. SwiftUI ベースの macOS アプリプロジェクトを作成し、既存 Python ロジックへ橋渡しする。
2. 録音、書き起こし、結果表示の基本フローを SwiftUI 側から操作できるようにする。
3. テストとビルド手順を明文化して、配布可能な形まで整理する。

---

## フェーズ分割とタスク

### フェーズ0: 下準備
- [ ] 既存 Python コードの責務整理
  - GUI 依存の無い関数/API として `recorder`, `transcriber` を再確認し、必要であれば CLI/関数インターフェースを整える。
  - Python 側でコマンド的に呼び出せる最小 API（録音開始/停止、文字起こし関数）を定義。
- [ ] 依存パッケージの棚卸し
  - `sounddevice`, `soundfile`, `mlx`, `parakeet_mlx` などのバージョン固定を確認し、埋め込み用 wheel/bundle の入手方法を調査。
- [ ] Python 実行時パスを固定化
  - Swift から呼び出しやすいように `pyproject.toml` のエントリポイントやモジュール構造を明文化。

### フェーズ1: Swift 側プロジェクト基盤
- [ ] Xcode で macOS App (SwiftUI + AppKit lifecycle) プロジェクトを作成。
- [ ] パッケージ依存で PythonKit を導入。
- [ ] ビルド設定で Python.framework をリンクし、`@rpath` にアプリ内の埋め込み Python を解決できるよう設定。
- [ ] 開発中はシステム Python/`uv` 仮想環境を参照できるようランチスクリプトを準備。

### フェーズ2: Python ブリッジ層（Swift ↔︎ Python）
- [ ] Swift 側に `TranscriptionService`（録音制御 + 文字起こし呼び出し）を定義。
- [ ] PythonKit 経由で `app.recorder.AudioRecorder` を Swift から生成・制御。
  - 録音のライフサイクルを Swift (AVFoundation) に置き換えるか、Python に委譲するかを再評価。
- [ ] PythonKit 経由で `app.transcriber.transcribe_audio` を呼び出し、結果を Swift に戻すラッパーを用意。
- [ ] エラー伝播・例外処理を整理し、Swift の `Result` / `async` にマッピング。

### フェーズ3: SwiftUI UI 実装
- [ ] 画面要件の洗い出し（録音ボタン、状態表示、テキストエリア、自動保存など）。
- [ ] 状態管理（`@StateObject` + `ObservableObject`）で録音状態・進行状況を表現。
- [ ] AVFoundation を用いた録音のネイティブ実装を検討。
  - **案 A:** Swift 側で録音 → 一時 WAV ファイルを作成 → Python の `transcribe_audio` へ渡す。
  - **案 B:** Python の `AudioRecorder` を PythonKit から起動。配布時のデバイス権限周りを確認。
- [ ] トランスクリプション結果を UI に反映し、エラー時はアラート表示。

### フェーズ4: テスト・CI・DX 整備
- [ ] Python 側のユニットテスト（録音・文字起こしモックなど）の整備と自動化。
- [ ] Swift 側での単体テスト（サービス層に対するモック）と UI テスト（Snapshot か最小限の動作確認）。
- [ ] CI ワークフロー検討（`xcodebuild` + Python テスト → 成果物アーカイブ）。

### フェーズ5: 配布 & ドキュメント
- [ ] アプリバンドルへの Python 埋め込み手順を整理。
  - `Resources/python` 配下へ仮想環境を配置、`PYTHONHOME`/`PYTHONPATH` を Swift 起動時に設定。
  - 依存モジュール（MLX, Parakeet 等）のビルドと配置。
- [ ] Notarization/コード署名の手順確認。
- [ ] `README.md` を更新し、開発・テスト・パッケージング手順を記載。
- [ ] エンドユーザー向け Quick Start と既知の制約（モデルサイズ/初回ダウンロード等）をまとめる。

---

## リスクと対策メモ
- **Python 実行環境**: MLX やサードパーティライブラリが arm64 macOS で動作する wheel を持つか事前確認。必要ならソースビルドフローを用意。
- **権限問題**: 録音許可（`NSMicrophoneUsageDescription`）を `Info.plist` へ追加。
- **モデルサイズ**: 初回ダウンロード時の UX を考慮し、UI に進捗やキャッシュ状況を表示。
- **パフォーマンス**: Python ↔︎ Swift の橋渡しでメインスレッドをブロックしないよう、`Task` や `DispatchQueue` で非同期化。

## 成果物チェックリスト
- [ ] SwiftUI アプリプロジェクト + Python ブリッジ実装
- [ ] 埋め込み Python ランタイムと依存を含むビルド手順
- [ ] 自動テスト（Python & Swift）
- [ ] 更新されたドキュメント（README、配布手順）
- [ ] 将来の機能拡張に備えた TODO/Issues 整理
