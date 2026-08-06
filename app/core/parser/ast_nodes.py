class ProgramNode:
    def __init__(self, statements):
        self.statements = statements

    def __repr__(self):
        return f"ProgramNode(statements={self.statements!r})"


class IfNode:
    def __init__(self, condition, true_branch, false_branch):
        self.condition = condition
        # Branches contain lists of statement nodes.
        self.true_branch = true_branch
        self.false_branch = false_branch

    def __repr__(self):
        return (
            "IfNode("
            f"condition={self.condition!r}, "
            f"true_branch={self.true_branch!r}, "
            f"false_branch={self.false_branch!r}"
            ")"
        )


class AssignNode:
    def __init__(self, variable, value):
        self.variable = variable
        self.value = value

    def __repr__(self):
        return f"AssignNode(variable={self.variable!r}, value={self.value!r})"


class TimerNode:
    def __init__(self, name, in_value, pt, input_source=None):
        self.name = name
        self.in_value = in_value
        self.pt = pt
        self.input_source = input_source

    def __repr__(self):
        return (
            "TimerNode("
            f"name={self.name!r}, "
            f"in_value={self.in_value!r}, "
            f"pt={self.pt!r}, "
            f"input_source={self.input_source!r}"
            ")"
        )


class JsrNode:
    """Jump to Subroutine: calls another program's compiled function."""

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"JsrNode(name={self.name!r})"
