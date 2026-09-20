# pygame-ce + SDL3 試験構成（macOS）

macOS 27でマスコンが認識されない問題を調査した際の構成です。
正式なSDL3移行ではありません。**ボタンの割り当ては未調整です。**
ボタンを押すと従来と異なるキーが送信される可能性があります。

## 再現手順

必要なもの: macOS、Xcode Command Line Tools（Cコンパイラ）、Git、uv、インターネット接続。

```bash
bash experiments/sdl3/build.sh
bash experiments/sdl3/run.sh --verbose
```

ビルド成果物・専用Python環境はGit管理対象外の `build/sdl3-experiment/` に作成します。
保存場所を変える場合は、両コマンドに同じ `ZUIKI_SDL3_ROOT` を指定してください。
ビルド後に保存場所を移動すると、ライブラリの参照が壊れる可能性があります。
MFIを有効・無効で比較する場合は、起動時に `SDL_JOYSTICK_MFI=1` または `0` を指定します。
スクリプト自体はMFI設定を変更しません。

通常の `uv run main.py` はSDL2版pygame-ceを使用します。
この試験構成は通常の `.venv` や配布アプリのビルドに組み込みません。

## 固定した構成と補正

- SDL 3.4.16（公式ソースのSHA-256をビルド時に照合）
- pygame-ce 3.0.0.dev1、コミット `f2e3f55e5f84a56044583e0e147618a06ef7ddb7`
- Python 3.13、CMake 4.1.0
- pygame-ceの画像・音声・フォント・MIDI拡張は省略。無効化オプションが拡張のビルド条件に反映されない部分を、専用ソースコピーに `patch_build.py` で補正
- SDL3のJoystick引数はインスタンスID。接続イベントの `device_index=-1` をそのまま渡さず、`launch.py` でSDL3からID一覧を取得して登録

## 実機での確認結果と未検証事項

- SDL3単体、pygame-ce + SDL3の両方で、MFI無効化を指定せず認識成功
- ZUIKI MasCon for Nintendo Switch (`33dd:0002`) が6軸・16ボタン・十字キー1個として認識
- ハンドルのノッチ表示は利用者の目視では正常。全段数の自動検証は未実施
- ボタンの割り当てはSDL2版から大幅に変化し、未調整
- 抜き差し、複数コントローラー、配布用パッケージは未検証
- SDL3で認識できたことは、AppleのGCController側の不整合が修正された証明ではない

アプリを閉じると試験を終了できます。通常起動へ戻すには `uv run main.py` を使用します。
