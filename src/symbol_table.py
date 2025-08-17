# --- symbol_table.py ---

class Symbol:
    def __init__(self, name, type):
        self.name = name
        self.type = type

class VariableSymbol(Symbol):
    def __init__(self, name, type, scope, offset=0, is_array=False, size=0):
        super().__init__(name, type)
        self.scope = scope
        self.offset = offset
        self.is_array = is_array # 配列かどうか
        self.size = size       # 配列の要素数

class FunctionSymbol(Symbol):
    def __init__(self, name, return_type, params):
        super().__init__(name, return_type)
        self.params = params

class ScopedSymbolTable:
    def __init__(self):
        self.scopes = [{}] # Scope stack, global scope is at the bottom
        self.scope_level = 0

    def enter_scope(self):
        self.scopes.append({})
        self.scope_level += 1

    def leave_scope(self):
        self.scopes.pop()
        self.scope_level -= 1

    def define(self, symbol):
        self.scopes[-1][symbol.name] = symbol

    def lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None