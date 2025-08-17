from lexer import Lexer
from parser import Parser # 上記で拡張したもの
from codegen import CodeGenerator # 上記で拡張したもの

def main(source_file, output_file):
    with open(source_file, 'r') as f: source_code = f.read()

    print("--- 1. Lexing ---")
    lexer = Lexer(source_code)
    tokens = list(lexer.tokenize())

    print("--- 2. Parsing ---")
    parser = Parser(tokens)
    ast = parser.parse()
    
    print("--- 3. Generating Code ---")
    generator = CodeGenerator()
    assembly_code = generator.generate(ast)

    with open(output_file, 'w') as f: f.write(assembly_code)
    
    print(f"✅ Compilation successful! Assembly written to {output_file}")
    print("\n--- Generated Assembly ---")
    print(assembly_code)
    print("--------------------------")

if __name__ == '__main__':
    # テスト用のソースファイルを作成
    with open("input.lang", "w") as f:
        f.write("""
        int data[3];
        data[0] = 10;
        data[1] = 20;
        data[2] = data[0] + data[1];
        """)

    main("input.lang", "output.z80")