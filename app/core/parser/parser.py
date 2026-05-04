from app.core.parser.ast_nodes import AssignNode, IfNode, ProgramNode


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.position = 0

    def current(self):
        if self.position >= len(self.tokens):
            return ("EOF", "")
        return self.tokens[self.position]

    def eat(self, token_type):
        current_type, value = self.current()
        if current_type != token_type:
            raise SyntaxError(f"Expected {token_type}, got {current_type}")
        self.position += 1
        return value

    def parse(self):
        statements = []
        while self.current()[0] != "EOF":
            statements.append(self.parse_statement())
        return ProgramNode(statements)

    def parse_statement(self):
        if self.current()[0] == "IF":
            return self.parse_if()
        if self.current()[0] == "IDENTIFIER":
            return self.parse_assign()
        raise SyntaxError(f"Unexpected token: {self.current()[0]}")

    def parse_if(self):
        self.eat("IF")
        condition = self.eat("IDENTIFIER")
        self.eat("THEN")
        true_branch = self.parse_block()
        false_branch = []
        if self.current()[0] == "ELSE":
            self.eat("ELSE")
            false_branch = self.parse_block()
        self.eat("END_IF")
        self.eat("SEMICOLON")
        return IfNode(condition, true_branch, false_branch)

    def parse_block(self):
        statements = []
        while self.current()[0] not in ("ELSE", "END_IF", "EOF"):
            statements.append(self.parse_statement())
        return statements

    def parse_assign(self):
        variable = self.eat("IDENTIFIER")
        self.eat("ASSIGN")
        value_type, value = self.current()
        if value_type not in ("TRUE", "FALSE"):
            raise SyntaxError(f"Expected TRUE or FALSE, got {value_type}")
        self.eat(value_type)
        self.eat("SEMICOLON")
        return AssignNode(variable, value)
