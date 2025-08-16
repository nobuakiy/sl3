from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Any
from enum import Enum, auto

# =======================
# AST ノード定義
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

import re
import sys

# =====================
# Token 定義
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
        tok = self.next()
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
        return ('Program', nodes)

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
            return ('ExprStmt', expr)

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
        return ('If', cond, then_stmt, else_stmt)

    def parse_while(self):
        self.lexer.expect('ID', 'while')
        self.lexer.expect('PUNCT', '(')
        cond = self.parse_expression()
        self.lexer.expect('PUNCT', ')')
        body = self.parse_statement()
        return ('While', cond, body)

    def parse_return(self):
        self.lexer.expect('ID', 'return')
        expr = self.parse_expression()
        self.lexer.expect('PUNCT', ';')
        return ('Return', expr)

    def parse_block(self):
        self.lexer.expect('PUNCT', '{')
        stmts = []
        while self.lexer.peek() != ('PUNCT', '}'):
            stmts.append(self.parse_statement())
        self.lexer.expect('PUNCT', '}')
        return ('Block', stmts)

    # ---------- Expression ----------
    def parse_expression(self):
        return self.parse_assignment()

    def parse_assignment(self):
        expr = self.parse_logical_or()
        if self.lexer.peek() == ('OP', '='):
            self.lexer.next()
            value = self.parse_assignment()
            return ('Assign', expr, value)
        return expr

    def parse_logical_or(self):
        expr = self.parse_logical_and()
        while self.lexer.peek() == ('OP', '||'):
            op = self.lexer.next()[1]
            rhs = self.parse_logical_and()
            expr = ('BinOp', op, expr, rhs)
        return expr

    def parse_logical_and(self):
        expr = self.parse_equality()
        while self.lexer.peek() == ('OP', '&&'):
            op = self.lexer.next()[1]
            rhs = self.parse_equality()
            expr = ('BinOp', op, expr, rhs)
        return expr

    def parse_equality(self):
        expr = self.parse_comparison()
        while self.lexer.peek()[1] in ('==', '!='):
            op = self.lexer.next()[1]
            rhs = self.parse_comparison()
            expr = ('BinOp', op, expr, rhs)
        return expr

    def parse_comparison(self):
        expr = self.parse_term()
        while self.lexer.peek()[1] in ('<', '>', '<=', '>='):
            op = self.lexer.next()[1]
            rhs = self.parse_term()
            expr = ('BinOp', op, expr, rhs)
        return expr

    def parse_term(self):
        expr = self.parse_factor()
        while self.lexer.peek()[1] in ('+', '-'):
            op = self.lexer.next()[1]
            rhs = self.parse_factor()
            expr = ('BinOp', op, expr, rhs)
        return expr

    def parse_factor(self):
        expr = self.parse_unary()
        while self.lexer.peek()[1] in ('*', '/', '%'):
            op = self.lexer.next()[1]
            rhs = self.parse_unary()
            expr = ('BinOp', op, expr, rhs)
        return expr

    def parse_unary(self):
        tok = self.lexer.peek()
        if tok[1] in ('+', '-', '!', '~'):
            op = self.lexer.next()[1]
            right = self.parse_unary()
            return ('UnaryOp', op, right)
        return self.parse_primary()

    def parse_primary(self):
        tok = self.lexer.peek()
        if tok[0] == 'NUMBER':
            return ('Number', self.lexer.next()[1])
        elif tok[0] == 'STRING':
            return ('String', self.lexer.next()[1])
        elif tok[0] == 'ID':
            return ('Var', self.lexer.next()[1])
        elif tok == ('PUNCT', '('):
            self.lexer.next()
            expr = self.parse_expression()
            self.lexer.expect('PUNCT', ')')
            return expr
        else:
            raise SyntaxError(f'Unexpected token: {tok}')

# =====================
# 実行例
# =====================
if __name__ == '__main__':
    code = r'''
    if (x > 0) {
        return x + 1;
    } else {
        return 0;
    }
    '''
    lexer = Lexer(code)
    parser = Parser(lexer)
    ast = parser.parse_program()
    from pprint import pprint
    pprint(ast)