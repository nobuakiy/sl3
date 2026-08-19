<#
.SYNOPSIS
    SL3 が生成した main.hex (Z80) を CP/M 環境(RunCPM)で実際に実行する。

.DESCRIPTION
    アセンブル/リンク(dotnet + N80.dll/LK80.dll)はこのスクリプトの範囲外。
    事前に z80.cmd などでビルド済みの main.hex を指定すること。

.EXAMPLE
    .\docker\run-z80.ps1
    .\docker\run-z80.ps1 .\build\output.hex
#>
param(
    [string]$HexFile = "main.hex",
    [string]$ComName = "SL3PROG"
)

$ErrorActionPreference = "Stop"

$hexPath = Resolve-Path $HexFile
$hexDir = Split-Path -Parent $hexPath
$hexName = Split-Path -Leaf $hexPath

docker build -t sl3-z80-cpm "$PSScriptRoot\z80-cpm"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

docker run --rm -v "${hexDir}:/src:ro" sl3-z80-cpm "/src/$hexName" $ComName
