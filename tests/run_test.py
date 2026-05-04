from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.compiler import compile_st_to_c


code = """
IF input1 THEN
timer1(IN:=TRUE, PT:=2000);
END_IF;

IF timer1.Q THEN
output1 := TRUE;
END_IF;
"""


print(compile_st_to_c(code))
