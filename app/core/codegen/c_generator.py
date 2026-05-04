from app.core.parser.ast_nodes import AssignNode, IfNode, ProgramNode


INDENT = " " * 4
VALUE_MACROS = {
    "TRUE": "HIGH",
    "FALSE": "LOW",
}


def indent(indent_level: int) -> str:
    return INDENT * indent_level


def generate_full_program(ast) -> str:
    pin_map = build_pin_map(ast)
    definitions = generate_pin_definitions(pin_map)
    setup = generate_pin_setup(pin_map)
    resets = generate_output_resets(pin_map)
    logic = generate_c(ast, pin_map, indent_level=1)
    loop_body = "\n".join(part for part in (resets, logic) if part)

    return (
        "#include <Arduino.h>\n\n"
        f"{definitions}\n\n"
        "void setup() {\n"
        f"{setup}\n"
        "}\n\n"
        "void loop() {\n"
        f"{loop_body}\n"
        "}"
    )


def generate_c(ast, pin_map: dict, indent_level: int = 0) -> str:
    if isinstance(ast, ProgramNode):
        return "\n\n".join(generate_c(statement, pin_map, indent_level) for statement in ast.statements)
    if isinstance(ast, IfNode):
        return generate_if(ast, pin_map, indent_level)
    if isinstance(ast, AssignNode):
        return generate_assign(ast, pin_map, indent_level)
    raise TypeError(f"Unsupported AST node: {type(ast).__name__}")


def generate_if(node: IfNode, pin_map: dict, indent_level: int = 0) -> str:
    condition_pin = pin_map["inputs"][node.condition]["macro"]
    true_branch = "\n".join(
        generate_c(statement, pin_map, indent_level + 1) for statement in node.true_branch
    )
    code = (
        f"{indent(indent_level)}if (digitalRead({condition_pin})) {{\n"
        f"{true_branch}\n"
        f"{indent(indent_level)}}}"
    )

    if node.false_branch:
        false_branch = "\n".join(
            generate_c(statement, pin_map, indent_level + 1) for statement in node.false_branch
        )
        code += (
            " else {\n"
            f"{false_branch}\n"
            f"{indent(indent_level)}}}"
        )

    return code


def generate_assign(node: AssignNode, pin_map: dict, indent_level: int = 0) -> str:
    output_pin = pin_map["outputs"][node.variable]["macro"]
    value = VALUE_MACROS[node.value]
    return f"{indent(indent_level)}digitalWrite({output_pin}, {value});"


def build_pin_map(ast) -> dict:
    inputs, outputs = collect_variables(ast)
    used_pins = set()
    pin_map = {"inputs": {}, "outputs": {}}

    next_input_pin = 4
    for variable in inputs:
        pin_map["inputs"][variable] = {
            "macro": make_pin_macro(variable),
            "pin": next_input_pin,
        }
        used_pins.add(next_input_pin)
        next_input_pin += 1

    next_output_pin = 5
    for variable in outputs:
        while next_output_pin in used_pins:
            next_output_pin += 1
        pin_map["outputs"][variable] = {
            "macro": make_pin_macro(variable),
            "pin": next_output_pin,
        }
        used_pins.add(next_output_pin)
        next_output_pin += 1

    return pin_map


def collect_variables(ast) -> tuple[list[str], list[str]]:
    inputs = []
    outputs = []

    def add_once(items, value):
        if value not in items:
            items.append(value)

    def visit(node):
        if isinstance(node, ProgramNode):
            for statement in node.statements:
                visit(statement)
        elif isinstance(node, IfNode):
            add_once(inputs, node.condition)
            for statement in node.true_branch:
                visit(statement)
            for statement in node.false_branch:
                visit(statement)
        elif isinstance(node, AssignNode):
            add_once(outputs, node.variable)
        else:
            raise TypeError(f"Unsupported AST node: {type(node).__name__}")

    visit(ast)
    return inputs, outputs


def generate_pin_definitions(pin_map: dict) -> str:
    lines = []
    for variable in pin_map["inputs"].values():
        lines.append(f"#define {variable['macro']} {variable['pin']}")
    for variable in pin_map["outputs"].values():
        lines.append(f"#define {variable['macro']} {variable['pin']}")
    return "\n".join(lines)


def generate_pin_setup(pin_map: dict) -> str:
    lines = []
    for variable in pin_map["inputs"].values():
        lines.append(f"{indent(1)}pinMode({variable['macro']}, INPUT);")
    for variable in pin_map["outputs"].values():
        lines.append(f"{indent(1)}pinMode({variable['macro']}, OUTPUT);")
    return "\n".join(lines)


def generate_output_resets(pin_map: dict) -> str:
    lines = []
    for variable in pin_map["outputs"].values():
        lines.append(f"{indent(1)}digitalWrite({variable['macro']}, LOW);  // default reset")
    return "\n".join(lines)


def make_pin_macro(variable: str) -> str:
    return f"{variable.upper()}_PIN"
