from app.core.parser.ast_nodes import AssignNode, IfNode, ProgramNode, TimerNode


INDENT = " " * 4
VALUE_MACROS = {
    "TRUE": "true",
    "FALSE": "false",
}


def indent(indent_level: int) -> str:
    return INDENT * indent_level


def generate_full_program(ast) -> str:
    pin_map = build_pin_map(ast)
    timers = collect_timers(ast)
    definitions = generate_pin_definitions(pin_map)
    timer_type = generate_timer_type(timers)
    timer_update_function = generate_timer_update_function(timers)
    timer_declarations = generate_timer_declarations(timers)
    output_states = generate_output_state_declarations(pin_map)
    setup = "\n".join(
        part for part in (generate_pin_setup(pin_map), generate_timer_setup(timers)) if part
    )
    resets = generate_output_state_resets(pin_map)
    timer_logic = "\n\n".join(generate_timer(timer, pin_map, indent_level=1) for timer in timers)
    logic = generate_c(ast, pin_map, indent_level=1)
    writes = generate_output_writes(pin_map)
    loop_body = "\n".join(part for part in (resets, timer_logic, logic, writes) if part)
    declarations = "\n\n".join(
        part
        for part in (timer_type, timer_update_function, timer_declarations, output_states)
        if part
    )

    return (
        "#include <Arduino.h>\n\n"
        f"{definitions}\n\n"
        f"{declarations}\n\n"
        "void setup() {\n"
        f"{setup}\n"
        "}\n\n"
        "void loop() {\n"
        f"{loop_body}\n"
        "}"
    )


def generate_c(ast, pin_map: dict, indent_level: int = 0) -> str:
    if isinstance(ast, ProgramNode):
        return "\n\n".join(
            code
            for statement in ast.statements
            if (code := generate_c(statement, pin_map, indent_level))
        )
    if isinstance(ast, IfNode):
        return generate_if(ast, pin_map, indent_level)
    if isinstance(ast, AssignNode):
        return generate_assign(ast, pin_map, indent_level)
    if isinstance(ast, TimerNode):
        return ""
    raise TypeError(f"Unsupported AST node: {type(ast).__name__}")


def generate_if(node: IfNode, pin_map: dict, indent_level: int = 0) -> str:
    condition = generate_condition(node.condition, pin_map)
    true_branch = "\n".join(
        code
        for statement in node.true_branch
        if (code := generate_c(statement, pin_map, indent_level + 1))
    )
    false_branch = "\n".join(
        code
        for statement in node.false_branch
        if (code := generate_c(statement, pin_map, indent_level + 1))
    )

    if not true_branch and not false_branch:
        return ""

    code = (
        f"{indent(indent_level)}if ({condition}) {{\n"
        f"{true_branch}\n"
        f"{indent(indent_level)}}}"
    )

    if false_branch:
        code += (
            " else {\n"
            f"{false_branch}\n"
            f"{indent(indent_level)}}}"
        )

    return code


def generate_assign(node: AssignNode, pin_map: dict, indent_level: int = 0) -> str:
    output_state = pin_map["outputs"][node.variable]["state"]
    value = VALUE_MACROS[node.value]
    return f"{indent(indent_level)}{output_state} = {value};"


def generate_timer(node: TimerNode, pin_map: dict, indent_level: int = 0) -> str:
    in_value = generate_timer_input(node, pin_map)
    return (
        f"{indent(indent_level)}{node.name}.IN = {in_value};\n"
        f"{indent(indent_level)}updateTON(&{node.name});"
    )


def generate_condition(condition: str, pin_map: dict) -> str:
    tokens = []
    for token in tokenize_condition(condition):
        if token == "AND":
            tokens.append("&&")
        elif token == "OR":
            tokens.append("||")
        elif token in ("(", ")"):
            tokens.append(token)
        elif "." in token:
            tokens.append(token)
        else:
            condition_pin = pin_map["inputs"][token]["macro"]
            tokens.append(f"digitalRead({condition_pin})")
    return " ".join(tokens).replace("( ", "(").replace(" )", ")")


def generate_timer_input(node: TimerNode, pin_map: dict) -> str:
    if node.input_source:
        return generate_condition(node.input_source, pin_map)
    return VALUE_MACROS[node.in_value]


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
            "state": make_state_variable(variable),
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
            for variable in collect_condition_inputs(node.condition):
                add_once(inputs, variable)
            for statement in node.true_branch:
                visit(statement)
            for statement in node.false_branch:
                visit(statement)
        elif isinstance(node, AssignNode):
            add_once(outputs, node.variable)
        elif isinstance(node, TimerNode):
            if node.input_source:
                for variable in collect_condition_inputs(node.input_source):
                    add_once(inputs, variable)
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


def collect_timers(ast) -> list[TimerNode]:
    timers = []
    seen = set()

    def visit(node):
        if isinstance(node, ProgramNode):
            for statement in node.statements:
                visit(statement)
        elif isinstance(node, IfNode):
            for statement in node.true_branch:
                visit(statement)
            for statement in node.false_branch:
                visit(statement)
        elif isinstance(node, TimerNode) and node.name not in seen:
            timers.append(node)
            seen.add(node.name)

    visit(ast)
    return timers


def generate_timer_type(timers: list[TimerNode]) -> str:
    if not timers:
        return ""
    return (
        "typedef struct {\n"
        f"{indent(1)}bool IN;\n"
        f"{indent(1)}bool Q;\n"
        f"{indent(1)}unsigned long startTime;\n"
        f"{indent(1)}unsigned long PT;\n"
        "} TON;"
    )


def generate_timer_update_function(timers: list[TimerNode]) -> str:
    if not timers:
        return ""
    return (
        "void updateTON(TON *t) {\n"
        f"{indent(1)}if (t->IN) {{\n"
        f"{indent(2)}if (t->startTime == 0) {{\n"
        f"{indent(3)}t->startTime = millis();\n"
        f"{indent(2)}}}\n"
        f"{indent(2)}if (millis() - t->startTime >= t->PT) {{\n"
        f"{indent(3)}t->Q = true;\n"
        f"{indent(2)}}}\n"
        f"{indent(1)}}} else {{\n"
        f"{indent(2)}t->startTime = 0;\n"
        f"{indent(2)}t->Q = false;\n"
        f"{indent(1)}}}\n"
        "}"
    )


def generate_timer_declarations(timers: list[TimerNode]) -> str:
    return "\n".join(f"TON {timer.name};" for timer in timers)


def generate_timer_setup(timers: list[TimerNode]) -> str:
    lines = []
    for timer in timers:
        lines.append(f"{indent(1)}{timer.name}.IN = false;")
        lines.append(f"{indent(1)}{timer.name}.Q = false;")
        lines.append(f"{indent(1)}{timer.name}.startTime = 0;")
        lines.append(f"{indent(1)}{timer.name}.PT = {timer.pt};  // preset time in ms")
    return "\n".join(lines)


def generate_output_state_declarations(pin_map: dict) -> str:
    lines = []
    for variable in pin_map["outputs"].values():
        lines.append(f"bool {variable['state']} = false;")
    return "\n".join(lines)


def generate_output_state_resets(pin_map: dict) -> str:
    lines = []
    for variable in pin_map["outputs"].values():
        lines.append(f"{indent(1)}{variable['state']} = false;")
    return "\n".join(lines)


def generate_output_writes(pin_map: dict) -> str:
    lines = []
    for variable in pin_map["outputs"].values():
        lines.append(
            f"{indent(1)}digitalWrite({variable['macro']}, {variable['state']} ? HIGH : LOW);"
        )
    return "\n".join(lines)


def make_pin_macro(variable: str) -> str:
    return f"{variable.upper()}_PIN"


def make_state_variable(variable: str) -> str:
    return f"{variable}_state"


def split_condition(condition: str) -> list[str]:
    return [
        token
        for token in tokenize_condition(condition)
        if token not in ("AND", "OR", "(", ")")
    ]


def collect_condition_inputs(condition: str) -> list[str]:
    return [part for part in split_condition(condition) if "." not in part]


def tokenize_condition(condition: str) -> list[str]:
    spaced = condition.replace("(", " ( ").replace(")", " ) ")
    return [token for token in spaced.split() if token]
