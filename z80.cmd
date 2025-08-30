@echo off
echo --- Assembling Files ---

dotnet .\bin\N80.dll output.z80 .\build\output.rel -l
dotnet .\bin\N80.dll .\src\runtime.asm .\build\runtime.rel -l
dotnet .\bin\LK80.dll .\build\output.rel .\src\runtime.rel -of hex -y .\build\map.txt -yf equs -o .\build\output.hex

echo --- Cleanup ---

REM 不要になった中間ファイルを削除
del *.rel src\*.rel
rem del *.lst src\*.lst
rem del *.sym src\*.sym
