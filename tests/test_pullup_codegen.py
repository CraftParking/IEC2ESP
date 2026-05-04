from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.compiler import compile_ladder_to_c


mapping = {
    "input1": {"pin": 4, "type": "input", "pullup": True},
    "motor1": {"pin": 5, "type": "output", "pullup": False},
}

code = compile_ladder_to_c("input1 -> motor1", mapping)
print(code)
