from __future__ import annotations
from symbol_table import ScopedSymbolTable, VariableSymbol, Symbol
from parser import (AST, Program, VarDecl, Assignment, IfStatement, WhileStatement,
                    FuncDecl, FuncCall, ReturnStatement, Block, ArrayAccess, BinOp,
                    Number, VarAccess, MemAccess, UnaryOp, StringLiteral, ForInStatement,
                    BitAccess, MethodCall, PortAccess)

class CodeGenerator:
    def __init__(self) -> None:
        self.assembly_code: list[str] = []
        self.label_count: int = 0
        self.symbol_table: ScopedSymbolTable | None = None
        self.source_lines: list[str] = []
        self.last_commented_line: int = -1 # コメントの重複出力を防ぐ
        self.string_literals: dict[str, str] = {} # ★ 文字列とラベルを管理する辞書


    def generate(self, node: AST, symbol_table: ScopedSymbolTable, source_lines: list[str]) -> str:
        self.symbol_table = symbol_table
        self.source_lines = source_lines # ★ ソース行リストを保持
        self.visit(node)
        return "\n".join(self.assembly_code)

    def _get_start_line(self, node: AST) -> int:
        """ASTノードからソースの開始行番号を取得するヘルパー"""
        if hasattr(node, 'token'):
            return node.token.line
        if hasattr(node, 'name_token'):
            return node.name_token.line
        if hasattr(node, 'start_token'): # 今後、明示的に開始トークンを持たせる場合
            return node.start_token.line
        # 再帰的に左端のトークンを探す
        if hasattr(node, 'left'):
            return self._get_start_line(node.left)
        if hasattr(node, 'var_node'):
            return self._get_start_line(node.var_node)
        # フォールバック
        return -1

    def _emit_source_comment(self, node: AST) -> None:
        """ASTノードに対応するソース行をコメントとして出力する"""
        line_num = self._get_start_line(node)
        if line_num != -1 and line_num != self.last_commented_line:
            # 行番号は1から始まるが、リストのインデックスは0から始まる
            source_line = self.source_lines[line_num - 1].strip()
            if source_line: # 空行はコメントしない
                self.assembly_code.append(f"\n; {source_line}")
                self.last_commented_line = line_num

    def _get_string_label(self, str_value: str) -> str:
        """文字列に対応するラベルを取得。なければ新しいラベルを作成する"""
        if str_value in self.string_literals:
            return self.string_literals[str_value]

        label = f".L_STR{len(self.string_literals)}"
        self.string_literals[str_value] = label
        return label

    def new_label(self) -> str:
        self.label_count += 1
        return f"L{self.label_count}"

    def get_symbol_size(self, symbol: Symbol) -> int:
        """シンボルの型からサイズ(バイト)を取得する"""
        if isinstance(symbol, VariableSymbol):
            if symbol.type.value == 'int': return 2
            if symbol.type.value == 'byte': return 1
        return 2 # 不明な場合はデフォルトでint

    def _get_element_address_in_hl(self, node: ArrayAccess) -> None:
        """配列要素の最終的なメモリアドレスを計算し、HLレジスタに格納する"""
        var_name = node.var_node.value
        symbol = self.symbol_table.lookup(var_name)

        if not symbol or not isinstance(symbol, VariableSymbol) or not symbol.is_array:
            self._error(f"'{var_name}' is not a valid array", node.var_node.token)

        self.assembly_code.append(f"; Calculate address for {var_name}[i]")

        # 1. インデックス値を評価し、要素サイズを乗算 -> 結果はHL
        self.visit(node.index_expr)
        if self.get_symbol_size(symbol) == 2: # int
            self.assembly_code.append("\tadd hl, hl ; index *= 2")

        # 2. 配列のベースアドレスを計算し、インデックスオフセットと加算
        if symbol.scope == 'global':
            self.assembly_code.append(f"\tld de, {var_name} ; Load global array base address")
            self.assembly_code.append("\tadd hl, de")
        else: # local
            # HL = (IX + base_offset) + (scaled_index)
            # まず IX を DE にコピー
            self.assembly_code.append("\tpush ix")
            self.assembly_code.append("\tpop de")
            # HL (scaled_index) と DE (IX) を加算
            self.assembly_code.append("\tadd hl, de")
            # 最後に配列のベースオフセットを加算
            self.assembly_code.append(f"\tld de, {symbol.offset}")
            self.assembly_code.append("\tadd hl, de")

    def visit(self, node: AST) -> None:
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: AST) -> None:
        raise NotImplementedError(f"No visit_{type(node).__name__} method")

    def visit_Program(self, node: Program) -> None:
        assert self.symbol_table is not None

        # 1. トップレベルのASTノードを分類する
        global_inits = []
        func_decls = []
        global_data_defs = []

        for child in node.children:
            if isinstance(child, VarDecl):
                # .ds定義を作成
                symbol = self.symbol_table.lookup(child.var_node.value)
                element_size = self.get_symbol_size(symbol)
                size = child.size * element_size if child.is_array else element_size
                global_data_defs.append(f"{child.var_node.value}: .ds {size}")
                # 初期化子があれば、実行コードとしてリストに追加
                if child.initial_value:
                    global_inits.append(child)
            elif isinstance(child, FuncDecl):
                func_decls.append(child)

        # 3. コードセグメントの初期化
        self.assembly_code.append("; --- Code Segment ---")
        self.assembly_code.append(".area CODE(ABS,CSEG)")

        # 2. 正しい順序でアセンブリコードを構築する
        self.assembly_code.append(".org 0x100")
        self.assembly_code.append("init:")
        self.assembly_code.append("\tld sp, 0xFFFE")

        if global_inits:
            self.assembly_code.append("\n; --- Global Variable Initializations ---")
            for var_decl_node in global_inits:
                self.visit(var_decl_node)

        self.assembly_code.append("\n; --- Start Program ---")
        self.assembly_code.append("\tcall main")
        self.assembly_code.append("\thalt")

        self.assembly_code.append("\n; --- include runtime ---")
        self.assembly_code.append("\t.include /src\\runtime.asm/")

        self.assembly_code.append("\n; --- Functions ---")
        for func_decl_node in func_decls:
            self.visit(func_decl_node)

        # ★ visit_Programの最後に文字列リテラルのデータセグメントを追加
        if self.string_literals:
            self.assembly_code.append("\n; --- String Literals ---")
            for str_val, label in self.string_literals.items():
                self.assembly_code.append(f"{label}:")
                byte_array = ", ".join(str(b) for b in str_val.encode('cp932'))
                self.assembly_code.append(f"\t.db {byte_array}, 0 ; \"{str_val}\"")

                # # ★ 文字列がASCII印字可能文字のみで構成されているかチェック
                # is_ascii_printable = all(32 <= ord(c) < 127 for c in str_val)

                # if is_ascii_printable:
                #     # ASCIIのみなら、アセンブラの文字列形式で出力
                #     # アセンブラによって区切り文字が違うため、ここでは ' を使用
                #     # 文字列内の ' はエスケープする必要がある
                #     escaped_str = str_val.replace("'", "''")
                #     self.assembly_code.append(f"\t.db '{escaped_str}', 0")
                # else:
                    # マルチバイト文字を含むなら、UTF-8バイト列で出力
                    # byte_array = ", ".join(str(b) for b in str_val.encode('utf-8'))
                    # self.assembly_code.append(f"\t.db {byte_array}, 0 ; \"{str_val}\"")


        self.assembly_code.append("\n; --- Data Segment ---")
        self.assembly_code.append(".area DATA(ABS,DSEG)")
        self.assembly_code.append(".org 0x8000")
        self.assembly_code.extend(global_data_defs)

        self.assembly_code.append("\n.end init")


    def visit_VarDecl(self, node):
        self._emit_source_comment(node)  # ソースコードの行をコメントとして出力
        # 初期化がある場合のみコードを生成
        if node.initial_value:
            var_name = node.var_node.value
            self.assembly_code.append(f"; Initialize {var_name}")
            # 代入のロジックはAssignmentと共通なので、Assignmentノードを模倣してvisitする
            # これによりコードの重複を避ける
            assignment_node = Assignment(left=VarAccess(node.var_node), right=node.initial_value)
            self.visit(assignment_node)

    def visit_FuncDecl(self, node: FuncDecl) -> None:
        func_name = node.name_token.value
        self.assembly_code.append(f"\n; --- Function: {func_name} ---")
        self.assembly_code.append(f"{func_name}:")

        # --- プロローグ ---
        self.assembly_code.append("\tpush ix")
        self.assembly_code.append("\tld ix, 0")
        self.assembly_code.append("\tadd ix, sp")

        # ★ ASTノードからローカル変数の情報を取得し、スタック領域を確保
        local_var_size = 0
        local_var_offset = 0
        for symbol in node.local_symbols.values():
            if isinstance(symbol, VariableSymbol):
                size = self.get_symbol_size(symbol)
                local_var_size += size
                local_var_offset -= size
                symbol.offset = local_var_offset # オフセット情報をシンボルに記録

        if local_var_size > 0:
            self.assembly_code.append(f"\tld hl, {local_var_size}")
            self.assembly_code.append("\tand a") # clear carry
            self.assembly_code.append("\tsbc hl, sp")
            self.assembly_code.append("\tld sp, hl ; Allocate space for local vars")

        # ★ コード生成の前に、現在のスコープにローカル変数を追加
        self.symbol_table.enter_scope()
        for name, symbol in node.local_symbols.items():
            self.symbol_table.define(symbol)

        # ★ 現在処理中の関数名を保存しておく
        self.current_function_name = func_name

        # --- 本体 ---
        self.visit(node.body)

        # --- エピローグ ---
        # ★ 予測可能なラベル名（.L_RET_{関数名}）を使用
        self.assembly_code.append(f".L_RET_{func_name}:")
        self.assembly_code.append("\tld sp, ix")
        self.assembly_code.append("\tpop ix")
        self.assembly_code.append("\tret")

        self.symbol_table.leave_scope()
        self.current_function_name = None # 処理が終わったらクリア

    def visit_FuncCall(self, node: FuncCall) -> None:
        # ★ node.name.value を node.name_token.value に修正
        func_name = node.name_token.value
        self.assembly_code.append(f"; Function Call: {func_name}")

        # 引数を右から左へスタックに積む
        if node.args:
            for arg_node in reversed(node.args):
                self.visit(arg_node)
                self.assembly_code.append("\tpush hl")

        self.assembly_code.append(f"\tcall {func_name}")

        # 呼び出し側がスタックをクリーンアップ
        arg_size = len(node.args) * 2 # 引数はint(2byte)と仮定
        if arg_size > 0:
            self.assembly_code.append(f"\tld hl, {arg_size}")
            self.assembly_code.append("\tadd hl, sp")
            self.assembly_code.append("\tld sp, hl")

    def visit_ReturnStatement(self, node):
        self._emit_source_comment(node)  # ソースコードの行をコメントとして出力
        self.assembly_code.append("; Return statement")
        self.visit(node.expr) # 戻り値をHLに計算
        # ... 関数のエピローグへジャンプ ...


    def visit_ArrayAccess(self, node: ArrayAccess) -> None:
        self._emit_source_comment(node)
        # 1. 要素のアドレスをHLに計算
        self._get_element_address_in_hl(node)

        # 2. HLが指すアドレスから値をロード
        symbol = self.symbol_table.lookup(node.var_node.value)
        self.assembly_code.append("; Load value from calculated address")
        if self.get_symbol_size(symbol) == 2: # int
            self.assembly_code.append("\tld e, (hl)")
            self.assembly_code.append("\tinc hl")
            self.assembly_code.append("\tld d, (hl)")
            self.assembly_code.append("\tex de, hl")
        else: # byte
            self.assembly_code.append("\tld a, (hl)")
            self.assembly_code.append("\tld h, 0")
            self.assembly_code.append("\tld l, a")


    def visit_VarAccess(self, node: VarAccess) -> None:
        var_name = node.value
        assert self.symbol_table is not None
        symbol = self.symbol_table.lookup(var_name)
        if not symbol or not isinstance(symbol, VariableSymbol):
            self._error(f"Undefined variable '{var_name}'", node.token)

        self.assembly_code.append(f"; Access var '{var_name}' ({symbol.scope})")

        if symbol.scope == 'global':
            if self.get_symbol_size(symbol) == 2:
                self.assembly_code.append(f"\tld hl, ({var_name})")
            else:
                self.assembly_code.append(f"\tld a, ({var_name})")
                self.assembly_code.append("\tld h, 0")
                self.assembly_code.append(f"\tld l, a  ; Promote byte to int in HL")
        else:  # local
            # --- ★ ここからが新しい高速なロジック ---
            offset = symbol.offset
            self.assembly_code.append(f"; Access local var at (ix{offset:+})")
            if self.get_symbol_size(symbol) == 2: # int
                # int型 (2バイト) の場合
                self.assembly_code.append(f"\tld e, (ix{offset:+})   ; Load low byte")
                self.assembly_code.append(f"\tld d, (ix{offset+1:+}) ; Load high byte")
                self.assembly_code.append(f"\tex de, hl")
            else: # byte
                self.assembly_code.append(f"\tld a, (ix{offset:+})")
                self.assembly_code.append(f"\tld h, 0")
                self.assembly_code.append(f"\tld l, a")

    def visit_BitAccess(self, node: BitAccess) -> None:
        """ビットを読み出し(テストし)、結果(0か1)をHLに格納する"""
        self._emit_source_comment(node)
        var_name = node.var_node.value
        bit_num = node.bit_num_token.value
        symbol = self.symbol_table.lookup(var_name)

        self.assembly_code.append(f"; Test bit {bit_num} of '{var_name}'")
        # 変数の下位バイトをAレジスタにロード
        if symbol.scope == 'global':
            self.assembly_code.append(f"\tld a, ({var_name})")
        else: # local
            self.assembly_code.append(f"\tld a, (ix{symbol.offset:+})")

        # BIT命令でテスト
        self.assembly_code.append(f"\tbit {bit_num}, a")
        # 結果(Zフラグ)を数値に変換してHLに入れる
        self.assembly_code.append("\tld hl, 0")
        self.assembly_code.append(f"\tjp z, .L_BIT_ZERO{self.label_count}") # Zフラグがセット(ビットが0)ならジャンプ
        self.assembly_code.append("\tld hl, 1")
        self.assembly_code.append(f".L_BIT_ZERO{self.label_count}:")
        self.label_count += 1

    def visit_PortAccess(self, node: PortAccess) -> None:
        """ポートから1バイト読み出し、結果をHLに格納する"""
        self._emit_source_comment(node)
        # 簡単のため、アドレスはコンパイル時定数と仮定
        port_addr = node.address_expr.value
        self.assembly_code.append(f"; Read from PORT[{port_addr}]")
        self.assembly_code.append(f"\tin a, ({port_addr})")
        self.assembly_code.append("\tld h, 0")
        self.assembly_code.append("\tld l, a ; Promote byte to int in HL")

    def visit_Assignment(self, node: Assignment) -> None:
        self._emit_source_comment(node)

        if isinstance(node.left, PortAccess):
            # --- ポートへの代入: PORT[addr] = value ---
            port_addr = node.left.address_expr.value
            self.visit(node.right) # 右辺を評価 -> HL
            self.assembly_code.append(f"; Write to PORT[{port_addr}]")
            self.assembly_code.append("\tld a, l ; Truncate to 8-bit")
            self.assembly_code.append(f"\tout ({port_addr}), a")

        elif isinstance(node.left, BitAccess) and isinstance(node.left.var_node, PortAccess):
            # --- ポートのビットへの代入: PORT[addr].bit = value ---
            port_addr = node.left.var_node.address_expr.value
            bit_num = node.left.bit_num_token.value
            value = node.right.value

            self.assembly_code.append(f"; Read-Modify-Write to PORT[{port_addr}].{bit_num}")
            # 1. Read
            self.assembly_code.append(f"\tin a, ({port_addr})")
            # 2. Modify
            if value == 1:
                self.assembly_code.append(f"\tset {bit_num}, a")
            else:
                self.assembly_code.append(f"\tres {bit_num}, a")
            # 3. Write
            self.assembly_code.append(f"\tout ({port_addr}), a")

        elif isinstance(node.left, BitAccess):
            # --- ビットへの代入 ---
            var_name = node.left.var_node.value
            bit_num = node.left.bit_num_token.value
            symbol = self.symbol_table.lookup(var_name)

            self.assembly_code.append(f"; Assign to bit {bit_num} of '{var_name}'")
            # 右辺の値(0か1)を評価
            # (簡単のため、ここではリテラル0か1のみをサポート)
            value = node.right.value

            # 変数の下位バイトをAレジスタにロード
            if symbol.scope == 'global':
                self.assembly_code.append(f"\tld a, ({var_name})")
            else: # local
                self.assembly_code.append(f"\tld a, (ix{symbol.offset:+})")

            # SETまたはRES命令
            if value == 1:
                self.assembly_code.append(f"\tset {bit_num}, a")
            else:
                self.assembly_code.append(f"\tres {bit_num}, a")

            # 結果をメモリに書き戻す
            if symbol.scope == 'global':
                self.assembly_code.append(f"\tld ({var_name}), a")
            else: # local
                self.assembly_code.append(f"\tld (ix{symbol.offset:+}), a")

        else:
            if isinstance(node.left, MemAccess):
                # MEM[addr] = value の場合
                # 1. 右辺の値を評価 -> HL
                self.visit(node.right)
                self.assembly_code.append("\tpush hl")
                # 2. 左辺のアドレス式を評価 -> HL
                self.visit(node.left.address_expr)
                self.assembly_code.append("\tpop de     ; Value to store in DE")
                # 3. DEの値をHLが指すアドレスにストア
                self.assembly_code.append("\tld (hl), e")
                self.assembly_code.append("\tinc hl")
                self.assembly_code.append("\tld (hl), d")
            # ... (他の代入処理)

            # 1. 右辺の式を評価 -> 結果はHLに入る
            self.visit(node.right)

            # 2. 左辺の変数を特定
            left_node = node.left
            if isinstance(left_node, VarAccess):
                var_name = left_node.value
                assert self.symbol_table is not None
                symbol = self.symbol_table.lookup(var_name)
                if not symbol or not isinstance(symbol, VariableSymbol):
                    self._error(f"Assignment to undeclared variable '{var_name}'", left_node.token)

                self.assembly_code.append(f"; Assign to {var_name} ({symbol.scope})")

                if symbol.scope == 'global':
                    if self.get_symbol_size(symbol) == 2:
                        self.assembly_code.append(f"\tld ({var_name}), hl")
                    else:
                        self.assembly_code.append("\tld a, l")
                        self.assembly_code.append(f"\tld ({var_name}), a")
                else: # local
                    # --- ★ ここからが新しい高速なロジック ---
                    offset = symbol.offset
                    self.assembly_code.append(f"; Store to local var at (ix{offset:+})")
                    if self.get_symbol_size(symbol) == 2: # int
                        self.assembly_code.append(f"\tld (ix{offset:+}), l   ; Store low byte")
                        self.assembly_code.append(f"\tld (ix{offset+1:+}), h ; Store high byte")
                    else: # byte
                        self.assembly_code.append("\tld a, l")
                        self.assembly_code.append(f"\tld (ix{offset:+}), a")

            # 配列への代入
            elif isinstance(node.left, ArrayAccess):
                self.assembly_code.append("; Assignment to array element")
                # 1. 右辺の値を評価 -> HL
                self.visit(node.right)
                self.assembly_code.append("\tpush hl")
                # 2. 左辺の要素アドレスを計算 -> HL
                self._get_element_address_in_hl(node.left)
                # 3. 退避した値をDEに復元
                self.assembly_code.append("\tpop de")
                # 4. DEの値をHLが指すアドレスにストア
                symbol = self.symbol_table.lookup(node.left.var_node.value)
                if self.get_symbol_size(symbol) == 2: # int
                    self.assembly_code.append("\tld (hl), e")
                    self.assembly_code.append("\tinc hl")
                    self.assembly_code.append("\tld (hl), d")
                else: # byte
                    self.assembly_code.append("\tld (hl), e ; Note: storing low byte of DE")

    def visit_Block(self, node):
        for stmt in node.statements:
            self.visit(stmt)

    def visit_IfStatement(self, node):
        self._emit_source_comment(node)  # ソースコードの行をコメントとして出力

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
        self._emit_source_comment(node)  # ソースコードの行をコメントとして出力

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

# (codegen.py内のvisit_BinOpメソッドを修正)

    def visit_BinOp(self, node: BinOp) -> None:
        op_type = node.op.type

        # 共通の評価ロジック
        self._emit_source_comment(node)
        self.assembly_code.append(f"; Begin BinOp {op_type}")
        self.visit(node.right)
        self.assembly_code.append("\tpush hl")
        self.visit(node.left)
        self.assembly_code.append("\tpop de")

        # 演算子に応じたコード生成
        if op_type == 'PLUS':
            self.assembly_code.append("\tadd hl, de")
        elif op_type == 'MINUS':
            self.assembly_code.append("\tand a ; Clear carry")
            self.assembly_code.append("\tsbc hl, de")
        elif op_type == 'MUL':
            # ★ 乗算サブルーチンを呼び出す
            self.assembly_code.append("\tcall MUL16")
            # 32bit結果の上位(DE)は無視し、下位(HL)を結果とする
        elif op_type == 'DIV':
            # ★ 除算サブルーチンを呼び出す
            self.assembly_code.append("\tcall DIV16")
            # 商がHLに、余りがDEに残る。結果は商(HL)とする
        elif op_type in ('EQ', 'NE', 'LT', 'GT', 'LE', 'GE'):
            self.assembly_code.append("\tand a")
            self.assembly_code.append("\tsbc hl, de ; For comparison")
        else:
            self._error(f"Unsupported binary operator '{op_type}'", node.op)

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

    def visit_UnaryOp(self, node: UnaryOp) -> None:
        if node.op.type == 'AMPERSAND':
            # &var の場合、varのアドレスをHLにロードする
            var_name = node.expr.value # 簡単のため、exprが変数名であると仮定
            symbol = self.symbol_table.lookup(var_name)

            self.assembly_code.append(f"; Address of '{var_name}'")
            if symbol.scope == 'global':
                self.assembly_code.append(f"\tld hl, {var_name}")
            else: # local
                # HL = IX + offset
                self.assembly_code.append("\tpush ix")
                self.assembly_code.append("\tpop hl")
                self.assembly_code.append(f"\tld de, {symbol.offset}")
                self.assembly_code.append("\tadd hl, de")

    def visit_MemAccess(self, node: MemAccess) -> None:
        # MEM[addr] の値を読む場合
        self.assembly_code.append(f"; Read from MEM[]")
        # 1. アドレス式を評価 -> 結果がHLに入る
        self.visit(node.address_expr)
        # 2. HLが指すアドレスから値をロードし、HLに格納
        self.assembly_code.append("\tld e, (hl)   ; Load low byte")
        self.assembly_code.append("\tinc hl")
        self.assembly_code.append("\tld d, (hl)   ; Load high byte")
        self.assembly_code.append("\tex de, hl")

    def visit_StringLiteral(self, node: StringLiteral) -> None:
        """文字列リテラルのアドレスをHLレジスタにロードするコードを生成"""
        label = self._get_string_label(node.value)
        self.assembly_code.append(f"; Load string literal address")
        self.assembly_code.append(f"\tld hl, {label}")

    def visit_ForInStatement(self, node: ForInStatement) -> None:
        self._emit_source_comment(node)

        array_name = node.array_node.value
        array_symbol = self.symbol_table.lookup(array_name)
        item_name = node.item_token.value

        # ループ変数'item'のオフセットを取得
        item_symbol = node.local_symbols[item_name]
        item_offset = item_symbol.offset

        loop_start_label = self.new_label()
        loop_end_label = self.new_label()

        self.assembly_code.append(f"; For '{item_name}' in '{array_name}'")
        # --- ループセットアップ ---
        # 1. 配列のベースアドレスをIXにロード (ポインタとして使用)
        self.assembly_code.append(f"\tld ix, {array_name}")
        # 2. 配列の要素数をBCにロード (カウンタとして使用)
        self.assembly_code.append(f"\tld bc, {array_symbol.size}")

        # --- ループ開始 ---
        self.assembly_code.append(f"{loop_start_label}:")
        # 3. カウンタが0かチェック
        self.assembly_code.append("\tld a, b")
        self.assembly_code.append("\tor c")
        self.assembly_code.append(f"\tjp z, {loop_end_label}")

        # 4. IXが指す要素を'item'変数にコピー
        #    (IX) -> DE, DE -> (IY+item_offset) のような処理が必要
        #    簡単のため、IXからHLにロードし、それをストアする
        self.assembly_code.append("\tld e, (ix+0)")
        self.assembly_code.append("\tld d, (ix+1)")
        self.assembly_code.append("\tex de, hl")
        self.assembly_code.append(f"\tld (iy{item_offset:+}), l") # フレームポインタをIYと仮定
        self.assembly_code.append(f"\tld (iy{item_offset+1:+}), h")

        # 5. 配列ポインタ(IX)を進める
        self.assembly_code.append("\tinc ix")
        self.assembly_code.append("\tinc ix")

        # --- ループ本体のコードを生成 ---
        # forループ専用スコープに入る
        self.symbol_table.enter_scope()
        for name, symbol in node.local_symbols.items():
            self.symbol_table.define(symbol)

        self.visit(node.body)

        self.symbol_table.leave_scope()

        # 6. カウンタをデクリメントしてループ先頭へ
        self.assembly_code.append("\tdec bc")
        self.assembly_code.append(f"\tjp {loop_start_label}")

        # --- ループ終了 ---
        self.assembly_code.append(f"{loop_end_label}:")

    def visit_MethodCall(self, node: MethodCall) -> None:
        self._emit_source_comment(node)
        var_name = node.var_node.value
        method_name = node.method_token.value.upper() # "append" -> "APPEND"

        self.assembly_code.append(f"; Method call: {var_name}.{method_name}")

        # 引数を評価してレジスタにセット
        # (例: appendの第1引数をDEに)
        if node.args:
            self.visit(node.args[0])
            self.assembly_code.append("\tpush hl")
            self.assembly_code.append("\tpop de")

        # StringBuffer変数のアドレスをHLにロード
        # (シンボルテーブルからアドレスを取得するロジック)
        self.assembly_code.append(f"\tld hl, {var_name}")

        # ランタイム関数を呼び出し
        self.assembly_code.append(f"\tcall SB_{method_name}")