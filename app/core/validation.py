LOGIC_TYPES = {"Digital Input", "Digital Output", "Analog Input", "Analog Output", "PWM Output", "UART TX", "UART RX"}


def validation(mapping, ladder_code: str, global_variables: list = None) -> list[str]:
    """Validate ladder code against global variables and optional IO mapping"""
    errors = []
    tag_map = {}
    seen_tags = set()
    seen_pins = set()
    
    # Use global variables as primary source of truth
    if global_variables:
        global_var_names = set()
        for var in global_variables:
            var_name = var["name"].strip()
            var_type = var["type"].strip()
            var_address = var.get("address", "").strip()
            
            if var_name in seen_tags:
                errors.append(f"[ERROR] duplicate variable name: {var_name}")
            seen_tags.add(var_name)
            global_var_names.add(var_name.upper())
            
            # Determine variable class and type for validation
            if var_type in ["Digital Input", "Digital Output", "Analog Input", "Analog Output"]:
                # Physical I/O types - check if they have GPIO assignments
                if not var_address:
                    errors.append(f"[WARNING] Physical I/O variable '{var_name}' has no GPIO address assigned")
                tag_map[var_name.upper()] = {"type": "input" if "Input" in var_type else "output", 
                                         "class": "physical", "address": var_address}
            elif var_type in ["TON", "TOF", "TP"]:
                tag_map[var_name.upper()] = {"type": "timer", "class": "timer", "address": var_address}
            elif var_type == "COUNTER":
                tag_map[var_name.upper()] = {"type": "counter", "class": "counter", "address": var_address}
            else:
                # Internal variables (BOOL, INT, REAL, STRING)
                tag_map[var_name.upper()] = {"type": "internal", "class": "internal", "address": var_address}
        
        # Validate ladder code against global variables
        errors.extend(validate_ladder_tags(tag_map, ladder_code))
    
    # Optional: Validate IO mapping for hardware assignments
    if mapping:
        for row in mapping:
            pin = row["pin"]
            tag = row["tag"].strip()
            pin_type = row["type"]
            
            if pin in seen_pins:
                errors.append(f"[ERROR] GPIO {pin} assigned multiple times")
            seen_pins.add(pin)
            
            # Check if type is a logic type (contains Input or Output)
            type_lower = pin_type.lower()
            is_logic_type = "input" in type_lower or "output" in type_lower
            
            if is_logic_type and not tag:
                errors.append(f"[ERROR] GPIO {pin} is {pin_type} but has no tag name")
                continue
            
            # Check if tag exists in global variables
            if tag and global_variables:
                tag_found = False
                for var in global_variables:
                    if var["name"].upper() == tag.upper():
                        tag_found = True
                        break
                
                if not tag_found:
                    errors.append(f"[WARNING] IO Mapping tag '{tag}' not found in Global Variables")
    
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
            # Case-insensitive lookup against global variables
            contact_upper = contact.upper()
            if contact_upper not in tag_map:
                errors.append(f"[ERROR] Symbol '{contact}' is not declared in Global Variables")
            elif tag_map[contact_upper]["type"] == "output":
                errors.append(f"[ERROR] {contact} is an Output, cannot be used as Input condition")

        if is_timer_output(output):
            continue

        # Case-insensitive lookup for output
        output_upper = output.upper()
        if output_upper not in tag_map:
            errors.append(f"[ERROR] Symbol '{output}' is not declared in Global Variables")
        elif tag_map[output_upper]["type"] != "output" and tag_map[output_upper]["type"] != "internal":
            errors.append(f"[ERROR] {output} is not an Output or Internal variable, cannot be used as Output coil")

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
