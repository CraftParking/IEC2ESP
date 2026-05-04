from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.validation import validation


mapping = [
    {"pin": 4, "tag": "input1", "type": "Input"},
    {"pin": 5, "tag": "output1", "type": "Output"},
]

ladder_code = """
input1 -> output1
output1 & missing_input -> output2
"""

errors = validation(mapping, ladder_code)
print("\n".join(errors))
