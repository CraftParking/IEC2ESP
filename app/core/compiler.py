from app.core.codegen.c_generator import generate_full_program, generate_multi_program_c
from app.core.ladder.ladder_to_st import ladder_to_st
from app.core.lexer.tokenizer import tokenize
from app.core.parser.parser import Parser


def compile_st_to_c(code: str, io_mapping: dict | None = None, controller_config: dict | None = None) -> str:
    """Compile Structured Text source code into C code."""
    tokens = tokenize(code)
    ast = Parser(tokens).parse()
    return generate_full_program(ast, io_mapping, controller_config)


def compile_ladder_to_c(code: str, io_mapping: dict | None = None, controller_config: dict | None = None) -> str:
    """Compile simple Ladder text into C code through Structured Text."""
    return compile_st_to_c(ladder_to_st(code), io_mapping, controller_config)


def compile_programs_to_c(
    programs: dict, main_name: str, io_mapping: dict | None = None,
    controller_config: dict | None = None, language: str = "ladder",
) -> str:
    """Compile a Main Program plus any number of Sub Programs (JSR targets)
    into one C file. `programs` maps program name -> source text in the
    given `language` ("ladder" or "st")."""
    asts = {}
    for name, code in programs.items():
        st_code = ladder_to_st(code) if language == "ladder" else code
        asts[name] = Parser(tokenize(st_code)).parse()
    return generate_multi_program_c(asts, main_name, io_mapping, controller_config)
