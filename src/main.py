from __future__ import annotations
from lexer import Lexer, Token
from parser import Parser, AST
from codegen import CodeGenerator

def main(source_file: str, output_file: str) -> None:
    with open(source_file, 'r', encoding='utf-8') as f:
        source_code: str = f.read()

    # ソースコードを行リストに分割
    source_lines: list[str] = source_code.splitlines()

    print("--- 1. Lexing ---")
    lexer = Lexer(source_code)
    tokens: list[Token] = list(lexer.tokenize())

    print("--- 2. Parsing ---")
    try:
        # ソースコードの文字列をパーサーに渡す
        parser = Parser(iter(tokens), source_code)
        ast: AST = parser.parse()
    except SyntaxError as e:
        print(e) # 整形されたエラーメッセージを表示
        return # コンパイルを中止

    print("--- 3. Generating Code ---")
    generator = CodeGenerator()
    assembly_code: str = generator.generate(ast, parser.symbol_table, source_lines)

    with open(output_file, 'w') as f:
        f.write(assembly_code)
    
    print(f"\n✅ Compilation successful! Assembly written to {output_file}")


if __name__ == '__main__':
    # わざとセミコロンを忘れたエラーを含むinput.langを作成
#     with open("input.lang", "w") as f:
#         f.write("""
# int my_global_variable = 100;  // <--- セミコロンを追加

# // 3行目
# int main() {
#     return 0;
# }
# """)
    main("input.lang", "output.z80")