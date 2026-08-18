from pathlib import Path

import pytest

from codegen_z80 import CodeGenerator
from lexer import Lexer
from parser import Parser


SAMPLE_SOURCES = sorted(
    (Path(__file__).parent.glob("*.lang")),
    key=lambda path: path.name,
) + sorted(
    (Path(__file__).parent.glob("*.sl3")),
    key=lambda path: path.name,
)

OUTPUT_DIR = Path(__file__).parent / "output"


@pytest.mark.parametrize(
    "source_path",
    SAMPLE_SOURCES,
    ids=lambda path: path.name,
)
def test_sample_source_generates_z80_assembly(source_path: Path) -> None:
    source_code = source_path.read_text(encoding="utf-8")
    source_lines = source_code.splitlines()
    tokens = list(Lexer(source_code).tokenize())
    parser = Parser(iter(tokens), source_code)
    ast = parser.parse()

    assembly = CodeGenerator().generate(ast, parser.symbol_table, source_lines)

    # 生成したアセンブラをテスト後も確認できるよう保存しておく
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / f"{source_path.stem}.z80").write_text(assembly, encoding="utf-8")

    assert assembly.strip()
    assert "main:" in assembly
