from pathlib import Path

import pytest

from codegen_8086 import CodeGenerator
from lexer import Lexer
from parser import Parser


SAMPLE_SOURCES = sorted(
    (Path(__file__).parent.glob("*.lang")),
    key=lambda path: path.name,
) + sorted(
    (Path(__file__).parent.glob("*.sl3")),
    key=lambda path: path.name,
)


@pytest.mark.parametrize(
    "source_path",
    SAMPLE_SOURCES,
    ids=lambda path: path.name,
)
def test_sample_source_generates_8086_assembly(source_path: Path) -> None:
    source_code = source_path.read_text(encoding="utf-8")
    source_lines = source_code.splitlines()
    tokens = list(Lexer(source_code).tokenize())
    parser = Parser(iter(tokens), source_code)
    ast = parser.parse()

    assembly = CodeGenerator().generate(ast, parser.symbol_table, source_lines)

    assert assembly.strip()
    assert "segment .text" in assembly