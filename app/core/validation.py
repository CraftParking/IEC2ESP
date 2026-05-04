LOGIC_TYPES = {"Input", "Output"}


def validation(mapping, ladder_code: str) -> list[str]:
    errors = []
    tag_map = {}
    seen_tags = set()
    seen_pins = set()

    for row in mapping:
        pin = row["pin"]
        tag = row["tag"].strip()
        pin_type = row["type"]

        if pin in seen_pins:
            errors.append(f"[ERROR] GPIO {pin} assigned multiple times")
        seen_pins.add(pin)

        if pin_type in LOGIC_TYPES and not tag:
            errors.append(f"[ERROR] GPIO {pin} is {pin_type} but has no tag name")
            continue

        if tag:
            if tag in seen_tags:
                errors.append(f"[ERROR] duplicate tag name: {tag}")
            seen_tags.add(tag)
            if pin_type in LOGIC_TYPES:
                tag_map[tag] = {"pin": pin, "type": pin_type.lower()}

    errors.extend(validate_ladder_tags(tag_map, ladder_code))
    return errors


def validate_ladder_tags(tag_map: dict, ladder_code: str) -> list[str]:
    errors = []
    lines = [line.strip() for line in ladder_code.splitlines() if line.strip()]
    timers = collect_timer_names(lines)

    for line in lines:
        if "->" not in line:
            continue

        condition_text, output_text = line.split("->", 1)
        output = output_text.strip()

        for contact in extract_condition_contacts(condition_text):
            if contact in timers:
                continue
            if contact not in tag_map:
                errors.append(f"[ERROR] {contact} not defined in IO Mapping")
            elif tag_map[contact]["type"] == "output":
                errors.append(f"[ERROR] {contact} is an Output, cannot be used as Input condition")

        if is_timer_output(output):
            continue

        if output not in tag_map:
            errors.append(f"[ERROR] {output} not defined in IO Mapping")
        elif tag_map[output]["type"] != "output":
            errors.append(f"[ERROR] {output} is an Input, cannot be used as Output coil")

    return errors


def collect_timer_names(lines: list[str]) -> set[str]:
    timers = set()
    for line in lines:
        if "->" not in line:
            continue
        output = line.split("->", 1)[1].strip()
        if is_timer_output(output):
            timers.add(output.split("(", 1)[0].strip())
    return timers


def extract_condition_contacts(condition_text: str) -> list[str]:
    contacts = []
    for branch in condition_text.split("|"):
        for contact in branch.split("&"):
            contact = contact.strip()
            if contact:
                contacts.append(contact)
    return contacts


def is_timer_output(output: str) -> bool:
    return "(" in output and output.endswith(")")
