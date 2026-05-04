from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.compiler import compile_st_to_c


code = """
IF input1 THEN
output1 := TRUE;
END_IF;

IF input2 THEN
output2 := TRUE;
END_IF;
"""


print(compile_st_to_c(code))
