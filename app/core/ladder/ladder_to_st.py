def ladder_to_st(ladder_code: str) -> str:
    blocks = []
    lines = [line.strip() for line in ladder_code.splitlines() if line.strip()]
    timers = collect_timers(lines)

    for line in lines:
        condition_text, output = line.split("->", 1)
        condition = convert_condition(condition_text, timers)
        output = output.strip()

        if is_jsr_output(output):
            subroutine_name = parse_jsr_output(output)
            blocks.append(
                f"IF {condition} THEN\n"
                f"JSR {subroutine_name};\n"
                "END_IF;"
            )
        elif is_timer_output(output):
            timer_name, preset_time = parse_timer_output(output)
            blocks.append(
                f"IF {condition} THEN\n"
                f"{timer_name}(IN:=TRUE, PT:={preset_time});\n"
                "END_IF;"
            )
        else:
            blocks.append(
                f"IF {condition} THEN\n"
                f"{output} := TRUE;\n"
                "END_IF;"
            )

    return "\n\n".join(blocks)


def convert_condition(condition_text: str, timers: set[str]) -> str:
    branches = []

    for branch in condition_text.split("|"):
        contacts = [contact.strip() for contact in branch.split("&")]
        contacts = [contact for contact in contacts if contact]
        contacts = [convert_contact(contact, timers) for contact in contacts]
        condition = " AND ".join(contacts)
        if len(contacts) > 1 and "|" in condition_text:
            condition = f"({condition})"
        branches.append(condition)

    return " OR ".join(branches)


def collect_timers(lines: list[str]) -> set[str]:
    timers = set()
    for line in lines:
        output = line.split("->", 1)[1].strip()
        if is_jsr_output(output):
            continue
        if is_timer_output(output):
            timer_name, _ = parse_timer_output(output)
            timers.add(timer_name)
    return timers


def convert_contact(contact: str, timers: set[str]) -> str:
    if contact in timers:
        return f"{contact}.Q"
    return contact


def is_timer_output(output: str) -> bool:
    return "(" in output and output.endswith(")")


def parse_timer_output(output: str) -> tuple[str, str]:
    timer_name, preset_time = output.split("(", 1)
    return timer_name.strip(), preset_time.rstrip(")").strip()


def is_jsr_output(output: str) -> bool:
    return output.startswith("JSR(") and output.endswith(")")


def parse_jsr_output(output: str) -> str:
    return output[len("JSR("):-1].strip()
