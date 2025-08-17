from __future__ import annotations
from symbol_table import ScopedSymbolTable, VariableSymbol
from parser import (AST, Program, VarDecl, Assignment, IfStatement, WhileStatement, 
                    FuncDecl, FuncCall, ReturnStatement, Block, ArrayAccess, BinOp, 
                    Number, VarAccess)

class CodeGenerator:
    def __init__(self) -> None:
        self.assembly_code: list[str] = []
        self.label_count: int = 0
        self.symbol_table: ScopedSymbolTable | None = None

    def generate(self, node: AST, symbol_table: ScopedSymbolTable) -> str:
        self.symbol_table = symbol_table
        self.visit(node)
        return "\n".join(self.assembly_code)

    def new_label(self) -> str:
        self.label_count += 1
        return f"L{self.label_count}"

    def visit(self, node: AST) -> None:
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: AST) -> None:
        raise NotImplementedError(f"No visit_{type(node).__name__} method")

    def visit_Program(self, node: Program) -> None:
        data_segment = ["; --- Data Segment ---"]
        assert self.symbol_table is not None
        global_vars = self.symbol_table.scopes[0]
        for name, symbol in global_vars.items():
            if isinstance(symbol, VariableSymbol):
                 size = symbol.size * 2 if symbol.is_array else 2
                 data_segment.append(f"{name}: .ds {size}")

        # 3. コードセグメントの初期化
        self.assembly_code.append("; --- Code Segment ---")
        self.assembly_code.append(".area CODE(ABS,CSEG)")
        self.assembly_code.append(".org 0x100")
        self.assembly_code.append("init: ld sp, 0xFFFE")
        self.assembly_code.append("\tcall main ; Jump to main function")
        self.assembly_code.append("\thalt")
        for child in node.children:
            self.visit(child)
        self.assembly_code.append(".end init")
        # 4. データセグメントのコードを追加
        self.assembly_code.append(";; --- Data Segment ---")
        self.assembly_code.append(".area DATA(ABS,DSEG)")
        self.assembly_code.append(".org 0x8000")
        self.assembly_code.extend(data_segment)

    def visit_VarDecl(self, node):
        # 初期化がある場合のみコードを生成
        if node.initial_value:
            var_name = node.var_node.value
            self.assembly_code.append(f"; Initialize {var_name}")
            self.visit(node.initial_value) # 式を評価 -> 結果がHLに
            self.assembly_code.append(f"\tld ({var_name}), hl")

    def visit_FuncDecl(self, node):
        func_name = node.name_token.value
        self.assembly_code.append(f"; Function Definition: {func_name}")
        self.assembly_code.append(f"{func_name}:")
        
        # --- プロローグ ---
        self.assembly_code.append("\tpush ix")
        self.assembly_code.append("\tld ix, 0")
        self.assembly_code.append("\tadd ix, sp")
        
        # ... ローカル変数分のスタック確保 (sub sp, N) ...
        
        # --- 本体 ---
        self.visit(node.body)
        
        # --- エピローグ ---
        self.assembly_code.append(f".L_RET_{func_name}:") # return文からのジャンプ先
        self.assembly_code.append("\tld sp, ix")
        self.assembly_code.append("\tpop ix")
        self.assembly_code.append("\tret")

    def visit_FuncCall(self, node):
        func_name = node.name.value
        self.assembly_code.append(f"; Function Call: {func_name}")
        # ... 引数をスタックに積む処理 ...
        self.assembly_code.append(f"\tcall {func_name}")
        # ... スタッククリーンアップ ...

    def visit_ReturnStatement(self, node):
        self.assembly_code.append("; Return statement")
        self.visit(node.expr) # 戻り値をHLに計算
        # ... 関数のエピローグへジャンプ ...


    def visit_ArrayAccess(self, node):
        # 値を読み出す場合
        # 1. 要素のアドレスをHLに計算
        self.get_element_address_in_hl(node)
        
        # 2. HLが指すアドレスから値をロード
        self.assembly_code.append("\tld e, (hl)   ; Load low byte")
        self.assembly_code.append("\tinc hl")
        self.assembly_code.append("\tld d, (hl)   ; Load high byte")
        self.assembly_code.append("\tex de, hl    ; Result in HL")
        
    def visit_Assignment(self, node):
        if isinstance(node.left, VarAccess):
            # 通常の変数への代入 (前回と同じ)
            var_name = node.left.value
            self.assembly_code.append(f"; Assign to {var_name}")
            self.visit(node.right) # 右辺の式を評価 -> 結果がHLに
            self.assembly_code.append(f"\tld ({var_name}), hl")

        elif isinstance(node.left, ArrayAccess):
            # 配列要素への代入
            self.assembly_code.append("; Assignment to array element")
            # 1. 右辺の値を評価 -> HL
            self.visit(node.right)
            # 2. 計算結果をスタックに退避
            self.assembly_code.append("\tpush hl")
            # 3. 左辺の要素アドレスを計算 -> HL
            self.get_element_address_in_hl(node.left)
            # 4. 退避した値をDEに復元
            self.assembly_code.append("\tpop de")
            # 5. DEの値をHLが指すアドレスにストア
            self.assembly_code.append("\tld (hl), e   ; Store low byte")
            self.assembly_code.append("\tinc hl")
            self.assembly_code.append("\tld (hl), d   ; Store high byte")

    def visit_VarAccess(self, node): # 追加
        var_name = node.value
        self.assembly_code.append(f"; Access var {var_name}")
        # 変数のメモリ位置から値をHLレジスタにロード
        self.assembly_code.append(f"\tld hl, ({var_name})")

    def visit_Block(self, node):
        for stmt in node.statements:
            self.visit(stmt)

    def visit_IfStatement(self, node):
        else_label = self.new_label()
        endif_label = self.new_label()
        
        self.assembly_code.append(f"; If statement")
        # 1. 条件式を評価 (visit_BinOpがZ80フラグをセットする)
        self.visit(node.condition)
        
        # 2. 条件が偽の場合にelseブロックへジャンプ
        #    node.condition.op.typeに応じてジャンプ命令を変える
        op = node.condition.op.type
        # ジャンプ命令は「条件の逆」を指定する
        jump_instruction = {
            'EQ': 'jp nz',  # 等しくない(Not Zero)ならジャンプ
            'NE': 'jp z',   # 等しい(Zero)ならジャンプ
            'LT': 'jp nc',  # キャリーなし(Not Carry, a >= b)ならジャンプ
            'GE': 'jp c',   # キャリーあり(Carry, a < b)ならジャンプ
            'GT': 'jp c',   # a > b は b < a と同じではない。要SBC後Zフラグ確認
            'LE': 'jp nz',
        }[op] # GTとLEはより複雑なため簡略化

        self.assembly_code.append(f"\t{jump_instruction}, {else_label}")
        
        # 3. thenブロックのコードを生成
        self.visit(node.then_block)
        self.assembly_code.append(f"\tjp {endif_label}") # elseをスキップ
        
        # 4. elseブロックのコードを生成
        self.assembly_code.append(f"{else_label}:")
        if node.else_block:
            self.visit(node.else_block)
            
        # 5. 終了ラベル
        self.assembly_code.append(f"{endif_label}:")

    def visit_WhileStatement(self, node):
        loop_start_label = self.new_label()
        loop_end_label = self.new_label()
        
        self.assembly_code.append(f"; While statement")
        
        # 1. ループ開始ラベルを配置
        self.assembly_code.append(f"{loop_start_label}:")
        
        # 2. 条件式を評価
        self.visit(node.condition)
        
        # 3. 条件が偽の場合にループの終わりへジャンプ
        op = node.condition.op.type
        jump_instruction = {
            'EQ': 'jp nz',  # Not Zero -> not equal
            'NE': 'jp z',   # Zero -> equal
            'LT': 'jp nc',  # Not Carry -> greater or equal
            'GE': 'jp c',   # Carry -> less than
            # GT, LEはより複雑なため簡略化
        }[op]
        self.assembly_code.append(f"\t{jump_instruction}, {loop_end_label}")
        
        # 4. ループ本体のコードを生成
        self.visit(node.body)
        
        # 5. ループの先頭に戻る無条件ジャンプ
        self.assembly_code.append(f"\tjp {loop_start_label}")
        
        # 6. ループ終了ラベルを配置
        self.assembly_code.append(f"{loop_end_label}:")


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

        # 比較演算子の処理を追加
        if op_type in ('EQ', 'NE', 'LT', 'GT', 'LE', 'GE'):
            self.assembly_code.append(f"; Begin CompareOp {op_type}")
            self.visit(node.right)
            self.assembly_code.append("\tpush hl")
            self.visit(node.left)
            self.assembly_code.append("\tpop de")
            self.assembly_code.append("\tand a      ; Clear carry flag for subtraction")
            self.assembly_code.append("\tsbc hl, de ; Compare HL and DE (HL - DE)")
            # この結果、ZフラグとCフラグがセットされる
        # 4. 演算を実行 (結果はHLに格納)
        elif op_type == 'PLUS':
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

    def get_element_address_in_hl(self, node):
        """配列要素のアドレスを計算してHLレジスタに入れる"""
        # (このメソッドは visit_ArrayAccess と visit_Assignment で使用)
        var_name = node.var_node.value
        symbol = self.symbol_table.lookup(var_name)
        
        self.assembly_code.append(f"; Calculate address for {var_name}[i]")
        # 1. インデックス`i`の値を評価 -> HL
        self.visit(node.index_expr)
        
        # 2. 要素サイズを乗算 (i * element_size)
        #    int (2 bytes) の場合は HL = HL * 2 -> ADD HL, HL
        if symbol.type.value == 'int':
            self.assembly_code.append("\tadd hl, hl ; index *= 2")
        
        # 3. ベースアドレスと加算
        #    HL = (base_addr) + (i * size)
        self.assembly_code.append("\tld de, (ix-...) ; Load base address offset")
        self.assembly_code.append("\tadd hl, de     ; Add base address to offset")
        # 注: 実際には、IXからのオフセットをシンボルテーブルで管理し、
        #     IX + 計算済みオフセット のアドレスをHLに入れる必要がある。
        #     ここでは概念的なコードを示します。
        
