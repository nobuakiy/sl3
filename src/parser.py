# --- parser.py ---

# --- AST Node Definitions (追加) ---
class AST: pass

class Program(AST):
    def __init__(self, children):
        self.children = children

class VarDecl(AST):
    def __init__(self, type_node, var_node, initial_value=None):
        self.type_node = type_node
        self.var_node = var_node
        self.initial_value = initial_value
        
class Type(AST):
    def __init__(self, token):
        self.token = token; self.value = token.value

class Variable(AST):
    def __init__(self, token):
        self.token = token; self.value = token.value

class Number(AST): # 数値リテラルを表すノード
    def __init__(self, token):
        self.token = token; self.value = token.value

class BinOp(AST): # 二項演算を表すノード (例: left + right)
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

# --- Parser Implementation (拡張) ---
class Parser:
    def __init__(self, tokens):
        self.tokens = iter(tokens)
        self.current_token = None
        self.advance()
        # 演算子の優先順位を定義
        self.precedence = {
            'PLUS': 1, 'MINUS': 1,
            'MUL': 2, 'DIV': 2,
        }

    def advance(self):
        try: self.current_token = next(self.tokens)
        except StopIteration: self.current_token = None

    def eat(self, token_type):
        if self.current_token and self.current_token.type == token_type:
            self.advance()
        else: raise SyntaxError(f"Expected {token_type}, got {self.current_token}")

    def parse(self):
        declarations = []
        while self.current_token is not None:
            declarations.append(self.parse_declaration())
        return Program(declarations)
        
    def parse_declaration(self):
        # ここでは変数宣言のみを仮定
        type_node = self.parse_type()
        var_token = self.current_token
        self.eat('ID') # or UPPERCASE_ID for consts
        var_node = Variable(var_token)
        
        initial_value = None
        if self.current_token and self.current_token.type == 'ASSIGN':
            self.eat('ASSIGN')
            initial_value = self.parse_expression() # 式の解析を呼び出す

        self.eat('SEMICOLON')
        return VarDecl(type_node, var_node, initial_value)

    def parse_type(self):
        token = self.current_token
        if token.type in ('INT', 'BYTE', 'VOID'):
            self.advance()
            return Type(token)
        else: raise SyntaxError("Expected a type specifier")

    # --- Expression Parsing Logic ---
    def parse_expression(self, prec=0):
        node = self.parse_primary() # 数値や括弧などを解析
        
        while self.current_token and self.current_token.type in self.precedence and self.precedence[self.current_token.type] > prec:
            op_token = self.current_token
            self.advance()
            right_node = self.parse_expression(self.precedence[op_token.type])
            node = BinOp(left=node, op=op_token, right=right_node)
            
        return node

    def parse_primary(self):
        token = self.current_token
        if token.type == 'INTEGER':
            self.advance()
            return Number(token)
        # ここに括弧 `(expr)` や変数参照 `ID` の解析を追加
        else:
            raise SyntaxError(f"Unexpected token in expression: {token}")