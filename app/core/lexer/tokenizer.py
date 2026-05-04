import re


TOKEN_PATTERNS = [
    ("ASSIGN", r":="),
    ("SEMICOLON", r";"),
    ("LPAREN", r"\("),
    ("RPAREN", r"\)"),
    ("COMMA", r","),
    ("DOT", r"\."),
    ("NUMBER", r"\d+"),
    ("IF", r"\bIF\b"),
    ("THEN", r"\bTHEN\b"),
    ("ELSE", r"\bELSE\b"),
    ("END_IF", r"\bEND_IF\b"),
    ("AND", r"\bAND\b"),
    ("OR", r"\bOR\b"),
    ("TRUE", r"\bTRUE\b"),
    ("FALSE", r"\bFALSE\b"),
    ("IDENTIFIER", r"\b[A-Za-z_][A-Za-z0-9_]*\b"),
    ("WHITESPACE", r"\s+"),
]


TOKEN_REGEX = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_PATTERNS))


def tokenize(code: str) -> list[tuple[str, str]]:
    tokens = []
    position = 0

    while position < len(code):
        match = TOKEN_REGEX.match(code, position)
        if not match:
            raise SyntaxError(f"Unexpected character: {code[position]!r}")

        token_type = match.lastgroup
        value = match.group()

        if token_type != "WHITESPACE":
            tokens.append((token_type, value))

        position = match.end()

    return tokens
