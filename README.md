# mahjong_Application

このリポジトリは麻雀関連の小さなアプリケーションです。以下に主要なファイルとディレクトリの役割をまとめます。

**ファイル一覧と役割**

- **[mahjong_app.py](mahjong_app.py)**: デスクトップ向けのメインアプリケーション起動スクリプト（エントリポイント）。
- **[mahjong_cli.py](mahjong_cli.py)**: コマンドライン向けの操作やデバッグ用インターフェース。
- **[webapp.py](webapp.py)**: 軽量なウェブサーバー／ウェブインターフェースの起動スクリプト。
- **[requirements.txt](requirements.txt)**: Python 依存パッケージの一覧。
- **[README.md](README.md)**: 本ファイル。プロジェクトの概要と各ファイルの役割を記述します。

- **[logic/](logic/)**: ゲームロジックやアルゴリズムを格納するモジュール群。
  - **[logic/__init__.py](logic/__init__.py)**: `logic` パッケージ初期化用。
  - **[logic/shanten.py](logic/shanten.py)**: シャンテン数（和了までのテンパイ距離）計算などのアルゴリズム。

- **[models/](models/)**: ゲーム状態・データ構造を表すクラスを格納。
  - **[models/__init__.py](models/__init__.py)**: `models` パッケージ初期化用。
  - **[models/game.py](models/game.py)**: ゲーム進行（局／点数管理など）のロジック。
  - **[models/hand.py](models/hand.py)**: 手牌や鳴き、和了判定に関するデータ構造と操作。
  - **[models/player.py](models/player.py)**: プレイヤーの状態や行動を表現するクラス。
  - **[models/tile_utils.py](models/tile_utils.py)**: 牌の表現、変換、ユーティリティ関数。

- **[templates/](templates/)**: ウェブ用テンプレートを格納。
  - **[templates/index.html](templates/index.html)**: ウェブUI のエントリページ。

- **[static/](static/)**: 静的リソース（CSS、画像タイルなど）。
  - **[static/styles.css](static/styles.css)**: サイト全体のスタイル定義。
  - **[static/tiles/](static/tiles/)**: 牌画像（PNG/SVG など）を格納するディレクトリ。

- **[tools/convert_svg_to_png.ps1](tools/convert_svg_to_png.ps1)**: 牌画像関連の変換やツール類。Windows PowerShell スクリプトとして SVG→PNG 変換などを行う補助スクリプト。

その他 `__pycache__/` 等のキャッシュディレクトリは実行時に生成されるため追跡対象外です。

**起動例（VS Code ターミナル用）**

以下は Windows の PowerShell を想定した VS Code ターミナルでの実行例です。プロジェクトのルート（`mahjong_Application`）に移動してから実行してください。

- 開発用仮想環境の作成と有効化、依存関係のインストール:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

- デスクトップアプリ（エントリーポイント）を起動:

```powershell
python mahjong_app.py
```

- コマンドラインインターフェースを使う（ヘルプ表示）:

```powershell
python mahjong_cli.py --help
```

- ウェブアプリを起動（`webapp.py` に開発サーバが実装されている場合）:

```powershell
python webapp.py
# ブラウザで http://localhost:5000/ を開く（ポートは実装に依存）
```

必要に応じて各スクリプトに引数や環境変数を渡して起動してください。具体的な引数やポート番号はそれぞれのスクリプトのヘルプやソースを参照してください。
