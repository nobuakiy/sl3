# --- parser.py ---
from symbol_table import SymbolTable, VariableSymbol

# --- AST Node Definitions (追加) ---
# (Program, VarDecl, Type, Variable, Number, BinOpは前回と同じ)
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

class Assignment(AST):
    def __init__(self, left, right):
        self.left = left  # The variable to assign to
        self.right = right # The expression

class VarAccess(AST):
    def __init__(self, token):
        self.token = token
        self.value = token.value

# --- Parser Implementation (拡張) ---
class Parser:
    def __init__(self, tokens):
        self.symbol_table = SymbolTable()
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
        statements = []
        while self.current_token is not None:
            statements.append(self.parse_statement())
        return Program(statements)

    def parse_statement(self):
        # 型名から始まれば変数宣言
        if self.current_token.type in ('INT', 'BYTE'):
            return self.parse_variable_declaration()
        # 識別子から始まれば代入文
        elif self.current_token.type == 'ID':
            return self.parse_assignment_statement()
        else:
            raise SyntaxError("Invalid statement")
            
    def parse_variable_declaration(self):
        type_node = self.parse_type()
        var_token = self.current_token
        self.eat('ID')
        var_node = Variable(var_token)
        
        # シンボルテーブルに登録
        symbol = VariableSymbol(var_node.value, type_node.value)
        self.symbol_table.define(symbol)
        
        initial_value = None
        if self.current_token.type == 'ASSIGN':
            self.eat('ASSIGN')
            initial_value = self.parse_expression()

        self.eat('SEMICOLON')
        return VarDecl(type_node, var_node, initial_value)

    def parse_assignment_statement(self):
        var_token = self.current_token
        self.eat('ID')
        
        # 変数が宣言済みかチェック
        if not self.symbol_table.lookup(var_token.value):
            raise NameError(f"Variable '{var_token.value}' not declared")
            
        left_node = VarAccess(var_token)
        self.eat('ASSIGN')
        right_node = self.parse_expression()
        self.eat('SEMICOLON')
        return Assignment(left_node, right_node)

    # ... (parse_type, parse_expressionは前回と同じ) ...
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


    def parse_primary(self): # 拡張
        token = self.current_token
        if token.type == 'INTEGER':
            self.advance()
            return Number(token)
        elif token.type == 'ID': # 変数参照のケース
            self.advance()
            if not self.symbol_table.lookup(token.value):
                raise NameError(f"Variable '{token.value}' not declared")
            return VarAccess(token)
        else:
            raise SyntaxError(f"Unexpected token in expression: {token}")