# parakeet-tdt-study

`parakeet-mlx` をベースに、Python から直接モデルを呼び出す方法と、macOS 向けのデスクトップアプリを提供しています。

## デスクトップアプリ（macOS）

### SwiftUI ネイティブアプリ (推奨)

macOS ネイティブの SwiftUI アプリケーションを `ParakeetTDT/` ディレクトリに用意しています。

- **場所**: `ParakeetTDT/`
- **詳細**: [ParakeetTDT/README.md](ParakeetTDT/README.md)
- **セットアップ**: `./scripts/dev-setup.sh`

SwiftUI + PythonKit を使用して既存の Python ロジックを活用しながら、ネイティブな macOS UI を提供します。

### Python/Qt アプリ (従来版)

### 機能概要

- 「録音開始」ボタンを押すとマイク録音を開始し、もう一度押すと録音を停止します。
- 停止直後に `mlx-community/parakeet-tdt_ctc-0.6b-ja` モデルで自動的に書き起こしを行い、結果をウィンドウ内に表示します。
- 書き起こし結果はその場でコピー＆ペーストできます。

### 実行方法

```bash
uv run python main.py
```

初回起動時にマイク使用の許可ダイアログが表示される場合があります。macOS の「システム設定 ＞ プライバシーとセキュリティ ＞ マイク」から、`uv`（Python）にマイク利用権限を付与してください。

### 技術メモ

- GUI には Qt for Python (`PySide6`) を使用しています。
- 録音は `sounddevice` + `soundfile` で直接 WAV に書き出しています。
- 書き起こし処理はバックグラウンドスレッドで行い、モデルはキャッシュして再利用するため、2 回目以降の推論は高速です。

## 直接呼び出すときのポイント

- `parakeet_mlx.from_pretrained()` で Hugging Face 上（もしくはローカル）からモデルをロードできます。
- ロードしたモデルは `model.transcribe(path, ...)` で音声ファイルを処理できます。戻り値は `AlignedResult` で、`text` や `sentences`（タイムスタンプ付き）にアクセスできます。
- CLI で指定できる `--fp32` やローカルアテンションなどの設定も、同じメソッド／プロパティを呼ぶことで反映できます。

### 最小コード例

```python
from pathlib import Path

import mlx.core as mx
from parakeet_mlx import from_pretrained

model = from_pretrained(
		"mlx-community/parakeet-tdt_ctc-0.6b-ja",
		dtype=mx.bfloat16,
)

result = model.transcribe("audio.wav", dtype=mx.bfloat16)
print(result.text.strip())
```

### 追加のオプション

- 長時間の音声に対してチャンク処理を行う場合は `chunk_duration`（秒）と `overlap_duration` を指定します。
- FP32 で動かしたい場合は `dtype=mx.float32` を渡します。
- 長い入力でメモリ使用量を抑えたい場合は、ロード後に `model.encoder.set_attention_model("rel_pos_local_attn", (256, 256))` のようにローカルアテンションへ切り替え可能です。

## サンプルスクリプト

`examples/transcribe.py` は上記の処理を CLI 風にまとめたスクリプトです。

```bash
uv run python examples/transcribe.py audio.wav \
	--model mlx-community/parakeet-tdt_ctc-0.6b-ja \
	--chunk-duration 120 \
	--overlap-duration 15
```

環境変数や CLI 版で使えるオプションとほぼ同じ形で制御でき、処理結果は標準出力にテキストで出力されます。

