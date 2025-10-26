# MimiTranscribe — Japanese Audio Transcriber

This is a one-click desktop tool for **macOS** that handles everything from **microphone recording** and **inference** to **transcription history management**. It is designed to bundle the `parakeet-mlx` **Parakeet-TDT (0.6B) model** running on the **Apple MLX backend**, providing fast **local transcription for Japanese audio**.

![](./assets/image.png)

- [MimiTranscribe — Japanese Audio Transcriber](#mimitranscribe--japanese-audio-transcriber)
  - [Key Features](#key-features)
  - [Quick Start (For Users)](#quick-start-for-users)
  - [Prerequisites (For Developers)](#prerequisites-for-developers)
  - [How to Use (For Developers)](#how-to-use-for-developers)
  - [Standalone Bundle with PyInstaller](#standalone-bundle-with-pyinstaller)
    - [Automatic Release with GitHub Actions](#automatic-release-with-github-actions)
    - [PyInstaller Setup Notes](#pyinstaller-setup-notes)
  - [About the Model](#about-the-model)
- [MimiTranscribe (日本語 README)](#mimitranscribe-日本語-readme)
  - [主な機能](#主な機能)
  - [クイックスタート（ユーザー向け）](#クイックスタートユーザー向け)
  - [必要要件（開発者向け）](#必要要件開発者向け)
  - [使い方（開発者向け）](#使い方開発者向け)
  - [PyInstaller によるスタンドアロンバンドル](#pyinstaller-によるスタンドアロンバンドル)
    - [GitHub Actions での自動リリース](#github-actions-での自動リリース)
    - [PyInstaller セットアップのポイント](#pyinstaller-セットアップのポイント)
  - [モデルについて](#モデルについて)

---

## Key Features

- **One-Step Transcription**: A single button controls the entire process, from starting to stopping the recording and performing the inference. The header displays the elapsed time and processing status.
- **Audio File Import**: Import and transcribe existing audio files (MP3, WAV, M4A, FLAC, OGG, OPUS) with a single click, in addition to live microphone recording.
- **Live Waveform Monitor**: Visualize microphone input levels in real time while recording so you can confirm that audio is being captured.
- **Microphone Device Selection**: Available input devices are listed automatically and can be switched via a dropdown menu.
- **Model Settings**: Easily toggle **FP32 mode** and **Local Attention** activation, or adjust the context window width via the GUI.
- **Multiple Model Support**: Choose from multiple AI models including Parakeet-TDT (Japanese-optimized) and Whisper Large V3 (multilingual). Switch models directly from the UI.
- **Transcription History**: Multiple transcription results are saved within the session. You can re-display any result by simply selecting it from the history list. Results can be copied or deleted via the context menu.
- **Export**: Generate text can be copied to the clipboard or saved as a file with a single click.

---

## Quick Start (For Users)

If you just want to use the application, download the pre-built package from the [Releases page](https://github.com/ymuichiro/parakeet-tdt-ui/releases).

### Download and Setup

1. **Download** the latest release file:
   - Go to the [Releases page](https://github.com/ymuichiro/parakeet-tdt-ui/releases)
   - Download `mimitranscribe-macos-arm64.zip` or `mimitranscribe-macos-arm64.dmg` (for Apple Silicon Macs)

2. **Extract** the downloaded file:
   - **For ZIP**: Double-click the `.zip` file in Finder to extract it, then `MimiTranscribe.app` will appear
   - **For DMG**: Double-click the `.dmg` file to mount it, then drag `MimiTranscribe.app` to your Applications folder

3. **Launch** the application:
   - Double-click `MimiTranscribe.app` to launch the application
   - *Alternative: Right-click `MimiTranscribe.app` and select **Open** if double-clicking doesn't work*

4. **Allow the app to run** (first launch only):
   - macOS may show a security warning: *"MimiTranscribe.app cannot be opened because it is from an unidentified developer"*
   - If this happens:
     - Open **System Settings** > **Privacy & Security**
     - Scroll down and click **Open Anyway** next to the blocked app message
     - Click **Open** in the confirmation dialog

5. **Grant microphone permission** (first launch only):
   - When you first start recording, macOS will ask for permission to use the microphone
   - Click **OK** to allow microphone access

6. **Start using the app**:
   - Press the **Start Recording** button to begin recording
   - Press it again to stop recording and start transcription
   - The transcription result will appear in the central text view

*Note: The first launch may take some time as the AI model is downloaded (approximately 1-2GB).*

---

## Prerequisites (For Developers)

- **macOS 14 or later** / **Apple Silicon** is recommended
- **Python 3.13**
- **[uv](https://github.com/astral-sh/uv)** (for dependency resolution)
- **[ffmpeg](https://ffmpeg.org/)** (for recording and conversion)

---

## How to Use (For Developers)

If you want to build and run the application from source:

1. Set up the dependencies.

```bash
uv sync
```

2.  Start the application.

```bash
uv run python main.py
```

*The first time you run the app, macOS may ask for permission to use the microphone. Please grant permission to `uv` (Python) in **System Settings \> Privacy & Security \> Microphone**.*

3.  Press the **Start Recording** button to begin recording. Press it again to stop, and transcription will start automatically.
4.  The transcription result will appear in the central text view. The result is also added to the history list, and clicking on a different entry will re-display its content.
5.  To use the result, click the **Copy** button or the **Save...** button on the right side of the header.

-----

## Standalone Bundle with PyInstaller

You can use **PyInstaller** to create a single distribution package that includes the application, its dependent libraries, and the `ffmpeg` binary.

1.  Install additional dependencies.

    ```bash
    uv sync --extra bundle
    ```

2.  Prepare a static **`ffmpeg` binary for macOS** and ensure the app can access it. Example:

    ```bash
    mkdir -p build/ffmpeg
    curl -L -o build/ffmpeg/ffmpeg.zip [https://evermeet.cx/ffmpeg/getrelease/zip](https://evermeet.cx/ffmpeg/getrelease/zip)
    unzip -o build/ffmpeg/ffmpeg.zip -d build/ffmpeg
    chmod +x build/ffmpeg/ffmpeg
    ```

    *If you want to use your existing Homebrew version, use the path obtained from `which ffmpeg`.*

3.  Build the application with PyInstaller. Specifying the binary with `PARAKEET_FFMPEG_PATH` will ensure it is copied to `MimiTranscribe.app/Contents/MacOS/bin/ffmpeg` in the generated package.

    ```bash
  PARAKEET_FFMPEG_PATH="$(pwd)/build/ffmpeg/ffmpeg" \
  uv run pyinstaller packaging/pyinstaller/parakeet.spec
    ```

    The build outputs will appear under `dist/`, containing the **`MimiTranscribe.app` bundle** alongside the unpacked `mimitranscribe` support directory.

4.  Check the generated files.

      - Launch `dist/MimiTranscribe.app` from Finder to confirm functionality.
      - Verify that `dist/MimiTranscribe.app/Contents/MacOS/bin/ffmpeg` exists and has `+x` permissions.
      - Before distribution, check that no unnecessary cache files (like `build/` artifacts or `.DS_Store`) have been included.

### Automatic Release with GitHub Actions

  - Pushing a new tag (a semantic version starting with `v*`) will trigger GitHub Actions to run the PyInstaller build on a macOS Runner, creating a `.zip` and `.dmg` that contain `MimiTranscribe.app` bundled with the `ffmpeg` binary fetched from evermeet.cx. (The artifacts are **not code-signed**; Gatekeeper will show a warning the first time.)

### PyInstaller Setup Notes

  - If **`PARAKEET_FFMPEG_PATH`** is not specified, the application will fall back to the OS-installed `ffmpeg`. To ensure complete dependency freedom, you must set this variable.
  - This setup assumes operation on **Apple Silicon macOS**. Distribution for Intel may require additional verification and code signing.

-----

## About the Model

The application supports multiple AI models for speech recognition:

- **Parakeet-TDT 0.6B** (`mlx-community/parakeet-tdt_ctc-0.6b-ja`) - Default model, optimized for Japanese speech recognition
- **Whisper Large V3** (`mlx-community/whisper-large-v3-mlx`) - High-accuracy multilingual model
- **Whisper Large V3 Turbo** (`mlx-community/whisper-large-v3-turbo-q4`) - Fast, quantized version for efficient processing

You can switch between models using the model selector in the GUI. For Japanese audio, Parakeet-TDT is recommended. For multilingual support or higher accuracy requirements, use Whisper models. The initial launch may take some time as the selected model is downloaded.

---

# MimiTranscribe (日本語 README)

macOS 向けのデスクトップアプリとして、マイクからの録音・推論・書き起こし履歴の管理までをワンクリックで完結させるツールです。Apple MLX バックエンドで動作する `parakeet-mlx` Parakeet-TDT (0.6B) モデルを同梱前提で扱い、日本語音声の高速なローカル書き起こしをサポートします。

![](./assets/image.png)

## 主な機能

- **ワンステップ書き起こし**: 録音開始から停止・推論までを 1 つのボタンで操作。経過時間と処理状況をヘッダーに表示します。
- **音声ファイル取り込み**: マイク録音に加えて、既存の音声ファイル（MP3、WAV、M4A、FLAC、OGG、OPUS）をワンクリックで読み込んで書き起こしができます。
- **リアルタイム波形モニタ**: 録音中のマイク入力レベルを波形で表示し、音声が取り込まれていることを視覚的に確認できます。
- **マイクデバイス選択**: 利用可能な入力デバイスを自動列挙し、ドロップダウンから切り替えられます。
- **モデル設定**: FP32 モードやローカルアテンションの有効化／コンテキスト幅の調整を GUI で切り替え。
- **複数モデル対応**: Parakeet-TDT（日本語最適化）、Whisper Large V3（多言語）など複数の AI モデルから選択可能。UI から直接モデルを切り替えられます。
- **書き起こし履歴**: セッション内に複数の書き起こし結果を保存し、選択するだけで結果を再表示。コンテキストメニューからコピーや削除が可能です。
- **エクスポート**: 生成テキストをワンクリックでクリップボードにコピー、またはファイルとして保存できます。

## クイックスタート（ユーザー向け）

アプリケーションをすぐに使いたい場合は、[リリースページ](https://github.com/ymuichiro/parakeet-tdt-ui/releases)からビルド済みパッケージをダウンロードしてください。

### ダウンロードとセットアップ

1. **ダウンロード**: 最新リリースファイルを取得します
   - [リリースページ](https://github.com/ymuichiro/parakeet-tdt-ui/releases)にアクセス
   - `mimitranscribe-macos-arm64.zip` または `mimitranscribe-macos-arm64.dmg` をダウンロード（Apple Silicon Mac 用）

2. **展開**: ダウンロードしたファイルを展開します
   - **ZIP の場合**: Finder で `.zip` ファイルをダブルクリックして展開すると `MimiTranscribe.app` が表示されます
   - **DMG の場合**: `.dmg` ファイルをダブルクリックしてマウントし、`MimiTranscribe.app` をアプリケーションフォルダにドラッグ

3. **起動**: アプリケーションを起動します
   - `MimiTranscribe.app` をダブルクリックして起動
   - *別の方法: ダブルクリックで起動しない場合は、`MimiTranscribe.app` を右クリックして **開く** を選択*

4. **アプリの実行を許可**（初回起動時のみ）:
   - macOS がセキュリティ警告を表示する場合があります：*「"MimiTranscribe.app" は開発元が未確認のため開けません」*
   - この警告が表示された場合:
     - **システム設定** > **プライバシーとセキュリティ** を開く
     - 下にスクロールして、ブロックされたアプリのメッセージの横にある **このまま開く** をクリック
     - 確認ダイアログで **開く** をクリック

5. **マイク使用許可の付与**（初回録音時のみ）:
   - 初めて録音を開始すると、macOS がマイク使用許可を求めます
   - **OK** をクリックしてマイクアクセスを許可

6. **アプリを使い始める**:
   - **録音開始** ボタンを押して録音を開始
   - もう一度押すと録音が停止し、書き起こしが開始されます
   - 書き起こし結果は中央のテキストビューに表示されます

*注意: 初回起動時は AI モデルのダウンロード（約 1～2GB）のため時間がかかる場合があります。*

## 必要要件（開発者向け）

- macOS 14 以降 / Apple Silicon を推奨
- Python 3.13
- [uv](https://github.com/astral-sh/uv)（依存解決用）
- [ffmpeg](https://ffmpeg.org/)（録音・変換処理用）

## 使い方（開発者向け）

ソースコードからアプリケーションをビルドして実行する場合:

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

   ※ 既存の Homebrew 版を利用する場合は `which ffmpeg` で得られるパスを使ってください。

3. PyInstaller でビルドします。`PARAKEET_FFMPEG_PATH` にバイナリを指定すると、生成物の `MimiTranscribe.app/Contents/MacOS/bin/ffmpeg` にコピーされます。

   ```bash
  PARAKEET_FFMPEG_PATH="$(pwd)/build/ffmpeg/ffmpeg" \
  uv run pyinstaller packaging/pyinstaller/parakeet.spec
   ```

  出力は `dist/` 配下に生成されます（`MimiTranscribe.app` バンドルと、サポート用の `mimitranscribe` ディレクトリが含まれます）。

4. 生成物をチェックします。

  - `dist/MimiTranscribe.app` を Finder から起動して動作確認します。
  - `dist/MimiTranscribe.app/Contents/MacOS/bin/ffmpeg` が存在し、権限が `+x` になっていることを確認します。
  - 配布前に不要なキャッシュ（`build/` 配下の生成物や `.DS_Store` 等）が混入していないかを見直してください。

### GitHub Actions での自動リリース

- 新しいタグ（`v*` で始まるセマンティックバージョン）をプッシュすると、GitHub Actions が macOS Runner 上で PyInstaller ビルドを実行し、evermeet.cx から取得した `ffmpeg` を同梱した `MimiTranscribe.app` を ZIP と DMG にまとめて生成します（現状はコード署名されないため、初回起動時に Gatekeeper に警告される点に注意してください）。

### PyInstaller セットアップのポイント

- `PARAKEET_FFMPEG_PATH` を指定しなかった場合は OS にインストールされた `ffmpeg` へフォールバックします。完全に依存レスにしたい場合は必ず同変数を設定してください。
- Apple Silicon macOS での動作を前提にしています。Intel 用に配布する場合は別途検証とコード署名が必要です。

## モデルについて

アプリケーションでは複数の音声認識 AI モデルをサポートしています：

- **Parakeet-TDT 0.6B** (`mlx-community/parakeet-tdt_ctc-0.6b-ja`) - デフォルトモデル、日本語音声認識に最適化
- **Whisper Large V3** (`mlx-community/whisper-large-v3-mlx`) - 高精度な多言語モデル
- **Whisper Large V3 Turbo** (`mlx-community/whisper-large-v3-turbo-q4`) - 高速処理用の量子化版

GUI のモデル選択から自由に切り替えられます。日本語音声には Parakeet-TDT を推奨します。多言語対応や高精度が必要な場合は Whisper モデルをご利用ください。初回起動時は選択したモデルのダウンロードに時間がかかる場合があります。