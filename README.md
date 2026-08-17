# SL3

SL3 は、小さな C 風構文を持つ自作言語と、そのコンパイラ実装です。
Python で字句解析、構文解析、コード生成を行い、現在は 8086 と Z80 をターゲットにしたアセンブリ生成に対応しています。

まだ作成途中で、リリース品質には達していません。

## 特徴

- C 風の宣言構文
- `if`、`while`、`for ... in ... do`、`return` に対応
- 配列アクセス、ビットアクセス、`MEM[...]` による直接メモリアクセスをサポート
- ターゲットに応じて 8086 または Z80 向けのアセンブリを生成

構文仕様の詳細は [doc/BNF.md](doc/BNF.md) を参照してください。

## 必要環境

- Python 3.14 以上
- uv
- ターゲット別の外部ツール

8086 を使う場合:

- `nasm`
- `alink`
- `PRINTF.obj`
- `PRINT.obj`

Z80 を使う場合:

- `dotnet`
- `bin/N80.dll`
- `bin/LK80.dll`

## セットアップ

このリポジトリは uv を前提にしています。

```powershell
uv venv --python 3.14 .venv
uv sync
.\.venv\Scripts\Activate.ps1
```

依存パッケージは現時点では特にありませんが、`uv sync` を実行して `pyproject.toml` と `uv.lock` を同期した状態にしておく運用を想定しています。

## 使い方

リポジトリのルートで実行します。

```powershell
uv run python .\src\main.py
```

引数を省略した場合は `input.lang` を入力として使います。
ファイルを指定する場合は次のように実行します。

```powershell
uv run python .\src\main.py .\test\sample.sl3
```

既に仮想環境を有効化している場合は、次の実行でも構いません。

```powershell
.\.venv\Scripts\python.exe .\src\main.py .\test\sample.sl3
```

## 設定ファイル

コンパイル対象やビルド設定は [config.json](config.json) で切り替えます。

現在の主な設定項目は次のとおりです。

- `target`: `8086` または `z80`
- `entry_point`: 8086 リンク時のエントリポイント名
- `memory_map`: 設定ファイル上には定義されている項目。現状の `src/main.py` では直接参照していないため、運用上の予約項目に近い扱いです

例:

```json
{
	"target": "8086",
	"memory_map": {
		"ROM": { "start": "0x0100" },
		"RAM": { "start": "0x2000" }
	},
	"entry_point": "main"
}
```

## 出力

ターゲットに応じて、次のファイルを生成します。

- 8086: `output.asm`、`output.obj`、`output.exe`
- Z80: `output.z80`、最終的に `main.hex`

## ターゲット別の注意

### 8086

リポジトリにある [config.json](config.json) の設定値は 8086 です。
ただし、`target` キーが設定ファイルに存在しない場合、実装上のフォールバックは Z80 になります。
生成したアセンブリは NASM でオブジェクト化し、`alink` で実行形式へリンクします。

### Z80

Z80 向けビルドでは `N80.dll` と `LK80.dll` を使います。
補助スクリプトとして [z80.cmd](z80.cmd) があります。

現状の実装では、Z80 周りは補助ファイルやビルド手順の前提がやや強いため、必要に応じてプロジェクト内のスクリプトと生成物を確認してください。

## サンプル

[test/sample.sl3](test/sample.sl3) には最小のサンプルがあります。

```sl3
int x = 10;
if (x > 0) {
		return x + 1;
} else {
		return 0;
}
```

## ディレクトリ構成

- [src](src): コンパイラ本体
- [doc](doc): 仕様メモ、BNF、設計メモ
- [test](test): サンプル入力や試験用ソース

## 補足

この README は、現在の実装に合わせて整理したものです。
言語仕様の更新が入った場合は、まず [doc/BNF.md](doc/BNF.md) を最新化し、その内容に合わせて README も更新してください。