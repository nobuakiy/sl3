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
    def __init__(self, code):
        self.tokens = []
        self.pos = 0
        self.tokenize(code)

    def tokenize(self, code):
        regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_REGEX)
        for mo in re.finditer(regex, code):
            kind = mo.lastgroup
            value = mo.group()
            if kind == 'NUMBER':
                self.tokens.append(('NUMBER', int(value)))
            elif kind == 'ID':
                if value in KEYWORDS:
                    self.tokens.append(('ID', value))
                else:
                    self.tokens.append(('ID', value))
            elif kind == 'STRING':
                self.tokens.append(('STRING', value[1:-1]))
            elif kind == 'OP':
                self.tokens.append(('OP', value))
            elif kind == 'PUNCT':
                self.tokens.append(('PUNCT', value))
            elif kind == 'NEWLINE' or kind == 'SKIP':
                continue
            elif kind == 'MISMATCH':
                raise SyntaxError(f'Unexpected character: {value}')
        self.tokens.append(('EOF', None))

    def peek(self):
        return self.tokens[self.pos]

    def next(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, kind, value=None):
        tok = self.tokens[self.pos]
        if tok[0] != kind or (value is not None and tok[1] != value):
            raise SyntaxError(f'Expected {kind} {value}, got {tok}')
        return tok

# =====================
# Parser
# =====================
class Parser:
    def __init__(self, lexer):
        self.lexer = lexer

    def parse_program(self):
        nodes = []
        while self.lexer.peek()[0] != 'EOF':
            nodes.append(self.parse_statement())
        return Program(nodes)

    # ---------- Statement ----------
    def parse_statement(self):
        tok = self.lexer.peek()
        if tok == ('ID', 'if'):
            return self.parse_if()
        elif tok == ('ID', 'while'):
            return self.parse_while()
        elif tok == ('ID', 'return'):
            return self.parse_return()
        elif tok == ('PUNCT', '{'):
            return self.parse_block()
        else:
            expr = self.parse_expression()
            self.lexer.expect('PUNCT', ';')
            return ExprStmt(expr)

    def parse_if(self):
        self.lexer.expect('ID', 'if')
        self.lexer.expect('PUNCT', '(')
        cond = self.parse_expression()
        self.lexer.expect('PUNCT', ')')
        then_stmt = self.parse_statement()
        else_stmt = None
        if self.lexer.peek() == ('ID', 'else'):
            self.lexer.next()
            else_stmt = self.parse_statement()
        return IfStmt(cond, then_stmt, else_stmt)

    def parse_while(self):
        self.lexer.expect('ID', 'while')
        self.lexer.expect('PUNCT', '(')
        cond = self.parse_expression()
        self.lexer.expect('PUNCT', ')')
        body = self.parse_statement()
        return WhileStmt(cond, body)

    def parse_return(self):
        self.lexer.expect('ID', 'return')
        expr = self.parse_expression()
        self.lexer.expect('PUNCT', ';')
        return ReturnStmt(expr)

    def parse_block(self):
        self.lexer.expect('PUNCT', '{')
        stmts = []
        while self.lexer.peek() != ('PUNCT', '}'):
            stmts.append(self.parse_statement())
        self.lexer.expect('PUNCT', '}')
        return Block(stmts)

    # ---------- Expression ----------
    def parse_expression(self):
        return self.parse_assignment()

    def parse_assignment(self):
        expr = self.parse_logical_or()
        if self.lexer.peek() == ('OP', '='):
            self.lexer.next()
            value = self.parse_assignment()
            return Assign('=', expr, value)
        return expr

    def parse_logical_or(self):
        expr = self.parse_logical_and()
        while self.lexer.peek() == ('OP', '||'):
            op = self.lexer.next()[1]
            rhs = self.parse_logical_and()
            expr = Binary(op, expr, rhs)
        return expr

    def parse_logical_and(self):
        expr = self.parse_equality()
        while self.lexer.peek() == ('OP', '&&'):
            op = self.lexer.next()[1]
            rhs = self.parse_equality()
            expr = Binary(op, expr, rhs)
        return expr

    def parse_equality(self):
        expr = self.parse_comparison()
        while self.lexer.peek()[1] in ('==', '!='):
            op = self.lexer.next()[1]
            rhs = self.parse_comparison()
            expr = Binary(op, expr, rhs)
        return expr

    def parse_comparison(self):
        expr = self.parse_term()
        while self.lexer.peek()[1] in ('<', '>', '<=', '>='):
            op = self.lexer.next()[1]
            rhs = self.parse_term()
            expr = Binary(op, expr, rhs)
        return expr

    def parse_term(self):
        expr = self.parse_factor()
        while self.lexer.peek()[1] in ('+', '-'):
            op = self.lexer.next()[1]
            rhs = self.parse_factor()
            expr = Binary(op, expr, rhs)
        return expr

    def parse_factor(self):
        expr = self.parse_unary()
        while self.lexer.peek()[1] in ('*', '/', '%'):
            op = self.lexer.next()[1]
            rhs = self.parse_unary()
            expr = Binary(op, expr, rhs)
        return expr

    def parse_unary(self):
        tok = self.lexer.peek()
        if tok[1] in ('+', '-', '!', '~'):
            op = self.lexer.next()[1]
            right = self.parse_unary()
            return Unary(op, right)
        return self.parse_primary()

    def parse_primary(self):
        tok = self.lexer.peek()
        if tok[0] == 'NUMBER':
            return IntLiteral(self.lexer.next()[1])
        elif tok[0] == 'STRING':
            return StringLiteral(self.lexer.next()[1])
        elif tok[0] == 'ID':
            return Identifier(self.lexer.next()[1])
        elif tok == ('PUNCT', '('):
            self.lexer.next()
            expr = self.parse_expression()
            self.lexer.expect('PUNCT', ')')
            return expr
        else:
            raise SyntaxError(f'Unexpected token: {tok}')

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
            code.append(f"\tSUB\tA,{right_reg}")
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
