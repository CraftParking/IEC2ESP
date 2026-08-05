# Architecture

IEC2ESP is a compiler backbone with no UI attached. It's organized as a
small pipeline:

- Lexer (`app/core/lexer`) - tokenizes Structured Text source
- Parser (`app/core/parser`) - builds an AST from tokens
- Code generator (`app/core/codegen`) - emits Arduino/ESP32 C from the AST
- Ladder (`app/core/ladder`) - converts simple Ladder text into Structured Text,
  so it can go through the same ST -> C pipeline
- Validation (`app/core/validation.py`) - checks tags/IO against global variables
- Controller config (`app/core/controller_config.py`) + profiles
  (`app/core/profiles`, `app/profiles/*.json`) - pin/type mapping per controller

`app/core/compiler.py` is the public entry point (`compile_st_to_c`,
`compile_ladder_to_c`) that a UI or CLI wires into.

`app/services` and `app/utils` are unimplemented placeholders for future
flashing, file, and logging support.
