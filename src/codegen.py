# --- codegen.py ---
from symbol_table import SymbolTable, VariableSymbol

class CodeGenerator:
    def __init__(self):
        self.assembly_code = []
        self.symbol_table = SymbolTable()
        self.label_count = 0

    def new_label(self):
        self.label_count += 1
        return f"L{self.label_count}"

    def generate(self, node):
        self.visit(node)
        return "\n".join(self.assembly_code)

    def visit(self, node):
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        raise NotImplementedError(f"No visit_{type(node).__name__} method for {type(node).__name__}")

    def visit_Program(self, node):
        data_segment = []
        code_segment = []
        
        # 1. まず全てのグローバル変数の領域を確保
        for stmt in node.children:
            if type(stmt).__name__ == 'VarDecl':
                var_name = stmt.var_node.value
                data_segment.append(f"{var_name}: .ds 2 ; int is 2 bytes")
        
        # 2. 次に実行コードを生成
        for stmt in node.children:
            # visitメソッドはコードを self.assembly_code に追加するので、一時的にリセット
            self.assembly_code = []
            self.visit(stmt)
            code_segment.extend(self.assembly_code)

        # 3. 最後に全体を結合
        self.assembly_code = [".org 0x100", "init:", "ld sp, 0xFFFE"]
        self.assembly_code.append(";; --- Data Segment ---")
        self.assembly_code.extend(data_segment)
        self.assembly_code.append(";; --- Code Segment ---")
        self.assembly_code.extend(code_segment)
        self.assembly_code.extend(["halt", ".end init"])

    def visit_VarDecl(self, node):
        # 初期化がある場合のみコードを生成
        if node.initial_value:
            var_name = node.var_node.value
            self.assembly_code.append(f"; Initialize {var_name}")
            self.visit(node.initial_value) # 式を評価 -> 結果がHLに
            self.assembly_code.append(f"\tld ({var_name}), hl")

    def visit_Assignment(self, node):
        var_name = node.left.value
        self.assembly_code.append(f"; Assign to {var_name}")
        self.visit(node.right) # 右辺の式を評価 -> 結果がHLに
        self.assembly_code.append(f"\tld ({var_name}), hl")

    def visit_VarAccess(self, node): # 追加
        var_name = node.value
        self.assembly_code.append(f"; Access var {var_name}")
        # 変数のメモリ位置から値をHLレジスタにロード
        self.assembly_code.append(f"\tld hl, ({var_name})")

    # ... (visit_Number, visit_BinOpは前回と同じ) ...

    # --- Expression Code Generation (追加) ---
    def visit_Number(self, node):
        self.assembly_code.append(f"; Load number {node.value}")
        self.assembly_code.append(f"\tld hl, {node.value}")

    def visit_BinOp(self, node):
        op_type = node.op.type
        self.assembly_code.append(f"; Begin BinOp {op_type}")

        # 1. 右辺 (RHS) を評価し、結果をスタックに退避
        self.visit(node.right)
        self.assembly_code.append("\tpush hl")
        
        # 2. 左辺 (LHS) を評価 (結果はHLに残る)
        self.visit(node.left)
        
        # 3. 退避した右辺の値をDEレジスタに復元
        self.assembly_code.append("\tpop de")

        # 4. 演算を実行 (結果はHLに格納)
        if op_type == 'PLUS':
            self.assembly_code.append("\tadd hl, de ; HL = HL + DE")
        elif op_type == 'MINUS':
            # Z80には16bit減算がないので `SBC` を使う
            self.assembly_code.append("\tand a ; Clear carry flag")
            self.assembly_code.append("\tsbc hl, de ; HL = HL - DE")
        elif op_type == 'MUL':
            # 乗算は複雑なので、ここでは単純な加算で代用 (本来はサブルーチンを呼ぶ)
            self.assembly_code.append("; Multiplication (placeholder)")
            self.assembly_code.append("\t; TODO: Implement multiplication routine")
        else:
            raise NotImplementedError(f"Operator {op_type} not implemented")
        
        self.assembly_code.append(f"; End BinOp {op_type}")

    # --- Code Generation for specific features ---
    
    # Example: How `a.3 = 1;` might be compiled
    def visit_BitAssignment(self, node): # Assuming a BitAssignment AST node exists
        # node.variable -> the variable 'a'
        # node.bit_number -> the integer 3
        # node.value -> the value to assign (0 or 1)
        
        var_name = node.variable.value
        bit_num = node.bit_number
        
        # Assume 'a' is a byte variable at a known memory address
        self.assembly_code.append(f"; Bit set for {var_name}.{bit_num}")
        self.assembly_code.append(f"\tld a, ({var_name}) ; Load value of 'a' into accumulator")
        if node.value == 1:
            self.assembly_code.append(f"\tset {bit_num}, a       ; Set bit {bit_num}")
        else:
            self.assembly_code.append(f"\tres {bit_num}, a       ; Reset bit {bit_num}")
        self.assembly_code.append(f"\tld ({var_name}), a ; Store it back")
        
    # Example: How `MEM[0x8000] = 0x21;` might be compiled
    def visit_MemAssignment(self, node): # Assuming a MemAssignment AST node exists
        # node.address -> the expression for the address (e.g., 0x8000)
        # node.value -> the expression for the value (e.g., 0x21)
        
        # 1. Evaluate value and put it in A (for byte)
        # self.visit(node.value) -> result would be in register A
        self.assembly_code.append(f"\tld a, {hex(node.value.integer)}")
        
        # 2. Evaluate address and put it in HL
        # self.visit(node.address) -> result would be in register HL
        self.assembly_code.append(f"\tld hl, {hex(node.address.integer)}")

        # 3. Store A at the address pointed to by HL
        self.assembly_code.append(f"\tld (hl), a ; MEM[addr] = value")