from __future__ import annotations
from typing import Optional

class Symbol:
    """すべてのシンボルの基底クラス"""
    def __init__(self, name: str, type: Optional['Type'] = None):
        self.name: str = name
        self.type: Optional['Type'] = type

class VariableSymbol(Symbol):
    """変数シンボル (グローバル/ローカル/引数)"""
    def __init__(self, name: str, type: 'Type', scope: str, offset: int = 0, is_array: bool = False, size: int = 0, is_const: bool = False):
        super().__init__(name, type)
        self.scope: str = scope
        self.offset: int = offset
        self.is_array: bool = is_array
        self.size: int = size
        self.is_const: bool = is_const  # 定数フラグを追加

class FunctionSymbol(Symbol):
    """関数シンボル"""
    def __init__(self, name: str, return_type: 'Type', params: Optional[list['Param']] = None):
        super().__init__(name, return_type)
        self.params: list['Param'] = params if params is not None else []

class ScopedSymbolTable:
    """スコープを持つシンボルテーブル"""
    def __init__(self) -> None:
        self.scopes: list[dict[str, Symbol]] = [{}]
        self.scope_level: int = 0

    def enter_scope(self) -> None:
        self.scopes.append({})
        self.scope_level += 1

    def leave_scope(self) -> None:
        if self.scope_level > 0:
            self.scopes.pop()
            self.scope_level -= 1

    def define(self, symbol: Symbol) -> None:
        self.scopes[-1][symbol.name] = symbol

    def lookup(self, name: str) -> Optional[Symbol]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None