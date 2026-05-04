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
