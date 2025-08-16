# main.py

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Any
from enum import Enum, auto
import re
import sys

# =======================
# AST Node Definitions
# =======================

@dataclass
class Program:
    decls: List["Decl"]

class Decl: ...

@dataclass
class ModuleDecl(Decl):
    name: str
    decls: List[Decl]

@dataclass
class StructDecl(Decl):
    name: str
    fields: List["VarDecl"]

@dataclass
class FuncDecl(Decl):
    ret_type: "TypeNode"
    name: str
    params: List["Param"]
    body: "Block"

@dataclass
class Param:
    type: "TypeNode"
    name: str
    array_size: Optional[int] = None

@dataclass
class VarDecl(Decl):
    type: "TypeNode"
    name: str
    array_size: Optional[int] = None
    init: Optional["Expr"] = None

@dataclass
class TypeNode:
    name: str

@dataclass
class Block:
    statements: List["Stmt"]

class Stmt: ...

@dataclass
class IfStmt(Stmt):
    cond: "Expr"
    then_stmt: Stmt
    else_stmt: Optional[Stmt]

@dataclass
class WhileStmt(Stmt):
    cond: "Expr"
    body: Stmt

@dataclass
class ReturnStmt(Stmt):
    value: Optional["Expr"]

@dataclass
class ExprStmt(Stmt):
    expr: "Expr"

# Expressions
class Expr: ...

@dataclass
class Assign(Expr):
    op: str
    target: "Expr"
    value: "Expr"

@dataclass
class Binary(Expr):
    op: str
    left: Expr
    right: Expr

@dataclass
class Unary(Expr):
    op: str
    expr: Expr

@dataclass
class Call(Expr):
    callee: Expr
    args: List[Expr]

@dataclass
class ArrayAccess(Expr):
    array: Expr
    index: Expr

@dataclass
class BitAccess(Expr):
    base: Expr
    bit: int

@dataclass
class Identifier(Expr):
    name: str

@dataclass
class IntLiteral(Expr):
    value: int

@dataclass
class StringLiteral(Expr):
    value: str

@dataclass
class BoolLiteral(Expr):
    value: bool

@dataclass
class ListLiteral(Expr):
    items: List[Expr]

@dataclass
class LambdaExpr(Expr):
    params: List[Param]
    body: Block

# =======================
# Lexer
# =======================

class TokenType(Enum):
    LPAR = auto(); RPAR = auto()
    LBRACE = auto(); RBRACE = auto()
    LBRACK = auto(); RBRACK = auto()
    COMMA = auto(); SEMI = auto(); DOT = auto()
    PLUS = auto(); MINUS = auto(); STAR = auto(); SLASH = auto(); PERCENT = auto()
    BANG = auto()
    LT = auto(); GT = auto(); EQ = auto()
    AMP = auto(); BAR = auto()
    EQEQ = auto(); NEQ = auto()
    LE = auto(); GE = auto()
    ANDAND = auto(); OROR = auto()
    PLUSEQ = auto(); MINUSEQ = auto(); STAREQ = auto(); SLASHEQ = auto()
    ARROW = auto()
    IDENT = auto(); INT = auto(); STRING = auto()
    IF = auto(); ELSE = auto(); WHILE = auto(); RETURN = auto()
    TRUE = auto(); FALSE = auto()
    STRUCT = auto(); MODULE = auto()
    INTKW = auto(); BYTEKW = auto(); STRBUF = auto(); BOOLKW = auto()
    EOF = auto()

KEYWORDS = {
    "if": TokenType.IF, "else": TokenType.ELSE, "while": TokenType.WHILE, "return": TokenType.RETURN,
    "true": TokenType.TRUE, "false": TokenType.FALSE,
    "struct": TokenType.STRUCT, "module": TokenType.MODULE,
    "int": TokenType.INTKW, "byte": TokenType.BYTEKW, "StringBuffer": TokenType.STRBUF, "bool": TokenType.BOOLKW,
}

@dataclass
class Token:
    kind: TokenType
    lexeme: str
    value: Any
    pos: int
    line_num: int # New field for line number

# =====================
# Token Definition
# =====================
TOKEN_REGEX = [
    ('NUMBER',   r'\d+'),
    ('ID',       r'[A-Za-z_]\w*'),
    ('STRING',   r'"([^"\\]|\\.)*"'),
    ('OP',       r'==|!=|<=|>=|&&|\|\||[+\-*/%<>=!&|^~]'),
    ('PUNCT',    r'[(){}[\],.;]'),
    ('NEWLINE',  r'\n'),
    ('SKIP',     r'[ \t\r]+'),
    ('MISMATCH', r'.'),
]

# =====================
# Lexer
# =====================
class Lexer:
    def __init__(self, code: str):
        self.tokens = []
        self.pos = 0
        self.line_num = 1 # Start line number from 1
        self.tokenize(code)

    def tokenize(self, code: str):
        regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_REGEX)
        for mo in re.finditer(regex, code):
            kind = mo.lastgroup
            value = mo.group()
            if kind == 'NEWLINE':
                self.line_num += 1
                continue
            elif kind == 'SKIP':
                continue
            elif kind == 'NUMBER':
                self.tokens.append(Token(TokenType.INT, value, int(value), mo.start(), self.line_num))
            elif kind == 'ID':
                if value in KEYWORDS:
                    self.tokens.append(Token(KEYWORDS[value], value, value, mo.start(), self.line_num))
                else:
                    self.tokens.append(Token(TokenType.IDENT, value, value, mo.start(), self.line_num))
            elif kind == 'STRING':
                self.tokens.append(Token(TokenType.STRING, value, value[1:-1], mo.start(), self.line_num))
            elif kind == 'OP':
                # Simplified token mapping for operators
                if value == '==': self.tokens.append(Token(TokenType.EQEQ, value, value, mo.start(), self.line_num))
                elif value == '!=': self.tokens.append(Token(TokenType.NEQ, value, value, mo.start(), self.line_num))
                elif value == '<=': self.tokens.append(Token(TokenType.LE, value, value, mo.start(), self.line_num))
                elif value == '>=': self.tokens.append(Token(TokenType.GE, value, value, mo.start(), self.line_num))
                elif value == '&&': self.tokens.append(Token(TokenType.ANDAND, value, value, mo.start(), self.line_num))
                elif value == '||': self.tokens.append(Token(TokenType.OROR, value, value, mo.start(), self.line_num))
                elif value == '+': self.tokens.append(Token(TokenType.PLUS, value, value, mo.start(), self.line_num))
                elif value == '-': self.tokens.append(Token(TokenType.MINUS, value, value, mo.start(), self.line_num))
                elif value == '*': self.tokens.append(Token(TokenType.STAR, value, value, mo.start(), self.line_num))
                elif value == '/': self.tokens.append(Token(TokenType.SLASH, value, value, mo.start(), self.line_num))
                elif value == '%': self.tokens.append(Token(TokenType.PERCENT, value, value, mo.start(), self.line_num))
                elif value == '<': self.tokens.append(Token(TokenType.LT, value, value, mo.start(), self.line_num))
                elif value == '>': self.tokens.append(Token(TokenType.GT, value, value, mo.start(), self.line_num))
                elif value == '=': self.tokens.append(Token(TokenType.EQ, value, value, mo.start(), self.line_num))
                elif value == '!': self.tokens.append(Token(TokenType.BANG, value, value, mo.start(), self.line_num))
                elif value == '&': self.tokens.append(Token(TokenType.AMP, value, value, mo.start(), self.line_num))
                elif value == '|': self.tokens.append(Token(TokenType.BAR, value, value, mo.start(), self.line_num))
                elif value == '^': self.tokens.append(Token(TokenType.OP, value, value, mo.start(), self.line_num))
                elif value == '~': self.tokens.append(Token(TokenType.OP, value, value, mo.start(), self.line_num))
            elif kind == 'PUNCT':
                # Simplified token mapping for punctuations
                if value == '(': self.tokens.append(Token(TokenType.LPAR, value, value, mo.start(), self.line_num))
                elif value == ')': self.tokens.append(Token(TokenType.RPAR, value, value, mo.start(), self.line_num))
                elif value == '{': self.tokens.append(Token(TokenType.LBRACE, value, value, mo.start(), self.line_num))
                elif value == '}': self.tokens.append(Token(TokenType.RBRACE, value, value, mo.start(), self.line_num))
                elif value == '[': self.tokens.append(Token(TokenType.LBRACK, value, value, mo.start(), self.line_num))
                elif value == ']': self.tokens.append(Token(TokenType.RBRACK, value, value, mo.start(), self.line_num))
                elif value == ',': self.tokens.append(Token(TokenType.COMMA, value, value, mo.start(), self.line_num))
                elif value == ';': self.tokens.append(Token(TokenType.SEMI, value, value, mo.start(), self.line_num))
                elif value == '.': self.tokens.append(Token(TokenType.DOT, value, value, mo.start(), self.line_num))
            elif kind == 'MISMATCH':
                raise SyntaxError(f'Unexpected character: {value} on line {self.line_num}')
        self.tokens.append(Token(TokenType.EOF, '', None, len(code), self.line_num))

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def next(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, kind: str, value: Optional[Any] = None) -> Token:
        tok = self.next()
        if tok.kind.name != kind or (value is not None and tok.value != value):
            raise SyntaxError(f"Expected {kind} {value}, got {tok.kind.name} {tok.value} on line {tok.line_num}")
        return tok

# =====================
# Parser
# =====================
class Parser:
    def __init__(self, lexer: Lexer):
        self.lexer = lexer

    def parse_program(self) -> Program:
        nodes = []
        while self.lexer.peek().kind != TokenType.EOF:
            nodes.append(self.parse_statement())
        return Program(nodes)

    # ---------- Statement ----------
    def parse_statement(self) -> Stmt:
        tok = self.lexer.peek()
        if tok.kind == TokenType.IF:
            return self.parse_if()
        elif tok.kind == TokenType.WHILE:
            return self.parse_while()
        elif tok.kind == TokenType.RETURN:
            return self.parse_return()
        elif tok.kind == TokenType.LBRACE:
            return self.parse_block()
        else:
            expr = self.parse_expression()
            self.lexer.expect('SEMI', ';')
            return ExprStmt(expr)

    def parse_if(self) -> IfStmt:
        self.lexer.expect('IF', 'if')
        self.lexer.expect('LPAR', '(')
        cond = self.parse_expression()
        self.lexer.expect('RPAR', ')')
        then_stmt = self.parse_statement()
        else_stmt = None
        if self.lexer.peek().kind == TokenType.ELSE:
            self.lexer.next()
            else_stmt = self.parse_statement()
        return IfStmt(cond, then_stmt, else_stmt)

    def parse_while(self) -> WhileStmt:
        self.lexer.expect('WHILE', 'while')
        self.lexer.expect('LPAR', '(')
        cond = self.parse_expression()
        self.lexer.expect('RPAR', ')')
        body = self.parse_statement()
        return WhileStmt(cond, body)

    def parse_return(self) -> ReturnStmt:
        self.lexer.expect('RETURN', 'return')
        expr = self.parse_expression()
        self.lexer.expect('SEMI', ';')
        return ReturnStmt(expr)

    def parse_block(self) -> Block:
        self.lexer.expect('LBRACE', '{')
        stmts = []
        while self.lexer.peek().kind != TokenType.RBRACE:
            stmts.append(self.parse_statement())
        self.lexer.expect('RBRACE', '}')
        return Block(stmts)

    # ---------- Expression ----------
    def parse_expression(self) -> Expr:
        return self.parse_assignment()

    def parse_assignment(self) -> Expr:
        expr = self.parse_logical_or()
        if self.lexer.peek().kind == TokenType.EQ:
            self.lexer.next()
            value = self.parse_assignment()
            return Assign('=', expr, value)
        return expr

    def parse_logical_or(self) -> Expr:
        expr = self.parse_logical_and()
        while self.lexer.peek().kind == TokenType.OROR:
            op = self.lexer.next().value
            rhs = self.parse_logical_and()
            expr = Binary(op, expr, rhs)
        return expr

    def parse_logical_and(self) -> Expr:
        expr = self.parse_equality()
        while self.lexer.peek().kind == TokenType.ANDAND:
            op = self.lexer.next().value
            rhs = self.parse_equality()
            expr = Binary(op, expr, rhs)
        return expr

    def parse_equality(self) -> Expr:
        expr = self.parse_comparison()
        while self.lexer.peek().kind in (TokenType.EQEQ, TokenType.NEQ):
            op = self.lexer.next().value
            rhs = self.parse_comparison()
            expr = Binary(op, expr, rhs)
        return expr

    def parse_comparison(self) -> Expr:
        expr = self.parse_term()
        while self.lexer.peek().kind in (TokenType.LT, TokenType.GT, TokenType.LE, TokenType.GE):
            op = self.lexer.next().value
            rhs = self.parse_term()
            expr = Binary(op, expr, rhs)
        return expr

    def parse_term(self) -> Expr:
        expr = self.parse_factor()
        while self.lexer.peek().kind in (TokenType.PLUS, TokenType.MINUS):
            op = self.lexer.next().value
            rhs = self.parse_factor()
            expr = Binary(op, expr, rhs)
        return expr

    def parse_factor(self) -> Expr:
        expr = self.parse_unary()
        while self.lexer.peek().kind in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self.lexer.next().value
            rhs = self.parse_unary()
            expr = Binary(op, expr, rhs)
        return expr

    def parse_unary(self) -> Expr:
        tok = self.lexer.peek()
        if tok.kind in (TokenType.PLUS, TokenType.MINUS, TokenType.BANG):
            op = self.lexer.next().value
            right = self.parse_unary()
            return Unary(op, right)
        return self.parse_primary()

    def parse_primary(self) -> Expr:
        tok = self.lexer.peek()
        if tok.kind == TokenType.INT:
            return IntLiteral(self.lexer.next().value)
        elif tok.kind == TokenType.STRING:
            return StringLiteral(self.lexer.next().value)
        elif tok.kind == TokenType.IDENT:
            return Identifier(self.lexer.next().value)
        elif tok.kind == TokenType.LPAR:
            self.lexer.next()
            expr = self.parse_expression()
            self.lexer.expect('RPAR', ')')
            return expr
        else:
            raise SyntaxError(f"Unexpected token: {tok.kind.name} {tok.value} on line {tok.line_num}")


# =======================
# Z80 Code Generator
# =======================

class CodeGenerator:
    def __init__(self, rom_start: int, ram_start: int):
        self.label_counter = 0
        self.symbol_table = {}
        self.rom_start = rom_start
        self.ram_start = ram_start
        self.ram_address = ram_start
        self.registers = ['A', 'B', 'C', 'D', 'E', 'H', 'L']
        self.reg_stack = ['A', 'B', 'C', 'D', 'E', 'H', 'L']
        self.variables = []

    def allocate_reg(self) -> str:
        if not self.reg_stack:
            raise Exception("No more registers available")
        return self.reg_stack.pop()

    def free_reg(self, reg: str):
        self.reg_stack.append(reg)

    def get_var_address(self, var_name: str) -> str:
        if var_name not in self.symbol_table:
            self.symbol_table[var_name] = self.ram_address
            self.ram_address += 1 # Assuming 1 byte for simplicity
            self.variables.append(var_name)
        return hex(self.symbol_table[var_name]).upper().replace('0X', '') + 'h'

    def generate_label(self, prefix: str) -> str:
        label = f"{prefix}_{self.label_counter}"
        self.label_counter += 1
        return label

    def visit(self, node: Any) -> str:
        method_name = f"visit_{type(node).__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: Any) -> str:
        raise TypeError(f"No visit_{type(node).__name__} method defined")

    def visit_Program(self, node: Program) -> str:
        code = [
            f"; asez80 Assembly Code generated by mini-language compiler",
            f".rom\t{hex(self.rom_start).upper().replace('0X', '')}h",
            ""
        ]
        
        # Add function definitions
        for decl in node.decls:
            code.append(self.visit(decl))
        
        code.append("")
        code.append(f"; === RAM variables ===")
        code.append(f".ram\t{hex(self.ram_start).upper().replace('0X', '')}h")
        for var_name in sorted(self.symbol_table.keys()):
            address = hex(self.symbol_table[var_name]).upper().replace('0X', '') + 'h'
            code.append(f"_{var_name}:\t.db\t0\t; at {address}")

        code.append("")
        code.append(f".end")
        
        return "\n".join(code)

    def visit_FuncDecl(self, node: FuncDecl) -> str:
        code = [f"{node.name}:"]
        # Save registers on the stack
        code.append("\tPUSH\tIX")
        code.append("\tPUSH\tBC")
        code.append("\tPUSH\tDE")
        # Function body
        code.append(self.visit(node.body))
        # Restore registers and return
        code.append("\tPOP\tDE")
        code.append("\tPOP\tBC")
        code.append("\tPOP\tIX")
        code.append("\tRET")
        return "\n".join(code)
    
    def visit_Block(self, node: Block) -> str:
        code = []
        for stmt in node.statements:
            code.append(self.visit(stmt))
        return "\n".join(code)

    def visit_IfStmt(self, node: IfStmt) -> str:
        end_label = self.generate_label("IF_END")
        
        # Evaluate the condition expression
        cond_code, cond_reg = self.visit_expression(node.cond)
        self.free_reg(cond_reg)
        code = [cond_code]
        
        # Check if condition is false (0)
        code.append(f"\tOR\tA")
        
        if node.else_stmt:
            else_label = self.generate_label("IF_ELSE")
            code.append(f"\tJP\tZ,{else_label}")
        else:
            code.append(f"\tJP\tZ,{end_label}")

        # Compile 'then' block
        code.append(self.visit(node.then_stmt))
        
        if node.else_stmt:
            code.append(f"\tJP\t{end_label}")
            code.append(f"{else_label}:")
            code.append(self.visit(node.else_stmt))

        code.append(f"{end_label}:")
        return "\n".join(code)

    def visit_WhileStmt(self, node: WhileStmt) -> str:
        start_label = self.generate_label("WHILE_START")
        end_label = self.generate_label("WHILE_END")
        
        code = [f"{start_label}:"]
        
        # Evaluate condition
        cond_code, cond_reg = self.visit_expression(node.cond)
        self.free_reg(cond_reg)
        code.append(cond_code)
        
        # Check if condition is false (0)
        code.append(f"\tOR\tA")
        code.append(f"\tJP\tZ,{end_label}")

        # Compile loop body
        code.append(self.visit(node.body))
        
        # Jump back to the start
        code.append(f"\tJP\t{start_label}")
        code.append(f"{end_label}:")
        
        return "\n".join(code)

    def visit_ReturnStmt(self, node: ReturnStmt) -> str:
        code = []
        if node.value:
            # Evaluate expression and store result in A register
            expr_code, expr_reg = self.visit_expression(node.value)
            self.free_reg(expr_reg)
            code.append(expr_code)
            if expr_reg != 'A':
                code.append(f"\tLD\tA,{expr_reg}")
        code.append("\tRET")
        return "\n".join(code)

    def visit_ExprStmt(self, node: ExprStmt) -> str:
        # Evaluate the expression and discard the result
        code, reg = self.visit_expression(node.expr)
        self.free_reg(reg)
        return code

    def visit_Assign(self, node: Assign) -> tuple[str, str]:
        if isinstance(node.target, Identifier):
            # Evaluate value expression
            value_code, value_reg = self.visit_expression(node.value)
            
            # Store value in memory
            var_name = node.target.name
            code = [
                value_code,
                f"\tLD\t(_{var_name}),{value_reg}"
            ]
            self.free_reg(value_reg)
            
            # Return no-op result
            return "\n".join(code), 'A'
        else:
            raise TypeError("Only Identifier can be assigned to.")

    def visit_expression(self, node: Expr) -> tuple[str, str]:
        # A helper method to dispatch to the correct visitor for expressions
        method_name = f"visit_{type(node).__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def visit_Binary(self, node: Binary) -> tuple[str, str]:
        left_code, left_reg = self.visit_expression(node.left)
        right_code, right_reg = self.visit_expression(node.right)
        
        code = [left_code, right_code]
        result_reg = self.allocate_reg()
        
        if node.op == '+':
            code.append(f"\tLD\tA,{left_reg}")
            code.append(f"\tADD\tA,{right_reg}")
            code.append(f"\tLD\t{result_reg},A")
        elif node.op == '-':
            code.append(f"\tLD\tA,{left_reg}")
            code.append(f"    SUB\tA,{right_reg}")
            code.append(f"\tLD\t{result_reg},A")
        elif node.op == '*':
            # Simple multiplication using a loop for example
            mul_label = self.generate_label("MUL_LOOP")
            end_mul_label = self.generate_label("MUL_END")
            code.append(f"\tLD\tA,{left_reg}")
            code.append(f"\tLD\tB,{right_reg}")
            code.append(f"\tLD\tC,0") # Result
            code.append(f"{mul_label}:")
            code.append(f"\tOR\tB")
            code.append(f"\tJP\tZ,{end_mul_label}")
            code.append(f"\tADD\tC,A")
            code.append(f"\tDEC\tB")
            code.append(f"\tJP\t{mul_label}")
            code.append(f"{end_mul_label}:")
            code.append(f"\tLD\t{result_reg},C")
        elif node.op == '>':
            # Comparison: A > B -> result is 1 or 0
            true_label = self.generate_label("GT_TRUE")
            end_label = self.generate_label("GT_END")
            
            code.append(f"\tLD\tA,{left_reg}")
            code.append(f"\tCP\t{right_reg}")
            
            code.append(f"\tJR\tC,{true_label}")
            code.append(f"\tLD\t{result_reg},0")
            code.append(f"\tJP\t{end_label}")
            code.append(f"{true_label}:")
            code.append(f"\tLD\t{result_reg},1")
            code.append(f"{end_label}:")

        self.free_reg(left_reg)
        self.free_reg(right_reg)
        
        return "\n".join(code), result_reg

    def visit_Identifier(self, node: Identifier) -> tuple[str, str]:
        var_name = node.name
        # Register a variable if it's the first time we see it
        self.get_var_address(var_name)
        
        reg = self.allocate_reg()
        code = [f"\tLD\t{reg},(_{var_name})"]
        return "\n".join(code), reg

    def visit_IntLiteral(self, node: IntLiteral) -> tuple[str, str]:
        reg = self.allocate_reg()
        code = f"\tLD\t{reg},{node.value}"
        return code, reg

# =====================
# Command Line Interface
# =====================
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python main.py <source_file>")
        sys.exit(1)

    source_file = sys.argv[1]
    
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            code = f.read()

        lexer = Lexer(code)
        parser = Parser(lexer)
        ast = parser.parse_program()
        
        # ROMとRAMのアドレスを指定してCodeGeneratorをインスタンス化
        # 実際にはコンパイラオプションとして受け取るとより良い
        rom_start_address = 0x8000
        ram_start_address = 0xC000
        
        generator = CodeGenerator(rom_start=rom_start_address, ram_start=ram_start_address)
        z80_code = generator.visit(ast)
        
        # 出力
        print(z80_code)

    except FileNotFoundError:
        print(f"Error: The file '{source_file}' was not found.")
        sys.exit(1)
    except SyntaxError as e:
        print(f"Syntax Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)
