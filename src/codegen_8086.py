from __future__ import annotations
from typing import Optional, NoReturn, cast
from lexer import Token
from symbol_table import ScopedSymbolTable, VariableSymbol, Symbol
from parser import (AST, Type, Program, VarDecl, Assignment, IfStatement, WhileStatement,
                    FuncDecl, FuncCall, ReturnStatement, Block, ArrayAccess, BinOp,
                    Number, VarAccess, Type, StringLiteral, BitAccess, PortAccess, MethodCall)

class CodeGenerator:
    def __init__(self) -> None:
        self.assembly_code: list[str] = []
        self.label_count: int = 0
        self.symbol_table: ScopedSymbolTable | None = None
        self.source_lines: list[str] = []
        self.last_commented_line: int = -1
        self.current_function_name: str | None = None
        self.entry_point: str | None = "start"

    def generate(self, node: AST, symbol_table: ScopedSymbolTable, source_lines: list[str]) -> str:
        self.symbol_table = symbol_table
        self.source_lines = source_lines
        self.visit(node)
        return "\n".join(self.assembly_code)

    def new_label(self) -> str:
        self.label_count += 1
        return f"L{self.label_count}"

    def get_symbol_size(self, symbol: Symbol) -> int:
        if isinstance(symbol, VariableSymbol):
            assert symbol.type is not None
            if symbol.type.value == 'int': return 2  # word
            if symbol.type.value == 'byte': return 1 # byte
        return 2

    def visit(self, node: AST) -> None:
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: AST) -> None:
        raise NotImplementedError(f"No visit_{type(node).__name__} method")

    def _error(self, message: str, token: Optional[Token] = None) -> NoReturn:
        location = f" (line {token.line}, column {token.column})" if token else ""
        raise Exception(f"Code generation error{location}: {message}")

    def _get_start_line(self, node: AST) -> int:
        token = getattr(node, 'token', None)
        if token is not None: return token.line
        name_token = getattr(node, 'name_token', None)
        if name_token is not None: return name_token.line
        var_node = getattr(node, 'var_node', None)
        if var_node is not None: return self._get_start_line(var_node)
        left = getattr(node, 'left', None)
        if left is not None: return self._get_start_line(left)
        return -1

    def _emit_source_comment(self, node: AST) -> None:
        line_num = self._get_start_line(node)
        if line_num != -1 and line_num != self.last_commented_line:
            source_line = self.source_lines[line_num - 1].strip()
            if source_line:
                self.assembly_code.append(f"\n; {source_line}")
                self.last_commented_line = line_num

    def visit_Program(self, node: Program) -> None:
        assert self.symbol_table is not None
        # --- .dataセグメント (RAM) ---
        self.assembly_code.append("segment .data")
        for child in node.children:
            if isinstance(child, VarDecl):
                symbol = self.symbol_table.lookup(child.var_node.value)
                if not symbol or not isinstance(symbol, VariableSymbol):
                    self._error(f"'{child.var_node.value}' is not a valid variable")
                if not symbol.is_const:
                    assert symbol.type is not None
                    # ★ 初期値がある場合はdw/dbで、ない場合はresw/resbで領域確保
                    if child.initial_value and isinstance(child.initial_value, Number):
                        size_directive = "dw" if symbol.type.value == 'int' else "db"
                        self.assembly_code.append(f"\t{child.var_node.value} {size_directive} {child.initial_value.value}")
                    else:
                        size_directive = "resw 1" if symbol.type.value == 'int' else "resb 1"
                        self.assembly_code.append(f"\t{child.var_node.value} {size_directive}")

        # --- .textセグメント (ROM) ---
        self.assembly_code.append("\nsegment .text")
        self.assembly_code.append("\tglobal main")

        for child in node.children:
            if isinstance(child, FuncDecl):
                self.visit(child)

    def visit_VarDecl(self, node: VarDecl) -> None:
        pass  # 変数宣言はProgramで処理済み

    def visit_FuncDecl(self, node: FuncDecl) -> None:
        assert self.symbol_table is not None
        func_name = node.name_token.value
        self.current_function_name = func_name
        self.assembly_code.append(f"\n; --- Function: {func_name} ---")
        self.assembly_code.append(f"{func_name}:")
        self.assembly_code.append("\tpush bp")
        self.assembly_code.append("\tmov bp, sp")
        # ローカル変数の領域確保
        local_var_size = sum(self.get_symbol_size(s) for s in node.local_symbols.values())
        if local_var_size > 0:
            self.assembly_code.append(f"\tsub sp, {local_var_size}")

        # ★ パース時にスコープから外れたローカルシンボルをコード生成中だけ再度参照可能にする
        self.symbol_table.scopes.append(node.local_symbols)
        self.visit(node.body)
        self.symbol_table.scopes.pop()

        self.assembly_code.append(f".L_RET_{func_name}:")
        self.assembly_code.append("\tmov sp, bp")
        self.assembly_code.append("\tpop bp")
        self.assembly_code.append("\tret")
        self.current_function_name = None

    def visit_BinOp(self, node: BinOp) -> None:
        self.visit(node.right)
        self.assembly_code.append("\tpush ax")
        self.visit(node.left)
        self.assembly_code.append("\tpop bx")

        op_type = node.op.type
        if op_type == 'PLUS':
            self.assembly_code.append("\tadd ax, bx")
        elif op_type == 'MINUS':
            self.assembly_code.append("\tsub ax, bx")
        # MULとDIVは後でCPU命令に置き換える
        elif op_type == 'MUL':
            self.assembly_code.append("\tmul bx")
        elif op_type == 'DIV':
            self.assembly_code.append("\txor dx, dx") # 上位ワードをクリア
            self.assembly_code.append("\tdiv bx")

    def visit_Number(self, node: Number) -> None:
        self.assembly_code.append(f"\tmov ax, {node.value}")

    def visit_VarAccess(self, node: VarAccess) -> None:
        assert self.symbol_table is not None
        var_name = node.value
        symbol = self.symbol_table.lookup(var_name)
        if symbol is None or not isinstance(symbol, VariableSymbol):
            self.assembly_code.append(f"; ERROR: symbol '{var_name}' not found")
            raise Exception(f"Undefined variable: {var_name}")
        assert symbol.type is not None
        size_directive = "word" if symbol.type.value == 'int' else "byte"

        if symbol.scope == 'global':
            self.assembly_code.append(f"\tmov ax, [{var_name}]")
        else: # local
            self.assembly_code.append(f"\tmov ax, {size_directive} [bp{symbol.offset:+}]")

    def visit_ArrayAccess(self, node: ArrayAccess) -> None:
        assert self.symbol_table is not None
        var_name = node.var_node.value
        symbol = self.symbol_table.lookup(var_name)
        if symbol is None or not isinstance(symbol, VariableSymbol):
            raise Exception(f"Undefined variable: {var_name}")

        self.visit(node.index_expr) # インデックスがAXに入る
        self.assembly_code.append("\tmov bx, ax")
        if self.get_symbol_size(symbol) == 2:
            self.assembly_code.append("\tshl bx, 1")

        if symbol.scope == 'global':
            self.assembly_code.append(f"\tmov ax, [{var_name} + bx]")
        else: # local
            self.assembly_code.append(f"\tmov ax, [bp{symbol.offset:+} + bx]")

    def _emit_read_bit_base(self, base: AST) -> None:
        """ビットアクセスの元となる値をAXに読み込む"""
        if isinstance(base, PortAccess):
            self.visit(base.address_expr)
            self.assembly_code.append("\tmov dx, ax")
            self.assembly_code.append("\tin al, dx")
            self.assembly_code.append("\tmov ah, 0")
        else:
            self.visit(base)

    def visit_BitAccess(self, node: BitAccess) -> None:
        self._emit_read_bit_base(node.var_node)
        mask = 1 << node.bit_num_token.value
        self.assembly_code.append(f"\tand ax, {mask}")

    def visit_Assignment(self, node: Assignment) -> None:
        self._emit_source_comment(node)
        assert self.symbol_table is not None
        self.visit(node.right) # 結果がAXに入る

        left_node = node.left
        if isinstance(left_node, VarAccess):
            var_name = left_node.value
            symbol = self.symbol_table.lookup(var_name)
            if symbol is None or not isinstance(symbol, VariableSymbol):
                self._error(f"'{var_name}' is not a valid variable", left_node.token)
            assert symbol.type is not None
            size_directive = "word" if symbol.type.value == 'int' else "byte"
            reg = "ax" if size_directive == "word" else "al"

            if symbol.scope == 'global':
                self.assembly_code.append(f"\tmov [{var_name}], {reg}")
            else: # local
                self.assembly_code.append(f"\tmov {size_directive} [bp{symbol.offset:+}], {reg}")

        elif isinstance(left_node, BitAccess):
            # 右辺値(0/非0)を退避してから、元の値にビットを立てる/クリアする
            mask = 1 << left_node.bit_num_token.value
            base = left_node.var_node
            self.assembly_code.append("\tmov cx, ax")
            self._emit_read_bit_base(base)
            clear_label, end_label = self.new_label(), self.new_label()
            self.assembly_code.append("\tcmp cx, 0")
            self.assembly_code.append(f"\tje {clear_label}")
            self.assembly_code.append(f"\tor al, {mask}")
            self.assembly_code.append(f"\tjmp {end_label}")
            self.assembly_code.append(f"{clear_label}:")
            self.assembly_code.append(f"\tand al, {(~mask) & 0xFF}")
            self.assembly_code.append(f"{end_label}:")

            if isinstance(base, PortAccess):
                self.assembly_code.append("\tout dx, al")
            elif isinstance(base, VarAccess):
                var_name = base.value
                symbol = self.symbol_table.lookup(var_name)
                if symbol is None or not isinstance(symbol, VariableSymbol):
                    self._error(f"'{var_name}' is not a valid variable", base.token)
                if symbol.scope == 'global':
                    self.assembly_code.append(f"\tmov [{var_name}], al")
                else: # local
                    self.assembly_code.append(f"\tmov byte [bp{symbol.offset:+}], al")

    def visit_Block(self, node: Block) -> None:
        for stmt in node.statements:
            self.visit(stmt)

    
    def visit_IfStatement(self, node: IfStatement) -> None:
        """
        IfStatementノードの処理:
        if 条件:
            ...then_block...
        else:
            ...else_block...
        """
        self._emit_source_comment(node)
        else_label = self.new_label()
        end_label = self.new_label()

        # 条件式の評価（結果はAXに入ると仮定）
        self.visit(node.condition)
        self.assembly_code.append("\tcmp ax, 0")
        self.assembly_code.append(f"\tje {else_label}")

        # thenブロック
        self.visit(node.then_block)
        self.assembly_code.append(f"\tjmp {end_label}")

        # elseブロック
        self.assembly_code.append(f"{else_label}:")
        if node.else_block:
            self.visit(node.else_block)

        self.assembly_code.append(f"{end_label}:")

    def visit_WhileStatement(self, node: WhileStatement) -> None:
        """
        WhileStatementノードの処理:
        while 条件:
            ...body...
        """
        self._emit_source_comment(node)
        start_label = self.new_label()
        end_label = self.new_label()

        self.assembly_code.append(f"{start_label}:")
        self.visit(node.condition)
        self.assembly_code.append("\tcmp ax, 0")
        self.assembly_code.append(f"\tje {end_label}")

        self.visit(node.body)
        self.assembly_code.append(f"\tjmp {start_label}")
        self.assembly_code.append(f"{end_label}:")

    def visit_ForInStatement(self, node) -> None:
        """
        ForInStatementノードの処理:
        for var in array:
            ...body...
        """
        self._emit_source_comment(node)
        assert self.symbol_table is not None
        loop_var = node.item_token.value
        array_name = node.array_node.value

        # ループインデックス用一時変数名
        index_var_name = f"__for_index_{loop_var}"

        # ★ パース時にスコープから外れたローカルシンボル（ループ変数）を再度参照可能にする
        self.symbol_table.scopes.append(node.local_symbols)

        # シンボルテーブルにインデックス変数を追加（なければ）
        if not self.symbol_table.lookup(index_var_name, current_scope_only=True):
            # int型のダミートークンを生成
            int_token = Token('INT', 'int', line=0, column=0)
            offset = -2  # 例: bp-2（既存ローカル変数のオフセット管理に合わせて調整）
            index_symbol = VariableSymbol(index_var_name, Type(int_token), 'local', offset, size=2, is_const=False)
            self.symbol_table.define(index_symbol)

        index_symbol = self.symbol_table.lookup(index_var_name)
        assert index_symbol is not None and isinstance(index_symbol, VariableSymbol)
        index_offset = index_symbol.offset

        # ループ用ラベル
        start_label = self.new_label()
        end_label = self.new_label()

        # ループインデックス初期化
        self.assembly_code.append(f"\tmov word [bp{index_offset:+}], 0")

        self.assembly_code.append(f"{start_label}:")
        # 配列サイズチェック
        self.assembly_code.append(f"\tmov ax, word [bp{index_offset:+}]")
        self.assembly_code.append(f"\tcmp ax, {array_name}_size")
        self.assembly_code.append(f"\tjge {end_label}")

        # ループ変数に配列要素を代入
        self.assembly_code.append(f"\tmov bx, word [bp{index_offset:+}]")
        self.assembly_code.append(f"\tmov ax, [{array_name} + bx*2]")  # int型配列の場合
        self.assembly_code.append(f"\tmov word [bp{index_offset:+}], ax")

        # ループ本体
        self.visit(node.body)

        # インデックス++
        self.assembly_code.append(f"\tinc word [bp{index_offset:+}]")
        self.assembly_code.append(f"\tjmp {start_label}")
        self.assembly_code.append(f"{end_label}:")

        self.symbol_table.scopes.pop()


    def visit_ReturnStatement(self, node: ReturnStatement) -> None:
        self._emit_source_comment(node)
        if node.expr:
            self.visit(node.expr) # 戻り値がAXに入る
        self.assembly_code.append(f"\tjmp .L_RET_{self.current_function_name}")

    def visit_FuncCall(self, node: FuncCall) -> None:
        self._emit_source_comment(node)
        func_name = node.name_token.value

        # ★★★ print と printf のための特別処理 ★★★
        if func_name in ("print", "printf"):
            self.assembly_code.append(f"; Special call to sl_{func_name}")
            # ライブラリの公開名 (sl_print, sl_printf) を呼び出す
            self.assembly_code.append(f"\tcall sl_{func_name}")

            # 第1引数は文字列リテラルでなければならない
            if not node.args or not isinstance(node.args[0], StringLiteral):
                self._error("First argument to 'print' or 'printf' must be a string literal.", node.name_token)
            first_arg = cast(StringLiteral, node.args[0])

            # CALLの直後に文字列を .db で配置
            format_string = first_arg.value
            # NASMでは ` (バッククォート) を使うと\nなどを解釈してくれる
            escaped_string = format_string.replace('\\n', '`, 10, `').replace('\\r', '`, 13, `')
            self.assembly_code.append(f"\tdb `{escaped_string}`, 0")

            # printfの場合、第2引数以降は変数のアドレスを .dd で配置
            if func_name == "printf" and len(node.args) > 1:
                for arg_node in node.args[1:]:
                    if not isinstance(arg_node, VarAccess):
                        self._error("Arguments to 'printf' after the format string must be variable names.", getattr(arg_node, 'token', None))
                    self.assembly_code.append(f"\tdd {arg_node.value}")

        else:
            # --- 通常の関数呼び出し (スタック経由) ---
            self.assembly_code.append(f"; Standard call to {func_name}")
            if node.args:
                for arg in reversed(node.args):
                    self.visit(arg)
                    self.assembly_code.append("\tpush ax")

            self.assembly_code.append(f"\tcall {func_name}")

            if node.args:
                self.assembly_code.append(f"\tadd sp, {len(node.args) * 2}")

    def visit_MethodCall(self, node: MethodCall) -> None:
        """StringBuffer 等のメソッド呼び出し。現状は StringBuffer.append のみ対応する最小実装。"""
        self._emit_source_comment(node)
        assert self.symbol_table is not None
        obj_name = node.var_node.value
        symbol = self.symbol_table.lookup(obj_name)
        if symbol is None or not isinstance(symbol, VariableSymbol):
            raise Exception(f"Undefined variable: {obj_name}")

        method_name = node.method_token.value
        if method_name != "append":
            raise Exception(f"Unknown method '{method_name}' on '{obj_name}'")

        if not node.args or not isinstance(node.args[0], StringLiteral):
            raise Exception("StringBuffer.append() currently only supports a single string literal argument.")

        self.assembly_code.append(f"; {obj_name}.append(...)")
        if symbol.scope == 'global':
            self.assembly_code.append(f"\tmov ax, {obj_name}")
        else: # local
            self.assembly_code.append(f"\tlea ax, [bp{symbol.offset:+}]")
        self.assembly_code.append("\tpush ax")
        self.assembly_code.append("\tcall strcatl")

        escaped_string = node.args[0].value.replace('\\n', '`, 10, `').replace('\\r', '`, 13, `')
        self.assembly_code.append(f"\tdb `{escaped_string}`, 0")