from app.core.codegen.c_generator import generate_full_program
from app.core.ladder.ladder_to_st import ladder_to_st
from app.core.lexer.tokenizer import tokenize
from app.core.parser.parser import Parser


def compile_st_to_c(code: str) -> str:
    """Compile Structured Text source code into C code."""
    tokens = tokenize(code)
    ast = Parser(tokens).parse()
    return generate_full_program(ast)


def compile_ladder_to_c(code: str) -> str:
    """Compile simple Ladder text into C code through Structured Text."""
    return compile_st_to_c(ladder_to_st(code))
