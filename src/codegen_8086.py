from __future__ import annotations
from typing import Optional
from symbol_table import ScopedSymbolTable, VariableSymbol, Symbol
from parser import (AST, Program, VarDecl, Assignment, IfStatement, WhileStatement,
                    FuncDecl, FuncCall, ReturnStatement, Block, ArrayAccess, BinOp,
                    Number, VarAccess, Type)

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
            if symbol.type.value == 'int': return 2  # word
            if symbol.type.value == 'byte': return 1 # byte
        return 2

    def visit(self, node: AST) -> None:
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: AST) -> None:
        raise NotImplementedError(f"No visit_{type(node).__name__} method")

    def _get_start_line(self, node: AST) -> int:
        if hasattr(node, 'token'): return node.token.line
        if hasattr(node, 'name_token'): return node.name_token.line
        if hasattr(node, 'var_node'): return self._get_start_line(node.var_node)
        if hasattr(node, 'left'): return self._get_start_line(node.left)
        return -1

    def _emit_source_comment(self, node: AST) -> None:
        line_num = self._get_start_line(node)
        if line_num != -1 and line_num != self.last_commented_line:
            source_line = self.source_lines[line_num - 1].strip()
            if source_line:
                self.assembly_code.append(f"\n; {source_line}")
                self.last_commented_line = line_num

    def visit_Program(self, node: Program) -> None:
        # 8086用のセグメント定義
        self.assembly_code.append("segment .data")
        # グローバル変数の定義
        for child in node.children:
            if isinstance(child, VarDecl):
                 symbol = self.symbol_table.lookup(child.var_node.value)
                 if not symbol.is_const:
                     size_directive = "dw" if symbol.type.value == 'int' else "db"
                     self.assembly_code.append(f"{child.var_node.value} {size_directive} 0")

        self.assembly_code.append("\nsegment .text")
        self.assembly_code.append("global main") # C言語のようにmainをエントリーポイントとする

        for child in node.children:
            if isinstance(child, FuncDecl):
                self.visit(child)

    def visit_FuncDecl(self, node: FuncDecl) -> None:
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

        self.visit(node.body)

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
        var_name = node.value
        symbol = self.symbol_table.lookup(var_name)
        size_directive = "word" if symbol.type.value == 'int' else "byte"

        if symbol.scope == 'global':
            self.assembly_code.append(f"\tmov ax, [{var_name}]")
        else: # local
            self.assembly_code.append(f"\tmov ax, {size_directive} [bp{symbol.offset:+}]")

    def visit_Assignment(self, node: Assignment) -> None:
        self._emit_source_comment(node)
        self.visit(node.right) # 結果がAXに入る

        left_node = node.left
        if isinstance(left_node, VarAccess):
            var_name = left_node.value
            symbol = self.symbol_table.lookup(var_name)
            size_directive = "word" if symbol.type.value == 'int' else "byte"
            reg = "ax" if size_directive == "word" else "al"

            if symbol.scope == 'global':
                self.assembly_code.append(f"\tmov [{var_name}], {reg}")
            else: # local
                self.assembly_code.append(f"\tmov {size_directive} [bp{symbol.offset:+}], {reg}")

    def visit_Block(self, node: Block) -> None:
        for stmt in node.statements:
            self.visit(stmt)

    def visit_ReturnStatement(self, node: ReturnStatement) -> None:
        self._emit_source_comment(node)
        if node.expr:
            self.visit(node.expr) # 戻り値がAXに入る
        self.assembly_code.append(f"\tjmp .L_RET_{self.current_function_name}")

    # visit_FuncCall は次のステップで特殊化する
    def visit_FuncCall(self, node: FuncCall) -> None:
        self._emit_source_comment(node)
        func_name = node.name_token.value
        # (今は通常のスタック渡しのみ実装)
        for arg in reversed(node.args):
            self.visit(arg)
            self.assembly_code.append("\tpush ax")
        self.assembly_code.append(f"\tcall {func_name}")
        # スタッククリーンアップ
        if node.args:
            self.assembly_code.append(f"\tadd sp, {len(node.args) * 2}")