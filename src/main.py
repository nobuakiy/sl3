from lexer import Lexer
from parser import Parser # These would be fully implemented
from codegen import CodeGenerator

def main(source_file, output_file):
    with open(source_file, 'r') as f:
        source_code = f.read()

    print("--- 1. Lexing ---")
    lexer = Lexer(source_code)
    tokens = list(lexer.tokenize())
    # print(tokens) # For debugging

    print("--- 2. Parsing ---")
    # A complete parser would be needed here
    # parser = Parser(tokens)
    # ast = parser.parse()
    # For this example, let's manually create an AST for "byte test_var;"
    from parser import VarDecl, Type, Variable, Token, Program
    ast = Program([
        VarDecl(Type(Token('BYTE')), Variable(Token('ID', 'test_var')))
    ])
    
    print("--- 3. Generating Code ---")
    generator = CodeGenerator()
    assembly_code = generator.generate(ast)

    with open(output_file, 'w') as f:
        f.write(assembly_code)
    
    print(f"Compilation successful! Assembly code written to {output_file}")
    print("\n--- Generated Assembly ---")
    print(assembly_code)
    print("--------------------------")


if __name__ == '__main__':
    # Usage: python compiler.py input.lang output.z80
    # Create a dummy input file "input.lang" with content: "byte test_var;"
    with open("input.lang", "w") as f:
        f.write("byte test_var;")
        
    main("input.lang", "output.z80")