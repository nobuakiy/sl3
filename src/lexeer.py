import re
import sys

class Token:
    def __init__(self, type, value=None):
        self.type = type
        self.value = value
    def __repr__(self):
        return f"Token({self.type}, {self.value})"

class Lexer:
    def __init__(self, code):
        self.code = code
        self.tokens = []
        self.token_specs = [
            # Keywords (order matters)
            ('CONST',      r'const'),
            ('INT',        r'int'),
            ('BYTE',       r'byte'),
            ('VOID',       r'void'),
            ('IF',         r'if'),
            ('ELSE',       r'else'),
            ('FOR',        r'for'),
            ('IN',         r'in'),
            ('DO',         r'do'),
            ('WHILE',      r'while'),
            ('RETURN',     r'return'),
            ('MEM',        r'MEM'),
            # Data Types that can be identifiers
            ('STRINGBUFFER', r'StringBuffer'),
            # Identifiers
            ('UPPERCASE_ID', r'[A-Z_][A-Z0-9_]*'),
            ('ID',         r'[a-z_][a-zA-Z0-9_]*'),
            # Literals
            ('INTEGER',    r'0x[0-9a-fA-F]+|[0-9]+'),
            ('STRING',     r'"[^"]*"'),
            # Operators and Delimiters
            ('LSHIFT',     r'<<'),
            ('RSHIFT',     r'>>'),
            ('EQ',         r'=='),
            ('NE',         r'!='),
            ('LE',         r'<='),
            ('GE',         r'>='),
            ('PLUS_EQ',    r'\+='),
            ('MINUS_EQ',   r'-='),
            ('LPAREN',     r'\('),
            ('RPAREN',     r'\)'),
            ('LBRACKET',   r'\['),
            ('RBRACKET',   r'\]'),
            ('LBRACE',     r'\{'),
            ('RBRACE',     r'\}'),
            ('COMMA',      r','),
            ('DOT',        r'\.'),
            ('PLUS',       r'\+'),
            ('MINUS',      r'-'),
            ('MUL',        r'\*'),
            ('DIV',        r'/'),
            ('ASSIGN',     r'='),
            ('LT',         r'<'),
            ('GT',         r'>'),
            ('AMPERSAND',  r'&'),
            ('PIPE',       r'\|'),
            ('CARET',      r'\^'),
            ('SEMICOLON',  r';'),
            # Misc
            ('NEWLINE',    r'\n'),
            ('SKIP',       r'[ \t]+'),
            ('MISMATCH',   r'.'),
        ]
        self.token_regex = '|'.join('(?P<%s>%s)' % pair for pair in self.token_specs)

    def tokenize(self):
        for mo in re.finditer(self.token_regex, self.code):
            kind = mo.lastgroup
            value = mo.group()
            if kind == 'INTEGER':
                if value.startswith('0x'):
                    value = int(value, 16)
                else:
                    value = int(value)
            elif kind == 'STRING':
                value = value[1:-1] # Strip quotes
            elif kind in ['SKIP', 'NEWLINE']:
                continue
            elif kind == 'MISMATCH':
                raise RuntimeError(f'Unexpected character: {value}')
            yield Token(kind, value)