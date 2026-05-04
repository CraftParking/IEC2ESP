from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.ladder.ladder_to_st import ladder_to_st
from app.core.compiler import compile_st_to_c

ladder_code = """
input1 & input2 | input3 -> timer1(2000)
timer1 -> output1
"""

# Step 1: Ladder → ST
st_code = ladder_to_st(ladder_code)
print("=== ST CODE ===")
print(st_code)

# Step 2: ST → C
c_code = compile_st_to_c(st_code)
print("\n=== C CODE ===")
print(c_code)
