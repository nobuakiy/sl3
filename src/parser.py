from __future__ import annotations
from typing import Iterator, Optional, NoReturn
from lexer import Token
from symbol_table import ScopedSymbolTable, VariableSymbol, FunctionSymbol

# --- AST Node Definitions (変更なし) ---
class AST: pass
class Program(AST):
    def __init__(self, children: list[AST]): self.children: list[AST] = children
class VarDecl(AST):
    def __init__(self, type_node: Type, var_node: Token, initial_value: Optional[AST] = None, is_array: bool = False, size: int = 0):
        self.type_node, self.var_node, self.initial_value = type_node, var_node, initial_value
        self.is_array, self.size = is_array, size
class Assignment(AST):
    def __init__(self, left: AST, right: AST): self.left, self.right = left, right
class IfStatement(AST):
    def __init__(self, condition: AST, then_block: Block, else_block: Optional[Block] = None):
        self.condition, self.then_block, self.else_block = condition, then_block, else_block
class WhileStatement(AST):
    def __init__(self, condition: AST, body: Block): self.condition, self.body = condition, body
class FuncDecl(AST):
    def __init__(self, return_type: Type, name_token: Token, params: list[Param], body: Block):
        self.return_type, self.name_token, self.params, self.body = return_type, name_token, params, body
class FuncCall(AST):
    def __init__(self, name_token: Token, args: list[AST]): self.name_token, self.args = name_token, args
class ReturnStatement(AST):
    def __init__(self, expr: AST): self.expr: AST = expr
class Block(AST):
    def __init__(self, statements: list[AST]): self.statements: list[AST] = statements
class ArrayAccess(AST):
    def __init__(self, var_node: VarAccess, index_expr: AST): self.var_node, self.index_expr = var_node, index_expr
class BinOp(AST):
    def __init__(self, left: AST, op: Token, right: AST): self.left, self.op, self.right = left, op, right
class Number(AST):
    def __init__(self, token: Token): self.token, self.value = token, token.value
class VarAccess(AST):
    def __init__(self, token: Token): self.token, self.value = token, token.value
class Type(AST):
    def __init__(self, token: Token): self.token, self.value = token, token.value
class Param(AST):
    def __init__(self, type_node: Type, var_node: Token): self.type_node, self.var_node = type_node, var_node

# --- Parser ---
class Parser:
    # __init__, _error, advance, eat (変更なし)
    def __init__(self, tokens: Iterator[Token], source_code: str):
        self.tokens: Iterator[Token] = tokens
        self.current_token: Optional[Token] = None
        self.peek_token: Optional[Token] = None
        self.source_lines: list[str] = source_code.splitlines()
        self.advance(); self.advance()
        self.symbol_table: ScopedSymbolTable = ScopedSymbolTable()
        self.precedence: dict[str, int] = {'EQ': 3, 'NE': 3, 'LT': 4, 'GT': 4, 'LE': 4, 'GE': 4, 'PLUS': 5, 'MINUS': 5, 'MUL': 6, 'DIV': 6}
    def _error(self, message: str, token: Optional[Token] = None) -> NoReturn:
        token = token or self.current_token
        err_line, pointer, line_info = "<source not available>", "", ""
        if token:
            line_num, col_num = token.line, token.column
            line_info = f"on line {line_num}, column {col_num}"
            if 0 < line_num <= len(self.source_lines):
                err_line = self.source_lines[line_num - 1].replace('\t', '    ')
                pointer = " " * col_num + "^"
        full_message = (f"\n\n--- Compilation Error ---\nSyntax Error {line_info}:\n{message}\n\n> {err_line}\n  {pointer}\n")
        raise SyntaxError(full_message)
    def advance(self) -> None:
        self.current_token = self.peek_token
        try: self.peek_token = next(self.tokens)
        except StopIteration: self.peek_token = None
    def eat(self, token_type: str) -> None:
        if self.current_token and self.current_token.type == token_type: self.advance()
        else:
            expected_type = self.current_token.type if self.current_token else 'EOF'
            self._error(f"Expected token '{token_type}', but got '{expected_type}'")

    # --- ここからロジックを修正 ---

    def parse(self) -> Program:
        declarations: list[AST] = []
        while self.current_token:
            declarations.append(self.parse_top_level_declaration())
        return Program(declarations)

    def parse_top_level_declaration(self) -> AST:
        type_node = self.parse_type()
        name_token = self.current_token
        self.eat('ID') # IDを消費
        if self.current_token and self.current_token.type == 'LPAREN':
            return self.parse_function_declaration(type_node, name_token)
        else:
            return self.parse_variable_declaration(type_node, name_token)

    def parse_variable_declaration(self, type_node: Type, name_token: Token) -> VarDecl:
        is_array, size = False, 0
        if self.current_token and self.current_token.type == 'LBRACKET':
            is_array, size = True, self._parse_array_size()
        
        scope = 'global' if self.symbol_table.scope_level == 0 else 'local'
        # ここでローカル変数のオフセットを計算・管理する必要がある (今後の課題)
        symbol = VariableSymbol(name_token.value, type_node, scope, is_array=is_array, size=size)
        self.symbol_table.define(symbol)
        
        initial_value = None
        if self.current_token and self.current_token.type == 'ASSIGN':
            self.eat('ASSIGN'); initial_value = self.parse_expression()
        self.eat('SEMICOLON')
        return VarDecl(type_node, name_token, initial_value, is_array, size)
    
    def _parse_array_size(self) -> int:
        self.eat('LBRACKET')
        size_node = self.parse_primary()
        if not isinstance(size_node, Number): self._error("Array size must be an integer literal")
        self.eat('RBRACKET')
        return size_node.value

    def parse_function_declaration(self, type_node: Type, name_token: Token) -> FuncDecl:
        func_symbol = FunctionSymbol(name_token.value, type_node)
        self.symbol_table.define(func_symbol)
        self.eat('LPAREN')
        params: list[Param] = []
        # ... パラメータ解析 (省略) ...
        self.eat('RPAREN')
        self.symbol_table.enter_scope()
        body = self.parse_block_statement()
        self.symbol_table.leave_scope()
        return FuncDecl(type_node, name_token, params, body)

    def parse_statement(self) -> AST:
        if not self.current_token: self._error("Unexpected end of file")
        tok_type = self.current_token.type
        if tok_type in ('INT', 'BYTE'):
            # 文中の変数宣言は、型 -> ID -> ... と続く
            type_node = self.parse_type()
            name_token = self.current_token
            self.eat('ID') # IDを消費
            return self.parse_variable_declaration(type_node, name_token)
        if tok_type == 'ID': return self.parse_assignment_or_call_statement()
        if tok_type == 'IF': return self.parse_if_statement()
        if tok_type == 'WHILE': return self.parse_while_statement()
        if tok_type == 'RETURN': return self.parse_return_statement()
        if tok_type == 'LBRACE': return self.parse_block_statement()
        self._error(f"Invalid statement starting with '{tok_type}'")

    def parse_assignment_or_call_statement(self) -> AST:
        name_token = self.current_token
        # 関数呼び出しかどうかを先読み
        if self.peek_token and self.peek_token.type == 'LPAREN':
            call_node = self.parse_function_call()
            self.eat('SEMICOLON')
            return call_node
        
        # 代入文の解析
        self.eat('ID'); left_node: AST = VarAccess(name_token)
        if self.current_token and self.current_token.type == 'LBRACKET':
            self.eat('LBRACKET'); index_expr = self.parse_expression(); self.eat('RBRACKET')
            left_node = ArrayAccess(left_node, index_expr)
        self.eat('ASSIGN'); right_node = self.parse_expression(); self.eat('SEMICOLON')
        return Assignment(left_node, right_node)
    
    # ... (parse_if, parse_while, parse_return, parse_type は変更なし) ...
    # ... (parse_expression, parse_primary, parse_function_call は変更なし) ...
    # (parse_block_statementも変更なし)
    def parse_block_statement(self) -> Block:
        self.eat('LBRACE')
        statements: list[AST] = []
        while self.current_token and self.current_token.type != 'RBRACE':
            statements.append(self.parse_statement())
        self.eat('RBRACE')
        return Block(statements)

    def parse_assignment_statement(self) -> Assignment:
        name_token = self.current_token
        self.eat('ID'); 
        left_node: AST = VarAccess(name_token)
        if self.current_token and self.current_token.type == 'LBRACKET':
            self.eat('LBRACKET'); 
            index_expr = self.parse_expression(); 
            self.eat('RBRACKET')
            left_node = ArrayAccess(left_node, index_expr)
        self.eat('ASSIGN'); 
        right_node = self.parse_expression(); 
        self.eat('SEMICOLON')
        return Assignment(left_node, right_node)
        
    def parse_if_statement(self) -> IfStatement:
        self.eat('IF'); 
        self.eat('LPAREN'); 
        condition = self.parse_expression(); 
        self.eat('RPAREN')
        then_block = self.parse_block_statement()
        else_block = None
        if self.current_token and self.current_token.type == 'ELSE':
            self.eat('ELSE'); 
            else_block = self.parse_block_statement()
        return IfStatement(condition, then_block, else_block)

    def parse_while_statement(self) -> WhileStatement:
        self.eat('WHILE'); 
        self.eat('LPAREN'); 
        condition = self.parse_expression(); 
        self.eat('RPAREN')
        body = self.parse_block_statement()
        return WhileStatement(condition, body)
        
    def parse_return_statement(self) -> ReturnStatement:
        self.eat('RETURN'); 
        expr = self.parse_expression(); 
        self.eat('SEMICOLON')
        return ReturnStatement(expr)

    def parse_type(self) -> Type:
        token = self.current_token
        if token and token.type in ('INT', 'BYTE', 'VOID'): 
            self.advance(); 
            return Type(token)
        self._error("Expected a type specifier")

    def parse_expression(self, prec: int = 0) -> AST:
        node = self.parse_primary()
        while self.current_token and self.current_token.type in self.precedence and self.precedence[self.current_token.type] > prec:
            op_token = self.current_token
            self.advance()
            right_node = self.parse_expression(self.precedence[op_token.type])
            node = BinOp(left=node, op=op_token, right=right_node)
        return node

    def parse_primary(self) -> AST:
        token = self.current_token
        if not token: 
            self._error("Unexpected end of expression")
        if token.type == 'INTEGER': self.advance(); return Number(token)
        if token.type == 'ID':
            name_token = token
            if self.peek_token and self.peek_token.type == 'LPAREN': return self.parse_function_call()
            self.advance()
            if self.current_token and self.current_token.type == 'LBRACKET':
                self.eat('LBRACKET'); index_expr = self.parse_expression(); self.eat('RBRACKET')
                return ArrayAccess(VarAccess(name_token), index_expr)
            return VarAccess(name_token)
        self._error(f"Unexpected token in expression: {token}")

    def parse_function_call(self) -> FuncCall:
        name_token = self.current_token
        self.eat('ID'); self.eat('LPAREN')
        args: list[AST] = []
        if self.current_token and self.current_token.type != 'RPAREN':
            args.append(self.parse_expression())
            while self.current_token and self.current_token.type == 'COMMA':
                self.eat('COMMA'); args.append(self.parse_expression())
        self.eat('RPAREN')
        return FuncCall(name_token, args)