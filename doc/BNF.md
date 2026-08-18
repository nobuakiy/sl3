# SL3 BNF

この文書は、現在の実装に近い形で SL3 の構文を整理したものです。
理想仕様ではなく、主に [src/parser.py](src/parser.py) と [src/lexer.py](src/lexer.py) に基づいています。

## 概要

SL3 は C 風の宣言構文を持つ小さな言語です。
トップレベルには変数宣言、定数宣言、関数定義を並べられます。

現在の実装には次の特徴があります。

- 基本型は `int`、`byte`、`void`、`StringBuffer`
- 文はブロック単位で記述する
- `if`、`while`、`for ... in ... do`、`return` をサポート
- `MEM[...]` と `PORT[...]` によるアクセスをサポート
- 式の二項演算子は現状 `==`、`!=`、`<`、`>`、`<=`、`>=`、`+`、`-`、`*`、`/` のみ
- 単項演算子として `&` をサポート

## プログラム構造

```bnf
<program> ::= <top_level_declaration>*

<top_level_declaration> ::= <const_variable_declaration>
                          | <variable_declaration>
                          | <function_declaration>
```

## 宣言

```bnf
<const_variable_declaration> ::= "const" <type_specifier> <identifier> <array_suffix>? "=" <expression> ";"

<variable_declaration> ::= <type_specifier> <identifier> <array_suffix>? <initializer>? ";"

<initializer> ::= "=" <expression>

<array_suffix> ::= "[" <const_integer> "]"

<function_declaration> ::= <type_specifier> <identifier> "(" <parameter_list>? ")" <block>

<parameter_list> ::= <parameter> ( "," <parameter> )*

<parameter> ::= <type_specifier> <identifier>

<type_specifier> ::= "int"
                   | "byte"
                   | "void"
                   | "StringBuffer"
```

補足:

- 配列サイズには整数リテラルか `const` 変数を使えます。
- `const` 変数は初期化必須です。
- `const` は変数宣言にのみ付けられ、関数宣言には付けられません。
- 引数宣言には現状、配列表記はありません。

## 文

```bnf
<statement> ::= <const_variable_declaration>
              | <variable_declaration>
              | <expression_statement>
              | <if_statement>
              | <while_statement>
              | <for_in_statement>
              | <return_statement>
              | <block>

<block> ::= "{" <statement>* "}"

<expression_statement> ::= <assignment_statement>
                         | <call_statement>

<assignment_statement> ::= <assignable> "=" <expression> ";"

<call_statement> ::= <call_expression> ";"

<if_statement> ::= "if" "(" <expression> ")" <block> <else_clause>?

<else_clause> ::= "else" <block>

<while_statement> ::= "while" "(" <expression> ")" <block>

<for_in_statement> ::= "for" <identifier> "in" <identifier> "do" <block>

<return_statement> ::= "return" <expression> ";"
```

補足:

- 代入演算子は現状 `=` のみです。
- 単独文として許される式は、関数呼び出しかメソッド呼び出しだけです。
- `return;` のような値なし return は現状の実装では不可です。
- `else if` は専用構文を持たず、必要なら `else { if (...) { ... } }` と書きます。
- `for` の `in` の後ろに書けるのは、既に宣言済みの配列変数の識別子だけです。実装上は
  一般の式パーサーを経由しますが、結果を無条件に変数アクセスとして扱っているため、
  配列変数の識別子以外(関数呼び出しの結果や配列要素など)を渡すと、構文エラーではなく
  未処理の例外で終了します。

## 式

```bnf
<expression> ::= <equality_expression>

<equality_expression> ::= <relational_expression>
                        | <equality_expression> "==" <relational_expression>
                        | <equality_expression> "!=" <relational_expression>

<relational_expression> ::= <additive_expression>
                          | <relational_expression> "<" <additive_expression>
                          | <relational_expression> ">" <additive_expression>
                          | <relational_expression> "<=" <additive_expression>
                          | <relational_expression> ">=" <additive_expression>

<additive_expression> ::= <multiplicative_expression>
                        | <additive_expression> "+" <multiplicative_expression>
                        | <additive_expression> "-" <multiplicative_expression>

<multiplicative_expression> ::= <unary_expression>
                              | <multiplicative_expression> "*" <unary_expression>
                              | <multiplicative_expression> "/" <unary_expression>

<unary_expression> ::= "&" <unary_expression>
                     | <primary_expression>
```

演算子優先順位は次の順です。

1. 単項 `&`
2. `*` `/`
3. `+` `-`
4. `<` `>` `<=` `>=`
5. `==` `!=`

補足:

- `&&`、`||`、`!`、`<<`、`>>` は字句解析(lexer.py)の時点でトークンとして存在しません。
- `|`(PIPE)と`^`(CARET)は字句解析ではトークン化されますが、構文解析側では式として使われていません。
- 単項 `-` も現状の parser では未対応です。

## 一次式

```bnf
<primary_expression> ::= "(" <expression> ")"
                       | <integer>
                       | <string>
                       | <mem_access>
                       | <port_access>
                       | <identifier_expression>

<mem_access> ::= "MEM" "[" <expression> "]"

<port_access> ::= "PORT" "[" <expression> "]" <port_bit_suffix>?

<port_bit_suffix> ::= "." <const_integer>

<identifier_expression> ::= <function_call>
                          | <method_call>
                          | <bit_access>
                          | <array_access>
                          | <variable_access>

<function_call> ::= <identifier> "(" <argument_list>? ")"

<method_call> ::= <identifier> "." <identifier> <method_arguments>

<method_arguments> ::= "(" <argument_list>? ")"

<bit_access> ::= <identifier> "." <const_integer>

<array_access> ::= <identifier> "[" <expression> "]"

<variable_access> ::= <identifier>

<argument_list> ::= <expression> ( "," <expression> )*
```

補足:

- メソッド呼び出しは括弧が必須で、`obj.method(...)` の形でのみ受理されます。
  `obj.method` のように括弧を省略すると、ビットアクセス構文として解釈されようとして
  エラーになります(引数リスト自体の省略、つまり `obj.method()` は可能です)。
- `PORT[...]` は `PORT[addr].bit` の形でビットアクセスもできます。
  ただし `MEM[...]` には同様のビットアクセス構文はありません。
- `a[0].method()` や `a[0].3` のような連鎖は現状の parser では扱っていません。
- `MEM[...]` と `PORT[...]` は式としても代入先としても使えます。
- ビットアクセスのビット番号には整数リテラルか `const` 変数を使えます。

## 代入可能な左辺

```bnf
<assignable> ::= <variable_access>
               | <array_access>
               | <bit_access>
               | <mem_access>
               | <port_access>

<call_expression> ::= <function_call>
                    | <method_call>
```

## 終端記号

```bnf
<identifier> ::= <letter_or_underscore> <identifier_char>*

<identifier_char> ::= <letter_or_underscore>
                    | <digit>

<letter_or_underscore> ::= "a" | ... | "z" | "A" | ... | "Z" | "_"

<integer> ::= <decimal_integer> | <hex_integer>

<decimal_integer> ::= <digit>+

<hex_integer> ::= "0x" <hex_digit>+

<string> ::= '"' <string_char>* '"'
```

字句上の予約語は次のとおりです。

- `const`
- `int`
- `byte`
- `void`
- `if`
- `else`
- `while`
- `return`
- `for`
- `in`
- `do`
- `MEM`
- `PORT`
- `StringBuffer`

## 実装との差分を避けるための注意

この文書は、将来の理想仕様ではなく現在の実装に寄せています。
そのため、一般的な C 風言語から期待しやすい次の機能は、今のところ使えないか、文法として未完成です。

- `import` 文
- 配列リテラル
- 複合代入演算子
- 論理演算子 `&&`、`||`、`!`
- ビット演算子 `|`、`^`、シフト演算子
- 引数なし `return`
- 多次元配列アクセスや式の連鎖

文法を拡張した場合は、まず [src/parser.py](src/parser.py) と [src/lexer.py](src/lexer.py) の挙動を更新し、その後でこの文書を合わせて更新してください。