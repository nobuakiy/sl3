from __future__ import annotations
import re
from typing import Any, Generator

class Token:
    """トークンを表すクラス"""
    def __init__(self, type: str, value: Any = None, line: int = 0, column: int = 0):
        self.type: str = type
        self.value: Any = value
        self.line: int = line
        self.column: int = column
    def __repr__(self) -> str:
        return f"Token({self.type}, {repr(self.value)})"

class Lexer:
    """ソースコードをトークンのストリームに変換する"""
    def __init__(self, code: str):
        self.code: str = code
        # トークンの正規表現定義
        self.token_specs: list[tuple[str, str]] = [
            ('COMMENT',    r'//.*'),
            ('CONST',      r'const'),
            ('INT',        r'int'),
            ('BYTE',       r'byte'),
            ('VOID',       r'void'),
            ('IF',         r'if'),
            ('ELSE',       r'else'),
            ('WHILE',      r'while'),
            ('RETURN',     r'return'),
            ('FOR',        r'for'), ('IN', r'in'), ('DO', r'do'),
            ('STRINGBUFFER', r'StringBuffer'),
            ('ID',         r'[a-zA-Z_][a-zA-Z0-9_]*'),
            ('INTEGER',    r'0x[0-9a-fA-F]+|[0-9]+'),
            ('STRING',     r'"[^"]*"'),
            ('EQ', r'=='), ('NE', r'!='), ('LE', r'<='), ('GE', r'>='),
            ('LPAREN', r'\('), ('RPAREN', r'\)'), ('LBRACKET', r'\['),
            ('RBRACKET', r'\]'), ('LBRACE', r'\{'), ('RBRACE', r'\}'),
            ('COMMA', r','), ('PLUS', r'\+'), ('MINUS', r'-'),
            ('MUL', r'\*'), ('DIV', r'/'), ('ASSIGN', r'='),
            ('LT', r'<'), ('GT', r'>'), ('SEMICOLON', r';'),
            ('NEWLINE',    r'\n'),
            ('SKIP',       r'[ \t]+'),
            ('MISMATCH',   r'.'),
        ]
        self.token_regex: str = '|'.join(f'(?P<{pair[0]}>{pair[1]})' for pair in self.token_specs)

    def tokenize(self) -> Generator[Token, None, None]:
        line_num: int = 1
        line_start: int = 0
        for mo in re.finditer(self.token_regex, self.code):
            kind: str = mo.lastgroup
            value: str | int = mo.group()
            column: int = mo.start() - line_start

            if kind == 'INTEGER':
                value = int(value, 16) if value.startswith('0x') else int(value)
            elif kind == 'STRING':
                value = value[1:-1]
            elif kind == 'NEWLINE':
                line_start = mo.end()
                line_num += 1
                continue
            elif kind in ['COMMENT', 'SKIP']:
                continue
            elif kind == 'MISMATCH':
                raise RuntimeError(f'{value!r} unexpected on line {line_num}')
            
            yield Token(kind, value, line_num, column)