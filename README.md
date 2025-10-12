# Parakeet TDT Transcriber

macOS 向けのデスクトップアプリとして、マイクからの録音・推論・書き起こし履歴の管理までをワンクリックで完結させるツールです。Apple MLX バックエンドで動作する `parakeet-mlx` Parakeet-TDT (0.6B) モデルを同梱前提で扱い、日本語音声の高速なローカル書き起こしをサポートします。

## 主な機能

- **ワンステップ書き起こし**: 録音開始から停止・推論までを 1 つのボタンで操作。経過時間と処理状況をヘッダーに表示します。
- **マイクデバイス選択**: 利用可能な入力デバイスを自動列挙し、ドロップダウンから切り替えられます。
- **モデル設定**: FP32 モードやローカルアテンションの有効化／コンテキスト幅の調整を GUI で切り替え。
- **書き起こし履歴**: セッション内に複数の書き起こし結果を保存し、選択するだけで結果を再表示。コンテキストメニューからコピーや削除が可能です。
- **エクスポート**: 生成テキストをワンクリックでクリップボードにコピー、またはファイルとして保存できます。

## 必要要件

- macOS 14 以降 / Apple Silicon を推奨
- Python 3.13
- [uv](https://github.com/astral-sh/uv)（依存解決用）
- [ffmpeg](https://ffmpeg.org/)（録音・変換処理用）

## 使い方

1. 依存関係をセットアップします。

   ```bash
   uv sync
   ```

2. アプリケーションを起動します。

   ```bash
   uv run python main.py
   ```

   初回起動時は macOS からマイク使用許可を求められる場合があります。`システム設定 > プライバシーとセキュリティ > マイク` で `uv`（Python） に権限を付与してください。

3. **録音開始** ボタンを押すと録音がスタートします。もう一度押すと録音が停止し、自動で書き起こしが始まります。

4. 書き起こし結果は中央のテキストビューに表示されます。履歴リストに結果が追加され、他の履歴をクリックするとその内容を再表示できます。

5. 結果を利用したい場合は、ヘッダー右側の **コピー** ボタン、または **保存…** ボタンを押してください。

## PyInstaller によるスタンドアロンバンドル

PyInstaller を使ってアプリ本体と依存ライブラリ、`ffmpeg` バイナリをひとまとめにした配布物を生成できます。

1. 依存関係を追加でインストールします。

   ```bash
   uv sync --extra bundle
   ```

2. macOS 用の静的 `ffmpeg` バイナリを準備し、アプリが参照できるようにします。例:

   ```bash
   mkdir -p build/ffmpeg
   curl -L -o build/ffmpeg/ffmpeg.zip https://evermeet.cx/ffmpeg/getrelease/zip
   unzip -o build/ffmpeg/ffmpeg.zip -d build/ffmpeg
   chmod +x build/ffmpeg/ffmpeg
   ```

   既存の Homebrew 版を利用する場合は `which ffmpeg` で得られるパスを使ってください。

3. PyInstaller でビルドします。`PARAKEET_FFMPEG_PATH` にバイナリを指定すると、生成物の `parakeet-tdt.app/Contents/MacOS/bin/ffmpeg` にコピーされます。

   ```bash
   PARAKEET_FFMPEG_PATH="$(pwd)/build/ffmpeg/ffmpeg" \
   uv run pyinstaller build/pyinstaller/parakeet.spec
   ```

   出力は `dist/parakeet-tdt` ディレクトリに生成されます（`.app` バンドルとサポートファイル）。

4. 生成物をチェックします。

   - `dist/parakeet-tdt/parakeet-tdt.app` を Finder から起動して動作確認します。
   - `dist/parakeet-tdt/parakeet-tdt.app/Contents/MacOS/bin/ffmpeg` が存在し、権限が `+x` になっていることを確認します。
   - 配布前に不要なキャッシュ（`build/pyinstaller` や `.DS_Store` 等）が混入していないかを見直してください。

### PyInstaller セットアップのポイント

- `build/pyinstaller/parakeet.spec` が標準化されたビルド定義です。`PySide6`、`parakeet_mlx`、`mlx`、`sounddevice` のデータ/ネイティブライブラリを自動収集します。
- `PARAKEET_FFMPEG_PATH` を指定しなかった場合は OS にインストールされた `ffmpeg` へフォールバックします。完全に依存レスにしたい場合は必ず同変数を設定してください。
- Apple Silicon macOS での動作を前提にしています。Intel 用に配布する場合は別途検証とコード署名が必要です。
- PyInstaller のビルド後、`codesign` や `notarytool` で署名することで Gatekeeper の警告を抑制できます。

## モデルについて

アプリケーションでは `mlx-community/parakeet-tdt_ctc-0.6b-ja` モデルを利用します。他モデルの切り替えは、精度と動作検証の観点で現時点ではサポートしていません。初回起動時はモデルのダウンロードに時間がかかる場合があります。

## 技術メモ

- GUI: Qt for Python (`PySide6`)
- 録音: `sounddevice` + `soundfile`
- モデル推論: `parakeet-mlx` (MLX backend)
- バンドル: Nuitka スタンドアロンモード + PySide6 プラグイン
- ログ: `~/Library/Logs/parakeet-tdt-study/` にセッションごとのログファイルを出力します。

## 開発に参加するには

Issue と Pull Request を歓迎します。バグ報告や改善アイデアがあれば [GitHub Issue](https://github.com/ymuichiro/parakeet-tdt-ui/issues) に投稿してください。PR では以下の点にご留意ください。

- 新規機能は可能な範囲で自動テストまたは動作確認手順を添えてください。
- UI 変更時はスクリーンショットや記述で差分が分かるようにしてください。
- 依存関係を追加する際は、`pyproject.toml` と `uv.lock` を更新してください。

## ライセンス

本プロジェクトは [MIT License](LICENSE) の下で提供されます。

## モデル API を直接利用したい場合

```python
from pathlib import Path

import mlx.core as mx
from parakeet_mlx import from_pretrained

model = from_pretrained(
    "mlx-community/parakeet-tdt_ctc-0.6b-ja",
    dtype=mx.bfloat16,
)

result = model.transcribe(Path("audio.wav"), dtype=mx.bfloat16)
print(result.text.strip())
```

長時間の音声では `chunk_duration` や `overlap_duration` を指定してチャンク処理を行ったり、`dtype=mx.float32` を指定して FP32 で計算することも可能です。ローカルアテンションを利用したい場合は、ロード後に下記を実行してください。

```python
model.encoder.set_attention_model("rel_pos_local_attn", (256, 256))
```

