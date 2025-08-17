# --- AST Node Definitions ---
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
        self.token = token
        self.value = token.value

class Variable(AST):
    def __init__(self, token):
        self.token = token
        self.value = token.value

# --- Parser Implementation (simplified) ---
class Parser:
    def __init__(self, tokens):
        self.tokens = iter(tokens)
        self.current_token = None
        self.advance()

    def advance(self):
        try:
            self.current_token = next(self.tokens)
        except StopIteration:
            self.current_token = None

    def eat(self, token_type):
        if self.current_token and self.current_token.type == token_type:
            self.advance()
        else:
            raise SyntaxError(f"Expected {token_type}, got {self.current_token.type}")

    def parse(self):
        declarations = []
        while self.current_token is not None:
            # For simplicity, we only parse variable declarations here
            declarations.append(self.parse_variable_declaration())
        return Program(declarations)

    def parse_variable_declaration(self):
        # Example: int counter;
        type_node = self.parse_type()
        var_token = self.current_token
        self.eat('ID')
        var_node = Variable(var_token)
        
        # Array handling would go here...
        
        initial_value = None
        if self.current_token and self.current_token.type == 'ASSIGN':
            self.eat('ASSIGN')
            # Expression parsing would go here...
            # initial_value = self.parse_expression() 
            pass # Placeholder

        self.eat('SEMICOLON')
        return VarDecl(type_node, var_node, initial_value)
    
    def parse_type(self):
        token = self.current_token
        if token.type in ('INT', 'BYTE'):
            self.advance()
            return Type(token)
        else:
            raise SyntaxError("Expected a type specifier")