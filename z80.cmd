.\bin\asez80.exe -l output.z80

@echo off
echo --- Assembling Files ---

REM コンパイラが出力したメインプログラムをアセンブル
.\bin\asz80 -o -l -s output.z80

REM ランタイムライブラリをアセンブル
@REM .\bin\asz80 -o -l -s .\src\runtime.asm

echo.
echo --- Linking Files ---

REM アセンブルして生成された.relファイルをリンクし、実行ファイル(.com)を生成
@REM .\bin\aslink -m -i output.rel .\src\runtime.rel
.\bin\aslink -m -i output.rel

echo.
echo --- Cleanup ---

REM 不要になった中間ファイルを削除
del *.rel src\*.rel
rem del *.lst src\*.lst
rem del *.sym src\*.sym
