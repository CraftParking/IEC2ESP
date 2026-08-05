# IEC2ESP

Convert IEC 61131-3 (Structured Text, Ladder Logic) into C for ESP32.

This repo is the compiler backbone only - lexer, parser, code generator,
ladder-to-ST conversion, validation, and controller profiles. There is no UI
here; the PyQt desktop UI that used to live in `app/ui` was removed so a new
UI can be built against this backbone directly.

## Integration entry points

```python
from app.core.compiler import compile_st_to_c, compile_ladder_to_c

compile_st_to_c(st_source_code, io_mapping, controller_config)
compile_ladder_to_c(ladder_source_code, io_mapping, controller_config)
```

- `app/core/lexer`, `app/core/parser`, `app/core/codegen` - the ST -> C pipeline
- `app/core/ladder` - Ladder -> ST conversion
- `app/core/validation.py` - tag/IO validation (`validation(...)`)
- `app/core/controller_config.py` - controller pin/type configuration
- `app/core/profiles/profile_manager.py` + `app/profiles/*.json` - saved controller profiles
- `app/services`, `app/utils` - placeholders for flashing/file/logging support, not yet implemented

See `docs/architecture.md` for the pipeline shape and `docs/roadmap.md` for what's left.
