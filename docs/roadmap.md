# Roadmap

- [x] Structured Text lexer
- [x] Structured Text parser
- [x] C code generation
- [x] Ladder -> ST conversion
- [x] Tag/IO validation
- [x] JSR (Main + Sub Program subroutine calls) - `app/core/parser` `JsrNode`,
      `app/core/codegen/c_generator.py` `generate_multi_program_c`
- [ ] New UI, built against the `app.core.compiler` backbone
- [ ] ESP32 flashing workflow (`app/services/esp32_flasher.py`, currently empty)
- [ ] Project file management (`app/services/file_manager.py`, currently empty)

## Known limitations

- **Sub Program timers tick every scan, not only while their Sub is called.**
  `generate_multi_program_c` collects timers across every program up front
  and updates them unconditionally in `loop()`, exactly like the
  single-program path always has. Real ladder scan semantics would pause a
  timer whose owning rung isn't currently scanned (i.e. its Sub Program
  wasn't JSR'd that cycle). Fixing this means moving timer updates to run
  inline at their actual tree position instead of being hoisted - a real
  behavior change to existing single-program output, so it's deliberately
  left alone for now.
