from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.compiler import compile_programs_to_c

programs = {
    "Main": "input1 -> JSR(Faults)",
    "Faults": "sensorA -> alarm1",
}

code = compile_programs_to_c(programs, main_name="Main")
print(code)

assert "void SBR_Faults() {" in code, "Sub Program should compile into its own function"

loop_start = code.index("void loop()")
loop_body = code[loop_start:]
assert "SBR_Faults();" in loop_body, "Main should call the subroutine from loop()"
assert "digitalRead(INPUT1_PIN)) {\n        SBR_Faults();" in loop_body, (
    "the call should be guarded by Main's JSR condition, not called unconditionally"
)
assert "alarm1_state = true;" not in loop_body, (
    "the subroutine's own coil write must live inside SBR_Faults(), not directly in loop()"
)

print("\nOK: JSR compiles to a guarded call into a separate subroutine function")
