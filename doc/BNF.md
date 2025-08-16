```
<program> ::= { <declaration> }

<declaration> ::= <var-decl>
                 | <func-decl>
                 | <struct-decl>
                 | <module-decl>

<var-decl> ::= <type> <identifier> [ "[" <int-literal> "]" ] [ "=" <array-initializer> | "=" <expression> ] ";"

<func-decl> ::= <type> <identifier> "(" [ <param-list> ] ")" <block>

<param-list> ::= <param> { "," <param> }
<param> ::= <type> <identifier> [ "[" <int-literal> "]" ]

<struct-decl> ::= "struct" <identifier> "{" { <var-decl> } "}"

<module-decl> ::= "module" <identifier> "{" { <declaration> } "}"

<type> ::= "int" | "byte" | "StringBuffer" | "bool" | <identifier>

<block> ::= "{" { <statement> } "}"

<statement> ::= <block>
               | <var-decl>
               | <expression-stmt>
               | <if-stmt>
               | <while-stmt>
               | <return-stmt>

<expression-stmt> ::= <expression> ";"

<if-stmt> ::= "if" "(" <expression> ")" <statement>
             [ "else" <statement> ]

<while-stmt> ::= "while" "(" <expression> ")" <statement>

<return-stmt> ::= "return" [ <expression> ] ";"

<expression> ::= <assignment>

<assignment> ::= <logical-or> [ <assign-operator> <assignment> ]

<assign-operator> ::= "=" | "+=" | "-=" | "*=" | "/="

<logical-or> ::= <logical-and> { "||" <logical-and> }
<logical-and> ::= <equality> { "&&" <equality> }

<equality> ::= <comparison> { ( "==" | "!=" ) <comparison> }
<comparison> ::= <term> { ( "<" | ">" | "<=" | ">=" ) <term> }

<term> ::= <factor> { ( "+" | "-" ) <factor> }
<factor> ::= <unary> { ( "*" | "/" | "%" ) <unary> }

<unary> ::= [ "!" | "-" ] <primary>

<primary> ::= <literal>
             | <identifier>
             | <call>
             | <bit-access>
             | <array-access>
             | "(" <expression> ")"
             | <lambda>

<array-access> ::= <identifier> "[" <expression> "]"

<bit-access> ::= <identifier> "." <bit-index>
<bit-index> ::= <digit>  // 0〜7

<call> ::= <identifier> "(" [ <arg-list> ] ")"
<arg-list> ::= <expression> { "," <expression> }

<lambda> ::= "(" [ <param-list> ] ")" "=>" <block>

<array-initializer> ::= "{" <expression> { "," <expression> } "}"

<literal> ::= <int-literal>
             | <byte-literal>
             | <string-literal>
             | "true"
             | "false"

<byte-literal> ::= <int-literal> // 実際は0〜255に制限

<identifier> ::= <letter> { <letter> | <digit> | "_" }
<letter> ::= "A".."Z" | "a".."z" | "_"
<digit> ::= "0".."9"
```