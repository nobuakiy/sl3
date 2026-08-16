
import json
import subprocess
import os
import sys
from lexer import Lexer
from parser import Parser

# --- 動的インポートのための準備 ---
CodeGenerator = None

def main():
    # --- 1. 設定ファイルの読み込み ---
    config_file = 'config.json'
    with open(config_file, 'r') as f:
        config = json.load(f)

    # --- 入力ファイルの指定（コマンドライン引数） ---
    if len(sys.argv) > 1:
        source_file = sys.argv[1]
    else:
        source_file = "input.lang"

    # --- 2. ターゲットに応じたCodeGeneratorの動的インポート ---
    target = config.get("target", "z80").lower() # デフォルトはz80
    if target == 'z80':
        from codegen_z80 import CodeGenerator
        output_asm_file = "output.z80"
        print(f"--- Target: Z80 ---")
    elif target == '8086':
        from codegen_8086 import CodeGenerator
        output_asm_file = "output.asm"
        print(f"--- Target: 8086 ---")
    else:
        raise ValueError(f"Unsupported target in {config_file}: {target}")

    # --- 3. コンパイル処理 (これまでと同じ) ---
    with open(source_file, 'r', encoding='utf-8') as f:
        source_code = f.read()
    source_lines = source_code.splitlines()

    lexer = Lexer(source_code)
    tokens = list(lexer.tokenize())
    parser = Parser(iter(tokens), source_code)
    ast = parser.parse()

    generator = CodeGenerator()
    assembly_code = generator.generate(ast, parser.symbol_table, source_lines)

    with open(output_asm_file, 'w') as f:
        f.write(assembly_code)

    print(f"✅ Assembly code generated: {output_asm_file}")

    # --- 4. ターゲットに応じたビルド処理 ---
    print(f"--- Building for {target.upper()} ---")
    if target == 'z80':
        # Z80用のビルドコマンド (asz80/aslink)
        params = f"dotnet .\\bin\\N80.dll {output_asm_file} .\\build\\main.rel -l -ie utf-8 -le utf-8 -se shift_jis".split(" ")
        subprocess.run(params, check=True)
        # ... aslinkのコマンド ...
        params = f"dotnet .\\bin\\LK80.dll .\\build\\main.rel .\\build\\runtime.rel -of hex -y map.txt -yf equs -o main.hex".split(" ")
        subprocess.run(params, check=True)
    elif target == '8086':
        # 8086用のビルドコマンド (nasm/alink)
        output_obj_file = "output.obj"
        output_exe_file = "output.exe"
        subprocess.run(["nasm", "-f", "obj", output_asm_file, "-o", output_obj_file], check=True)
        # 複数のライブラリファイルもここで指定できる
        link_args = ["alink", "-oEXE", output_obj_file, "PRINTF.obj", "PRINT.obj", "-entry", config["entry_point"]]
        subprocess.run(link_args, check=True)

    print(f"✅ Build successful! Executable created.")


if __name__ == '__main__':
    try:
        main()
    except (SyntaxError, ValueError, FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"\n--- ERROR ---\n{e}")