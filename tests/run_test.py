from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.compiler import compile_ladder_to_c


code = """
input1 -> output1
input1 & input2 -> output2
sensorA & sensorB & sensorC -> motor1
"""


print(compile_ladder_to_c(code))
