from __future__ import annotations
from typing import Iterator, Optional, NoReturn, cast
from lexer import Token
from symbol_table import ScopedSymbolTable, VariableSymbol, FunctionSymbol, Symbol
# from parser_nodes import * # ASTノードを別ファイルに分離したと仮定

# --- AST Node Definitions (変更なし) ---
class AST: pass
class Program(AST):
    def __init__(self, children: list[AST]):
        self.children: list[AST] = children
class VarDecl(AST):
    def __init__(self, type_node: Type, var_node: Token, initial_value: Optional[AST] = None, is_array: bool = False, size: int = 0):
        self.type_node, self.var_node, self.initial_value = type_node, var_node, initial_value
        self.is_array, self.size = is_array, size
class Assignment(AST):
    def __init__(self, left: AST, right: AST):
        self.left, self.right = left, right
class IfStatement(AST):
    def __init__(self, condition: AST, then_block: Block, else_block: Optional[Block] = None):
        self.condition, self.then_block, self.else_block = condition, then_block, else_block
class WhileStatement(AST):
    def __init__(self, condition: AST, body: Block):
        self.condition, self.body = condition, body
class ForInStatement(AST):
    def __init__(self, item_token: Token, array_node: AST, body: Block):
        self.item_token = item_token
        self.array_node = array_node
        self.body = body
        self.local_symbols: dict[str, Symbol] = {} # ループ変数用のスコープ
class FuncDecl(AST):
    def __init__(self, return_type: Type, name_token: Token, params: list[Param], body: Block):
        self.return_type, self.name_token, self.params, self.body = return_type, name_token, params, body
        self.local_symbols: dict[str, Symbol] = {} # ★ ローカルシンボルを保存する辞書を追加
class FuncCall(AST):
    def __init__(self, name_token: Token, args: list[AST]):
        self.name_token, self.args = name_token, args
class ReturnStatement(AST):
    def __init__(self, expr: AST):
        self.expr: AST = expr
class Block(AST):
    def __init__(self, statements: list[AST]):
        self.statements: list[AST] = statements
class ArrayAccess(AST):
    def __init__(self, var_node: VarAccess, index_expr: AST):
        self.var_node, self.index_expr = var_node, index_expr
class UnaryOp(AST):
    def __init__(self, op: Token, expr: AST):
        self.op, self.expr = op, expr
class MemAccess(AST):
    def __init__(self, address_expr: AST):
        self.address_expr: AST = address_expr
class PortAccess(AST):
    def __init__(self, address_expr: AST, token: Token):
        self.address_expr: AST = address_expr
        self.token: Token = token # エラー報告用にトークンを保持
class BinOp(AST):
    def __init__(self, left: AST, op: Token, right: AST):
        self.left, self.op, self.right = left, op, right
class Number(AST):
    def __init__(self, token: Token):
        self.token, self.value = token, token.value
class VarAccess(AST):
    def __init__(self, token: Token):
        self.token, self.value = token, token.value
class Type(AST):
    def __init__(self, token: Token):
        self.token, self.value = token, token.value
class Param(AST):
    def __init__(self, type_node: Type, var_node: Token):
        self.type_node, self.var_node = type_node, var_node
class StringLiteral(AST):
    def __init__(self, token: Token):
        self.token: Token = token
        self.value: str = token.value
class BitAccess(AST):
    def __init__(self, var_node: AST, bit_num_token: Token):
        self.var_node = var_node
        self.bit_num_token = bit_num_token
class MethodCall(AST):
    def __init__(self, var_node: VarAccess, method_token: Token, args: list[AST]):
        self.var_node = var_node
        self.method_token = method_token
        self.args = args


# --- Parser ---
class Parser:

    def __init__(self, tokens: Iterator[Token], source_code: str):
        self.tokens: Iterator[Token] = tokens
        self.current_token: Optional[Token] = None
        self.peek_token: Optional[Token] = None
        self.source_lines: list[str] = source_code.splitlines()
        self.advance(); self.advance()
        self.symbol_table: ScopedSymbolTable = ScopedSymbolTable()
        # ★★★ ファイルから組み込み関数を登録するよう変更 ★★★
        self._register_builtins_from_file("./src/stdlib.def")
        self.precedence: dict[str, int] = {
            'EQ': 3, 'NE': 3, 'LT': 4, 'GT': 4, 'LE': 4, 'GE': 4,
            'PLUS': 5, 'MINUS': 5, 'MUL': 6, 'DIV': 6
        }

    def _register_builtins_from_file(self, filename: str) -> None:
        """定義ファイルからライブラリ関数を読み込み、シンボルテーブルに登録する"""
        print(f"--- Loading library definitions from '{filename}' ---")
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                count = 0
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue # コメント行や空行はスキップ

                    parts = line.split()
                    if len(parts) < 2: continue

                    return_type, func_name, *arg_types = parts

                    # 文字列の型名をトークンとTypeノードに変換
                    # (大文字に変換してトークンタイプとする)
                    return_type_node = Type(Token(return_type.upper(), return_type))

                    # TODO: 引数の型リストも同様に作成
                    params = []

                    func_symbol = FunctionSymbol(func_name, return_type_node, params)
                    self.symbol_table.define(func_symbol)
                    count += 1
            print(f"✅ Loaded {count} library functions.")
        except FileNotFoundError:
            print(f"⚠️ Warning: Library definition file '{filename}' not found. Skipping.")

    def _error(self, message: str, token: Optional[Token] = None) -> NoReturn:
        token = token or self.current_token
        err_line, pointer, line_info = "<source not available>", "", ""
        if token:
            line_num, col_num = token.line, token.column
            line_info = f"on line {line_num}, column {col_num}"
            if 0 < line_num <= len(self.source_lines):
                err_line = self.source_lines[line_num - 1].replace('\t', '    ')
                pointer = " " * col_num + "^"
        full_message = (f"\n\n--- Compilation Error ---\nSyntax Error {line_info}:\n{message}\n\n> {err_line}\n  {pointer}\n")
        raise SyntaxError(full_message)

    def advance(self) -> None:
        self.current_token = self.peek_token
        try:
            self.peek_token = next(self.tokens)
        except StopIteration:
            self.peek_token = None

    def eat(self, token_type: str) -> None:
        if self.current_token and self.current_token.type == token_type:
            self.advance()
        else:
            got_type = self.current_token.type if self.current_token else 'EOF'
            self._error(f"Expected token '{token_type}', but got '{got_type}'")

    def parse(self) -> Program:
        declarations: list[AST] = []
        while self.current_token:
            declarations.append(self.parse_top_level_declaration())
        return Program(declarations)

    def parse_top_level_declaration(self) -> AST:
        # ★ constキーワードをチェック
        is_const = False
        if self.current_token and self.current_token.type == 'CONST':
            is_const = True
            self.eat('CONST')

        type_node = self.parse_type()
        name_token = self.current_token
        assert name_token is not None
        self.eat('ID')

        if self.current_token and self.current_token.type == 'LPAREN':
            if is_const:
                self._error("Functions cannot be declared const", name_token)
            return self.parse_function_declaration(type_node, name_token)
        else:
            # ★ is_constフラグを渡す
            return self.parse_variable_declaration(type_node, name_token, is_const=is_const)

    def parse_variable_declaration(self, type_node: Type, name_token: Token, is_const: bool = False) -> VarDecl:
        # (is_constを引数として受け取るように変更)
        is_array, size = False, 0
        if self.current_token and self.current_token.type == 'LBRACKET':
            is_array, size = True, self._parse_array_size()

        scope = 'global' if self.symbol_table.scope_level == 0 else 'local'
        # ★ is_constフラグをシンボルに設定
        symbol = VariableSymbol(name_token.value, type_node, scope,
                                is_array=is_array, size=size, is_const=is_const)
        self.symbol_table.define(symbol)

        initial_value = None
        if self.current_token and self.current_token.type == 'ASSIGN':
            self.eat('ASSIGN')
            initial_value = self.parse_expression()
            if is_const:
                # ★ const変数の初期値は整数リテラルまたはconst変数のみ許可
                ref_symbol = self.symbol_table.lookup(initial_value.token.value) if isinstance(initial_value, VarAccess) else None
                is_const_ref = isinstance(ref_symbol, VariableSymbol) and ref_symbol.is_const
                if not isinstance(initial_value, Number) and not is_const_ref:
                    self._error(f"Constant variable '{name_token.value}' must be initialized with a constant expression", name_token)
                else:
                    # 初期値が整数リテラルまたはconst変数の場合、値を保存
                    if isinstance(initial_value, Number):
                        symbol.const_value = initial_value.value
                    else:
                        # 本当は定数表現であれば、計算したいが...
                        pass

        # ★ const変数が初期化されているかチェック
        if is_const and initial_value is None:
            self._error(f"Constant variable '{name_token.value}' must be initialized", name_token)

        self.eat('SEMICOLON')
        return VarDecl(type_node, name_token, initial_value, is_array, size)

    def _parse_const_integer(self) -> int:
        """定数として扱える整数値（リテラルまたはconst変数）を解析して返す"""
        token = self.current_token
        assert token is not None
        if token.type == 'INTEGER':
            self.advance()
            return token.value

        if token.type == 'ID':
            symbol = self.symbol_table.lookup(token.value)
            if symbol and isinstance(symbol, VariableSymbol) and symbol.is_const:
                # シンボルがconstの場合、その初期値を取得する必要がある。
                # このためには、VarDeclノードに初期値の情報を保存しておく必要がある。
                # ここでは簡単のため、定数値がシンボルに直接格納されていると仮定する。
                # 実際のプロジェクトでは、シンボルに初期化式への参照を持たせるなどの工夫が必要。

                # --- 仮実装 ---
                # シンボルテーブルに定数の値を保存するよう拡張したと仮定
                if symbol.const_value is not None:
                    self.advance()
                    return symbol.const_value
                else:
                    self._error(f"Value of const '{token.value}' not available at compile time", token)

            self._error(f"Expected a constant integer expression", token)

        self._error(f"Expected an integer literal or a const identifier", token)

    def _parse_array_size(self) -> int:
        self.eat('LBRACKET')
        # ★ 整数リテラルだけでなく、const変数も使えるようにする
        size = self._parse_const_integer()
        self.eat('RBRACKET')
        return size

    def parse_function_declaration(self, type_node: Type, name_token: Token) -> FuncDecl:
        func_symbol = FunctionSymbol(name_token.value, type_node)
        self.symbol_table.define(func_symbol)

        self.eat('LPAREN')
        # ★ 引数リストの解析を専用メソッドに切り出し
        params = self.parse_param_list()
        func_symbol.params = params # シンボルにも引数情報を記録
        self.eat('RPAREN')

        self.symbol_table.enter_scope()

        # 引数をローカルスコープに登録
        param_offset = 4 # 戻りアドレス(2byte), 旧IX(2byte)の次から
        for p in params:
            param_symbol = VariableSymbol(p.var_node.value, p.type_node, 'local', offset=param_offset)
            self.symbol_table.define(param_symbol)
            param_offset += 2 # 今はint(2byte)のみと仮定

        body = self.parse_block_statement()

        local_symbols = self.symbol_table.scopes[-1]
        self.symbol_table.leave_scope()

        func_decl_node = FuncDecl(type_node, name_token, params, body)
        func_decl_node.local_symbols = local_symbols
        return func_decl_node

    def parse_param_list(self) -> list[Param]:
        """関数宣言の引数リストを解析する"""
        params: list[Param] = []
        if self.current_token and self.current_token.type == 'RPAREN':
            return params # 引数なし

        # 最初の引数
        type_node = self.parse_type()
        var_token = self.current_token
        assert var_token is not None
        self.eat('ID')
        params.append(Param(type_node, var_token))

        # 2つ目以降の引数 (コンマがある限りループ)
        while self.current_token and self.current_token.type == 'COMMA':
            self.eat('COMMA')
            type_node = self.parse_type()
            var_token = self.current_token
            assert var_token is not None
            self.eat('ID')
            params.append(Param(type_node, var_token))

        return params

    def parse_statement(self) -> AST:
        if not self.current_token: self._error("Unexpected end of file")

        tok_type = self.current_token.type
        is_const = False
        if tok_type == 'CONST':
            is_const = True
            self.eat('CONST')

        if tok_type in ('INT', 'BYTE', 'STRINGBUFFER'):
            type_node = self.parse_type()
            name_token = self.current_token
            self.eat('ID')
            return self.parse_variable_declaration(type_node, name_token, is_const=is_const)

        if is_const: # constの後ろに型名がなければエラー
            self._error("Expected a type specifier after 'const'")

        if tok_type in ('ID', 'MEM', 'PORT', 'LPAREN'):
            # 代入文または関数呼び出しの解析
            return self.parse_expression_statement()

        if tok_type == 'FOR':
            return self.parse_for_in_statement()

        if tok_type == 'IF': return self.parse_if_statement()
        if tok_type == 'WHILE': return self.parse_while_statement()
        if tok_type == 'RETURN': return self.parse_return_statement()
        if tok_type == 'LBRACE': return self.parse_block_statement()
        self._error(f"Invalid statement starting with '{tok_type}'")

    def parse_expression_statement(self) -> AST:
        """代入文か、単独の(関数呼び出しなどの)文かを解析する"""
        # まず、文の最初の部分を式として解析する
        expr_node = self.parse_expression()

        # 式の後に続くトークンで、文の種類を判断
        if self.current_token and self.current_token.type == 'ASSIGN':
            # --- 代入文の場合 ---
            # 左辺が代入可能なものかチェック
            if not isinstance(expr_node, (VarAccess, ArrayAccess, BitAccess, MemAccess, PortAccess)):
                self._error("The left-hand side of an assignment must be a variable or memory location.")

            self.eat('ASSIGN')
            right_node = self.parse_expression()
            self.eat('SEMICOLON')
            return Assignment(expr_node, right_node)
        else:
            # --- 単独の文 (関数呼び出しなど) の場合 ---
            # 効果のない文 (例: "x + y;") をエラーにする
            if not isinstance(expr_node, (FuncCall, MethodCall)):
                self._error("This expression has no effect and is not a valid statement.")

            self.eat('SEMICOLON')
            return expr_node

    def parse_block_statement(self) -> Block:
        self.eat('LBRACE')
        statements: list[AST] = []
        while self.current_token and self.current_token.type != 'RBRACE':
            statements.append(self.parse_statement())
        self.eat('RBRACE')
        return Block(statements)

    def parse_assignment_statement(self) -> Assignment:
        name_token = self.current_token
        assert name_token is not None
        self.eat('ID');
        left_node: AST = VarAccess(name_token)
        if self.current_token and self.current_token.type == 'LBRACKET':
            self.eat('LBRACKET');
            index_expr = self.parse_expression();
            self.eat('RBRACKET')
            left_node = ArrayAccess(left_node, index_expr)
        self.eat('ASSIGN');

        # constantの代入をチェック
        symbol = self.symbol_table.lookup(name_token.value)
        if isinstance(symbol, VariableSymbol) and symbol.is_const:
            self._error(f"Cannot assign to constant variable '{name_token.value}'")

        right_node = self.parse_expression();
        self.eat('SEMICOLON')
        return Assignment(left_node, right_node)

    def parse_if_statement(self) -> IfStatement:
        self.eat('IF');
        self.eat('LPAREN');
        condition = self.parse_expression();
        self.eat('RPAREN')
        then_block = self.parse_block_statement()
        else_block = None
        if self.current_token and self.current_token.type == 'ELSE':
            self.eat('ELSE');
            else_block = self.parse_block_statement()
        return IfStatement(condition, then_block, else_block)

    def parse_while_statement(self) -> WhileStatement:
        self.eat('WHILE');
        self.eat('LPAREN');
        condition = self.parse_expression();
        self.eat('RPAREN')
        body = self.parse_block_statement()
        return WhileStatement(condition, body)

    def parse_return_statement(self) -> ReturnStatement:
        self.eat('RETURN');
        expr = self.parse_expression();
        self.eat('SEMICOLON')
        return ReturnStatement(expr)

    def parse_type(self) -> Type:
        token = self.current_token
        if token and token.type in ('INT', 'BYTE', 'VOID', 'STRINGBUFFER'):
            self.advance();
            return Type(token)
        self._error("Expected a type specifier")

    def parse_expression(self, prec: int = 0) -> AST:
        # & のような単項演算子を処理
        if self.current_token and self.current_token.type == 'AMPERSAND': # &
            op = self.current_token
            self.advance()
            expr = self.parse_expression(100) # 演算子の優先順位を高く設定
            return UnaryOp(op, expr)

        # 二項演算子の処理
        node = self.parse_primary()
        while self.current_token and self.current_token.type in self.precedence and self.precedence[self.current_token.type] > prec:
            op_token = self.current_token
            self.advance()
            right_node = self.parse_expression(self.precedence[op_token.type])
            node = BinOp(left=node, op=op_token, right=right_node)
        return node

    def parse_primary(self) -> AST:
        token = self.current_token
        if not token:
            self._error("Unexpected end of expression")

        if token.type == 'LPAREN':
            self.eat('LPAREN')
            node = self.parse_expression() # 括弧の中の式を再帰的に解析
            self.eat('RPAREN')
            return node

        # ★ STRINGトークンの解析を追加
        if token.type == 'STRING':
            self.advance()
            return StringLiteral(token)

        if token.type == 'INTEGER':
            self.advance();
            return Number(token)

        if token.type == 'MEM':
            self.eat('MEM'); self.eat('LBRACKET')
            addr_expr = self.parse_expression()
            self.eat('RBRACKET')
            return MemAccess(addr_expr)

        if token.type == 'PORT':
            self.eat('PORT'); self.eat('LBRACKET')
            addr_expr = self.parse_expression()
            self.eat('RBRACKET')
            port_node: AST = PortAccess(addr_expr, token)
            # PORT[...].BIT のようなビットアクセスにも対応
            if self.current_token and self.current_token.type == 'DOT':
                self.eat('DOT')
                bit_num_val = self._parse_const_integer()
                bit_num_token = Token('INTEGER', bit_num_val)
                return BitAccess(port_node, bit_num_token)
            return port_node

        if token.type == 'ID':
            name_token = token
            self.advance()

            # メソッド呼び出しとbitアクセス
            if self.current_token and self.current_token.type == 'DOT':
                self.eat('DOT')
                # DOTの後ろが「ID + LPAREN」ならメソッド呼び出し、それ以外はビットアクセス
                if (self.current_token and self.current_token.type == 'ID'
                        and self.peek_token and self.peek_token.type == 'LPAREN'):
                    method_token = self.current_token
                    self.eat('ID')
                    self.eat('LPAREN')
                    args: list[AST] = []
                    if self.current_token and self.current_token.type != 'RPAREN':
                        args.append(self.parse_expression())
                        while self.current_token and self.current_token.type == 'COMMA':
                            self.eat('COMMA')
                            args.append(self.parse_expression())
                    self.eat('RPAREN')
                    return MethodCall(VarAccess(name_token), method_token, args)

                else:
                    # ビットアクセス（ビット番号は整数リテラルまたはconst変数）
                    bit_num_val = self._parse_const_integer()
                    # BitAccessノードはトークンではなく数値を直接受け取るように変更するのが望ましい
                    bit_num_token = Token('INTEGER', bit_num_val)
                    return BitAccess(VarAccess(name_token), bit_num_token)

            # 関数呼び出し
            if self.current_token and self.current_token.type == 'LPAREN':
                return self.parse_function_call(name_token)

            # 配列アクセス
            if self.current_token and self.current_token.type == 'LBRACKET':
                self.eat('LBRACKET'); index_expr = self.parse_expression(); self.eat('RBRACKET')
                return ArrayAccess(VarAccess(name_token), index_expr)

            # 普通の変数アクセス
            return VarAccess(name_token)

        self._error(f"Unexpected token in expression: {token}")

    def parse_function_call(self, name_token) -> FuncCall:

        # シンボルテーブルに関数として登録されているかチェック
        symbol = self.symbol_table.lookup(name_token.value)
        if not symbol or not isinstance(symbol, FunctionSymbol):
            self._error(f"'{name_token.value}' is not a function or is not defined.", name_token)

        self.eat('LPAREN')
        args: list[AST] = []
        if self.current_token and self.current_token.type != 'RPAREN':
            args.append(self.parse_expression())
            while self.current_token and self.current_token.type == 'COMMA':
                self.eat('COMMA'); args.append(self.parse_expression())
        self.eat('RPAREN')
        return FuncCall(name_token, args)

    def parse_for_in_statement(self) -> ForInStatement:
        self.eat('FOR')
        item_token = self.current_token
        assert item_token is not None
        self.eat('ID')
        self.eat('IN')
        array_node = self.parse_expression()
        array_var = cast(VarAccess, array_node) # 簡単のため変数ノードと仮定
        self.eat('DO')

        # forループ専用のスコープに入る
        self.symbol_table.enter_scope()

        # ループ変数をシンボルとして登録 (型は配列の要素型から推論)
        array_symbol = self.symbol_table.lookup(array_var.value)
        if not array_symbol or not isinstance(array_symbol, VariableSymbol) or not array_symbol.is_array:
            self._error(f"'{array_var.value}' is not an array and cannot be iterated", array_var.token)
        assert array_symbol.type is not None

        # item変数の型は配列の型と同じ
        item_symbol = VariableSymbol(item_token.value, array_symbol.type, 'local')
        self.symbol_table.define(item_symbol)

        body = self.parse_block_statement()

        local_symbols = self.symbol_table.scopes[-1]
        self.symbol_table.leave_scope()

        node = ForInStatement(item_token, array_node, body)
        node.local_symbols = local_symbols # codegen用にローカルシンボルを保存
        return node