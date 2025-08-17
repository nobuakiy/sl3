# --- symbol_table.py ---

class Symbol:
    def __init__(self, name, type):
        self.name = name
        self.type = type

class VariableSymbol(Symbol):
    def __init__(self, name, type):
        super().__init__(name, type)

class SymbolTable:
    def __init__(self):
        self._symbols = {}

    def define(self, symbol):
        print(f"Defining symbol: {symbol.name}")
        self._symbols[symbol.name] = symbol

    def lookup(self, name):
        print(f"Looking up symbol: {name}")
        return self._symbols.get(name)