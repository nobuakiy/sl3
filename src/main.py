from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Union, Tuple, Any
from enum import Enum, auto

# === AST nodes ===

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
    name: str  # "int" | "byte" | "StringBuffer" | "bool" | user ident

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
    op: str  # '=', '+=', ...
    target: "Expr"  # must be lvalue (Identifier/ArrayAccess/BitAccess)
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
    callee: "Expr"  # allow Identifier or further postfix
    args: List[Expr]

@dataclass
class ArrayAccess(Expr):
    array: Expr
    index: Expr

@dataclass
class BitAccess(Expr):
    base: Expr
    bit: int  # 0..7

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
class LambdaExpr(Expr):
    params: List[Param]  # start with empty param lambda support
    body: Block


# === Lexer ===

class TokenType(Enum):
    # single-char
    LPAR = auto(); RPAR = auto()
    LBRACE = auto(); RBRACE = auto()
    LBRACK = auto(); RBRACK = auto()
    COMMA = auto(); SEMI = auto(); DOT = auto()
    PLUS = auto(); MINUS = auto(); STAR = auto(); SLASH = auto(); PERCENT = auto()
    BANG = auto()
    LT = auto(); GT = auto(); EQ = auto()
    AMP = auto(); BAR = auto()
    # multi-char
    EQEQ = auto(); NEQ = auto()
    LE = auto(); GE = auto()
    ANDAND = auto(); OROR = auto()
    PLUSEQ = auto(); MINUSEQ = auto(); STAREQ = auto(); SLASHEQ = auto()
    ARROW = auto()  # =>
    # literals / id
    IDENT = auto(); INT = auto(); STRING = auto()
    # keywords
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

class Lexer:
    def __init__(self, src: str):
        self.s = src
        self.i = 0
        self.n = len(src)

    def _peek(self, k=0) -> str:
        j = self.i + k
        return self.s[j] if j < self.n else "\0"

    def _adv(self) -> str:
        ch = self._peek()
        self.i += 1
        return ch

    def tokens(self) -> List[Token]:
        toks: List[Token] = []
        while True:
            self._skip_ws_and_comments()
            pos = self.i
            ch = self._peek()
            if ch == "\0":
                toks.append(Token(TokenType.EOF, "", None, pos))
                break
            # strings
            if ch == '"':
                toks.append(self._string())
                continue
            # numbers (int / hex)
            if ch.isdigit():
                toks.append(self._number())
                continue
            # identifiers / keywords
            if ch.isalpha() or ch == "_":
                toks.append(self._ident_or_kw())
                continue
            # operators / punctuation
            two = ch + self._peek(1)
            three = two + self._peek(2)

            # multi-char first
            if two == "==": toks.append(Token(TokenType.EQEQ, "==", None, pos)); self.i += 2; continue
            if two == "!=": toks.append(Token(TokenType.NEQ, "!=", None, pos)); self.i += 2; continue
            if two == "<=": toks.append(Token(TokenType.LE, "<=", None, pos)); self.i += 2; continue
            if two == ">=": toks.append(Token(TokenType.GE, ">=", None, pos)); self.i += 2; continue
            if two == "&&": toks.append(Token(TokenType.ANDAND, "&&", None, pos)); self.i += 2; continue
            if two == "||": toks.append(Token(TokenType.OROR, "||", None, pos)); self.i += 2; continue
            if two == "+=": toks.append(Token(TokenType.PLUSEQ, "+=", None, pos)); self.i += 2; continue
            if two == "-=": toks.append(Token(TokenType.MINUSEQ, "-=", None, pos)); self.i += 2; continue
            if two == "*=": toks.append(Token(TokenType.STAREQ, "*=", None, pos)); self.i += 2; continue
            if two == "/=": toks.append(Token(TokenType.SLASHEQ, "/=", None, pos)); self.i += 2; continue
            if two == "=>": toks.append(Token(TokenType.ARROW, "=>", None, pos)); self.i += 2; continue

            # single-char
            single_map = {
                "(": TokenType.LPAR, ")": TokenType.RPAR,
                "{": TokenType.LBRACE, "}": TokenType.RBRACE,
                "[": TokenType.LBRACK, "]": TokenType.RBRACK,
                ",": TokenType.COMMA, ";": TokenType.SEMI, ".": TokenType.DOT,
                "+": TokenType.PLUS, "-": TokenType.MINUS, "*": TokenType.STAR, "/": TokenType.SLASH, "%": TokenType.PERCENT,
                "!": TokenType.BANG, "<": TokenType.LT, ">": TokenType.GT, "=": TokenType.EQ,
                "&": TokenType.AMP, "|": TokenType.BAR,
            }
            if ch in single_map:
                toks.append(Token(single_map[ch], ch, None, pos))
                self.i += 1
                continue

            raise SyntaxError(f"Unexpected character '{ch}' at {pos}")
        return toks

    def _skip_ws_and_comments(self):
        while True:
            ch = self._peek()
            if ch in " \t\r\n":
                self.i += 1
                continue
            # line comment //
            if ch == "/" and self._peek(1) == "/":
                while self._peek() not in ("\n", "\0"):
                    self.i += 1
                continue
            # block comment /* ... */
            if ch == "/" and self._peek(1) == "*":
                self.i += 2
                while not (self._peek() == "*" and self._peek(1) == "/"):
                    if self._peek() == "\0":
                        raise SyntaxError("Unterminated block comment")
                    self.i += 1
                self.i += 2
                continue
            break

    def _string(self) -> Token:
        pos = self.i
        assert self._adv() == '"'
        buf = []
        while True:
            ch = self._adv()
            if ch == "\0":
                raise SyntaxError(f"Unterminated string at {pos}")
            if ch == '"':
                break
            if ch == "\\":
                esc = self._adv()
                m = {"n":"\n", "r":"\r", "t":"\t", '"':'"', "\\":"\\"}
                buf.append(m.get(esc, esc))
            else:
                buf.append(ch)
        return Token(TokenType.STRING, "".join(buf), "".join(buf), pos)

    def _number(self) -> Token:
        pos = self.i
        if self._peek() == "0" and self._peek(1) in ("x", "X"):
            self.i += 2
            start = self.i
            while self._peek().isalnum():
                self.i += 1
            s = self.s[start:self.i]
            v = int(s, 16)
            return Token(TokenType.INT, s, v, pos)
        start = self.i
        while self._peek().isdigit():
            self.i += 1
        s = self.s[start:self.i]
        return Token(TokenType.INT, s, int(s), pos)

    def _ident_or_kw(self) -> Token:
        pos = self.i
        start = self.i
        while self._peek().isalnum() or self._peek() == "_":
            self.i += 1
        s = self.s[start:self.i]
        kind = KEYWORDS.get(s, TokenType.IDENT)
        if kind == TokenType.IDENT:
            return Token(kind, s, s, pos)
        return Token(kind, s, s, pos)


# === Parser ===

class ParseError(Exception): ...

class Parser:
    def __init__(self, tokens: List[Token]):
        self.toks = tokens
        self.i = 0

    # ------------- utilities -------------
    def _peek(self, k=0) -> Token:
        j = self.i + k
        return self.toks[j] if j < len(self.toks) else self.toks[-1]

    def _match(self, *kinds: TokenType) -> Optional[Token]:
        if self._peek().kind in kinds:
            t = self._peek()
            self.i += 1
            return t
        return None

    def _expect(self, kind: TokenType, msg: str = "") -> Token:
        t = self._peek()
        if t.kind != kind:
            raise ParseError(msg or f"Expected {kind.name}, got {t.kind.name} at {t.pos}")
        self.i += 1
        return t

    def _is_type_start(self) -> bool:
        k = self._peek().kind
        if k in (TokenType.INTKW, TokenType.BYTEKW, TokenType.STRBUF, TokenType.BOOLKW):
            return True
        # user-defined type: IDENT IDENT pattern
        return (k == TokenType.IDENT) and (self._peek(1).kind == TokenType.IDENT)

    # ------------- entry -------------
    def parse_program(self) -> Program:
        decls: List[Decl] = []
        while self._peek().kind != TokenType.EOF:
            decls.append(self.parse_declaration())
        return Program(decls)

    # ------------- declarations -------------
    def parse_declaration(self) -> Decl:
        # module | struct | func | var
        if self._peek().kind == TokenType.MODULE:
            return self.parse_module()
        if self._peek().kind == TokenType.STRUCT:
            return self.parse_struct()
        # otherwise starts with type
        tnode = self.parse_type()
        name_tok = self._expect(TokenType.IDENT, "Expected identifier after type")
        name = name_tok.value

        if self._match(TokenType.LPAR):  # function
            params = self.parse_param_list_opt()
            self._expect(TokenType.RPAR, "Expected ')' after parameters")
            body = self.parse_block()
            return FuncDecl(tnode, name, params, body)

        # variable (optional array and initializer)
        array_size = None
        if self._match(TokenType.LBRACK):
            size_tok = self._expect(TokenType.INT, "Array size must be integer literal")
            array_size = int(size_tok.value)
            self._expect(TokenType.RBRACK, "Expected ']' after array size")

        init: Optional[Expr] = None
        if self._match(TokenType.EQ):
            if self._peek().kind == TokenType.LBRACE:
                init = self.parse_array_initializer()
            else:
                init = self.parse_expression()
        self._expect(TokenType.SEMI, "Expected ';' after variable declaration")
        return VarDecl(tnode, name, array_size, init)

    def parse_module(self) -> ModuleDecl:
        self._expect(TokenType.MODULE)
        name = self._expect(TokenType.IDENT, "Module name required").value
        self._expect(TokenType.LBRACE, "Expected '{' after module name")
        decls: List[Decl] = []
        while self._peek().kind != TokenType.RBRACE:
            decls.append(self.parse_declaration())
        self._expect(TokenType.RBRACE, "Expected '}' to close module")
        return ModuleDecl(name, decls)

    def parse_struct(self) -> StructDecl:
        self._expect(TokenType.STRUCT)
        name = self._expect(TokenType.IDENT, "Struct name required").value
        self._expect(TokenType.LBRACE, "Expected '{' in struct")
        fields: List[VarDecl] = []
        while self._peek().kind != TokenType.RBRACE:
            # only var decls inside struct
            tnode = self.parse_type()
            fname = self._expect(TokenType.IDENT, "Field name required").value
            fsize = None
            if self._match(TokenType.LBRACK):
                size_tok = self._expect(TokenType.INT, "Array size must be integer literal")
                fsize = int(size_tok.value)
                self._expect(TokenType.RBRACK, "Expected ']'")
            # no initializers in struct fields
            self._expect(TokenType.SEMI, "Expected ';' after field")
            fields.append(VarDecl(tnode, fname, fsize, None))
        self._expect(TokenType.RBRACE, "Expected '}' to close struct")
        return StructDecl(name, fields)

    def parse_param_list_opt(self) -> List[Param]:
        params: List[Param] = []
        if self._peek().kind == TokenType.RPAR:
            return params
        while True:
            t = self.parse_type()
            name = self._expect(TokenType.IDENT, "Parameter name required").value
            arr_size = None
            if self._match(TokenType.LBRACK):
                size_tok = self._expect(TokenType.INT, "Array size must be integer literal")
                arr_size = int(size_tok.value)
                self._expect(TokenType.RBRACK, "Expected ']'")
            params.append(Param(t, name, arr_size))
            if not self._match(TokenType.COMMA):
                break
        return params

    def parse_type(self) -> TypeNode:
        t = self._peek()
        if t.kind in (TokenType.INTKW, TokenType.BYTEKW, TokenType.STRBUF, TokenType.BOOLKW):
            self.i += 1
            return TypeNode(t.lexeme)
        # user defined type identifier
        name_tok = self._expect(TokenType.IDENT, "Type name expected")
        return TypeNode(name_tok.value)

    # ------------- statements -------------
    def parse_block(self) -> Block:
        self._expect(TokenType.LBRACE, "Expected '{'")
        stmts: List[Stmt] = []
        while self._peek().kind != TokenType.RBRACE:
            stmts.append(self.parse_statement())
        self._expect(TokenType.RBRACE, "Expected '}'")
        return Block(stmts)

    def parse_statement(self) -> Stmt:
        k = self._peek().kind
        if k == TokenType.LBRACE:
            return self.parse_block()
        if k == TokenType.IF:
            return self.parse_if()
        if k == TokenType.WHILE:
            return self.parse_while()
        if k == TokenType.RETURN:
            return self.parse_return()
        # local var-decl?
        if self._is_type_start():
            # re-parse type and var-decl path similar to top-level
            tnode = self.parse_type()
            name = self._expect(TokenType.IDENT, "Identifier required").value
            arr_size = None
            if self._match(TokenType.LBRACK):
                size_tok = self._expect(TokenType.INT, "Array size must be integer literal")
                arr_size = int(size_tok.value)
                self._expect(TokenType.RBRACK, "Expected ']'")
            init = None
            if self._match(TokenType.EQ):
                if self._peek().kind == TokenType.LBRACE:
                    init = self.parse_array_initializer()
                else:
                    init = self.parse_expression()
            self._expect(TokenType.SEMI, "Expected ';'")
            return VarDecl(tnode, name, arr_size, init)
        # expression statement
        expr = self.parse_expression()
        self._expect(TokenType.SEMI, "Expected ';' after expression")
        return ExprStmt(expr)

    def parse_if(self) -> IfStmt:
        self._expect(TokenType.IF)
        self._expect(TokenType.LPAR, "Expected '(' after if")
        cond = self.parse_expression()
        self._expect(TokenType.RPAR, "Expected ')'")
        then = self.parse_statement()
        else_stmt = None
        if self._match(TokenType.ELSE):
            else_stmt = self.parse_statement()
        return IfStmt(cond, then, else_stmt)

    def parse_while(self) -> WhileStmt:
        self._expect(TokenType.WHILE)
        self._expect(TokenType.LPAR)
        cond = self.parse_expression()
        self._expect(TokenType.RPAR)
        body = self.parse_statement()
        return WhileStmt(cond, body)

    def parse_return(self) -> ReturnStmt:
        self._expect(TokenType.RETURN)
        if self._peek().kind == TokenType.SEMI:
            self.i += 1
            return ReturnStmt(None)
        val = self.parse_expression()
        self._expect(TokenType.SEMI)
        return ReturnStmt(val)

    def parse_array_initializer(self) -> Expr:
        # Represent as a special Call node to a pseudo-func "initvec"? Simpler: return as a list literal in a custom node
        # Here we reuse Call with callee=Identifier("{") is awkward. Let's define a lightweight container:
        items: List[Expr] = []
        self._expect(TokenType.LBRACE)
        items.append(self.parse_expression())
        while self._match(TokenType.COMMA):
            items.append(self.parse_expression())
        self._expect(TokenType.RBRACE)
        # reuse a tiny wrapper:
        return ListLiteral(items)

@dataclass
class ListLiteral(Expr):
    items: List[Expr]
# Attach expression parsing to Parser

ASSIGN_OPS = {
    TokenType.EQ: "=",
    TokenType.PLUSEQ: "+=",
    TokenType.MINUSEQ: "-=",
    TokenType.STAREQ: "*=",
    TokenType.SLASHEQ: "/=",
}

class Parser(Parser):  # extend
    def parse_expression(self) -> Expr:
        return self.parse_assignment()

    def parse_assignment(self) -> Expr:
        left = self.parse_logical_or()
        tok = self._peek()
        if tok.kind in ASSIGN_OPS:
            op_tok = self._peek(); self.i += 1
            value = self.parse_assignment()  # right-associative
            return Assign(ASSIGN_OPS[op_tok.kind], self.ensure_lvalue(left), value)
        return left

    def ensure_lvalue(self, e: Expr) -> Expr:
        if isinstance(e, (Identifier, ArrayAccess, BitAccess)):
            return e
        raise ParseError("Left-hand side of assignment must be lvalue")

    def parse_logical_or(self) -> Expr:
        expr = self.parse_logical_and()
        while self._match(TokenType.OROR):
            right = self.parse_logical_and()
            expr = Binary("||", expr, right)
        return expr

    def parse_logical_and(self) -> Expr:
        expr = self.parse_equality()
        while self._match(TokenType.ANDAND):
            right = self.parse_equality()
            expr = Binary("&&", expr, right)
        return expr

    def parse_equality(self) -> Expr:
        expr = self.parse_comparison()
        while True:
            if self._match(TokenType.EQEQ):
                right = self.parse_comparison()
                expr = Binary("==", expr, right)
            elif self._match(TokenType.NEQ):
                right = self.parse_comparison()
                expr = Binary("!=", expr, right)
            else:
                break
        return expr

    def parse_comparison(self) -> Expr:
        expr = self.parse_term()
        while True:
            if self._match(TokenType.LT):
                right = self.parse_term(); expr = Binary("<", expr, right)
            elif self._match(TokenType.GT):
                right = self.parse_term(); expr = Binary(">", expr, right)
            elif self._match(TokenType.LE):
                right = self.parse_term(); expr = Binary("<=", expr, right)
            elif self._match(TokenType.GE):
                right = self.parse_term(); expr = Binary(">=", expr, right)
            else:
                break
        return expr

    def parse_term(self) -> Expr:
        expr = self.parse_factor()
        while True:
            if self._match(TokenType.PLUS):
                expr = Binary("+", expr, self.parse_factor())
            elif self._match(TokenType.MINUS):
                expr = Binary("-", expr, self.parse_factor())
            else:
                break
        return expr

    def parse_factor(self) -> Expr:
        expr = self.parse_unary()
        while True:
            if self._match(TokenType.STAR):
                expr = Binary("*", expr, self.parse_unary())
            elif self._match(TokenType.SLASH):
                expr = Binary("/", expr, self.parse_unary())
            elif self._match(TokenType.PERCENT):
                expr = Binary("%", expr, self.parse_unary())
            else:
                break
        return expr

    def parse_unary(self) -> Expr:
        if self._match(TokenType.BANG):
            return Unary("!", self.parse_unary())
        if self._match(TokenType.MINUS):
            return Unary("-", self.parse_unary())
        return self.parse_postfix()

    def parse_postfix(self) -> Expr:
        expr = self.parse_primary()
        while True:
            if self._match(TokenType.LPAR):
                # call
                args: List[Expr] = []
                if self._peek().kind != TokenType.RPAR:
                    args.append(self.parse_expression())
                    while self._match(TokenType.COMMA):
                        args.append(self.parse_expression())
                self._expect(TokenType.RPAR, "Expected ')' after arguments")
                expr = Call(expr, args)
                continue
            if self._match(TokenType.LBRACK):
                idx = self.parse_expression()
                self._expect(TokenType.RBRACK, "Expected ']' after index")
                expr = ArrayAccess(expr, idx)
                continue
            if self._match(TokenType.DOT):
                bit_tok = self._expect(TokenType.INT, "Bit index 0..7 required after '.'")
                bit = int(bit_tok.value)
                if not (0 <= bit <= 7):
                    raise ParseError("Bit index must be 0..7")
                expr = BitAccess(expr, bit)
                continue
            break
        return expr

    def parse_primary(self) -> Expr:
        t = self._peek()
        if t.kind == TokenType.INT:
            self.i += 1
            return IntLiteral(int(t.value))
        if t.kind == TokenType.STRING:
            self.i += 1
            return StringLiteral(t.value)
        if t.kind == TokenType.TRUE:
            self.i += 1
            return BoolLiteral(True)
        if t.kind == TokenType.FALSE:
            self.i += 1
            return BoolLiteral(False)
        if t.kind == TokenType.IDENT:
            self.i += 1
            return Identifier(t.value)
        if self._match(TokenType.LPAR):
            # try empty-params lambda: () => { ... }
            if self._match(TokenType.RPAR) and self._match(TokenType.ARROW):
                body = self.parse_block()
                return LambdaExpr(params=[], body=body)
            # otherwise parenthesized expr
            expr = self.parse_expression()
            self._expect(TokenType.RPAR, "Expected ')'")
            return expr
        raise ParseError(f"Unexpected token {t.kind.name} at {t.pos} in primary")


