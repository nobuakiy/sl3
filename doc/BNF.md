はい、承知いたしました。C言語風の型指定方法に変更したBNFを以下に提案します。

`var`キーワードを廃止し、型名を先に記述するスタイルに変更しました。これにより、変数、定数、関数の宣言がよりC言語に近い、馴染みのある構文になります。


-----


### 1\. プログラム全体構造

プログラムは、インポート文、グローバル宣言（定数、変数）、そして関数定義の集まりで構成されます。

```bnf
<program> ::= <program_statement>*

<program_statement> ::= <import_statement>
                      | <declaration>
                      | <function_declaration>
```

-----


### 2\. トップレベル文

**インポート文** 📦
他のモジュールを読み込みます。

```bnf
<import_statement> ::= 'import' <IDENTIFIER> ';'
```

**宣言文** 宣言は、定数、変数、または関数定義です。トップレベル（グローバル）にも、関数内（ローカル）にも記述できます。

```bnf
<declaration> ::= <const_declaration>
                | <variable_declaration>
```

**定数宣言** 📝
C言語と同様に `const <型> <名前> = <値>;` の形式になります。

```bnf
<const_declaration> ::= 'const' <type_specifier> <UPPERCASE_IDENTIFIER> ('[' ']')? '=' <expression> ';'
```

  * `const int MAX_VALUE = 65535;`
  * `const byte KEY_MAP[] = [0, 1, 2, 3];`  // 配列定数。サイズは初期化子から推論される


**変数宣言** 💾
`var`キーワードがなくなり、型名から宣言を始めます。配列のサイズは変数名の後に指定します。

```bnf
<variable_declaration> ::= <type_specifier> <IDENTIFIER> ('[' <expression> ']')? ('=' <expression>)? ';'
```

  * `byte counter;`
  * `int buffer[16];`
  * `StringBuffer name_buffer[32];` // 32要素のStringBuffer配列

**関数宣言** 🔧
`func`キーワードと`->`を廃止し、戻り値の型を関数名の前に置きます。引数もC言語と同じ `型名 仮引数名` の順序です。

```bnf
<function_declaration> ::= <type_specifier> <IDENTIFIER> '(' <parameter_list>? ')' <block_statement>

<parameter_list> ::= <parameter> (',' <parameter>)*
<parameter>      ::= <type_specifier> <IDENTIFIER> ('[' ']')?
```

  * `int add(int a, int b) { return a + b; }`
  * `void setup_display() { /* ... */ }`
  * `void process_data(byte data_array[]) { /* ... */ }`

-----

### 3\. 型指定子 (変更点)

型の指定は、基本型、`StringBuffer`、または`void`のみを指すように単純化されます。配列の指定は各宣言の識別子部分に移動しました。

```bnf
<type_specifier> ::= 'void' | <base_type> | 'StringBuffer'

<base_type> ::= 'int' | 'byte'
```

  * **`void`** を追加し、値を返さない関数の戻り値の型として使用します。
  * 配列を示す `[ ]` の記述はここから削除されました。

-----

### 4\. 文 (Statements)

関数や制御構文の本体を構成する個々の命令です。

```bnf
<statement> ::= <declaration>
              | <assignment_statement>
              | <expression_statement>
              | <if_statement>
              | <for_statement>
              | <while_statement>
              | <return_statement>
              | <block_statement>

<block_statement> ::= '{' <statement>* '}'
```

**代入文**

```bnf
<assignment_statement> ::= <lvalue> <assignment_operator> <expression> ';'
<assignment_operator>  ::= '=' | '+=' | '-=' | '*=' | '/=' | '&=' | '|=' | '^=' | '<<=' | '>>='
```

**式文**
関数呼び出しなど、評価結果を捨てる式です。

```bnf
<expression_statement> ::= <expression> ';'
```

**if文**
C言語と同様の `if-else` 構文です。

```bnf
<if_statement> ::= 'if' <expression> <block_statement> ('else' <block_statement>)?
```

**for文 (for-in-do)**
指定された構文の`for`ループです。

```bnf
<for_statement> ::= 'for' <IDENTIFIER> 'in' <expression> 'do' <block_statement>
```

**while文**
標準的な`while`ループです。

```bnf
<while_statement> ::= 'while' <expression> <block_statement>
```

**return文**
関数から値を返します。

```bnf
<return_statement> ::= 'return' <expression>? ';'
```

-----

### 5\. 式 (Expressions)

値を生成するすべての構文です。演算子の優先順位に従って定義します。

```bnf
<expression> ::= <logic_or_expr>

<logic_or_expr>  ::= <logic_and_expr> ('||' <logic_and_expr>)*
<logic_and_expr> ::= <bitwise_or_expr> ('&&' <bitwise_or_expr>)*
<bitwise_or_expr>  ::= <bitwise_xor_expr> ('|' <bitwise_xor_expr>)*
<bitwise_xor_expr> ::= <bitwise_and_expr> ('^' <bitwise_and_expr>)*
<bitwise_and_expr> ::= <equality_expr> ('&' <equality_expr>)*
<equality_expr>  ::= <relational_expr> (('==' | '!=') <relational_expr>)*
<relational_expr>::= <shift_expr> (('<' | '>' | '<=' | '>=') <shift_expr>)*
<shift_expr>     ::= <additive_expr> (('<<' | '>>') <additive_expr>)*
<additive_expr>  ::= <multiplicative_expr> (('+' | '-') <multiplicative_expr>)*
<multiplicative_expr> ::= <unary_expr> (('*' | '/') <unary_expr>)*

<unary_expr> ::= ('-' | '!' | '&') <unary_expr>
               | <primary_expr>
```

  * `&` はアドレス取得演算子です。

**一次式 (Primary Expressions)**
式を構成する最も基本的な要素です。

```bnf
<primary_expr> ::= <lvalue>
                 | <literal>
                 | <array_literal>
                 | <function_call>
                 | '(' <expression> ')'

<lvalue> ::= <IDENTIFIER>
           | <lvalue> '[' <expression> ']'   // 配列アクセス: a[i]
           | <lvalue> '.' <INTEGER>          // ビットアクセス: a.3
           | 'MEM' '[' <expression> ']'    // メモリ直接アクセス: MEM[0x8000]

<function_call> ::= <IDENTIFIER> '(' <argument_list>? ')'
<argument_list> ::= <expression> (',' <expression>)*
```

**リテラル**
ソースコードに直接記述される値です。

```bnf
<literal> ::= <INTEGER> | <STRING>

<array_literal> ::= '[' <argument_list>? ']'
```

### 6\. 終端記号 (Terminals)

これ以上分解できない、語彙要素です。

```bnf
<IDENTIFIER>           ::= [a-z_][a-zA-Z0-9_]*
<UPPERCASE_IDENTIFIER> ::= [A-Z_][A-Z0-9_]*
<INTEGER>              ::= [1-9][0-9]* | '0' | '0x'[0-9a-fA-F]+
<STRING>               ::= '"' ( [^"] )* '"'
```

-----

このBNFは、指定された言語仕様を網羅し、パーサーを実装するための強固な基盤となるでしょう。特に、`lvalue`の定義により、配列要素 (`a[i]`) や特定ビット (`var.3`)、直接メモリアドレス (`MEM[addr]`) に対して、統一的な方法で値の読み書き（代入）が可能になるように設計されています。