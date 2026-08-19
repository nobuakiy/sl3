<#
.SYNOPSIS
    SL3 が生成した output.exe (8086) を実際の DOS 環境(DOSBox)で実行する。

.DESCRIPTION
    アセンブル/リンク(nasm + alink + PRINTF.obj/PRINT.obj)はこのスクリプトの範囲外。
    事前にビルド済みの output.exe を指定すること。標準出力(INT 21h)の内容を表示する。

.EXAMPLE
    .\docker\run-8086.ps1
    .\docker\run-8086.ps1 .\output.exe
#>
param(
    [string]$ExeFile = "output.exe"
)

$ErrorActionPreference = "Stop"

$exePath = Resolve-Path $ExeFile
$exeDir = Split-Path -Parent $exePath
$exeName = Split-Path -Leaf $exePath

docker build -t sl3-dosbox-8086 "$PSScriptRoot\dosbox-8086"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

docker run --rm -v "${exeDir}:/src" sl3-dosbox-8086 $exeName
