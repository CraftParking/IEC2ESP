from app.core.parser.ast_nodes import AssignNode, IfNode, ProgramNode, TimerNode


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.position = 0

    def current(self):
        if self.position >= len(self.tokens):
            return ("EOF", "")
        return self.tokens[self.position]

    def peek(self):
        if self.position + 1 >= len(self.tokens):
            return ("EOF", "")
        return self.tokens[self.position + 1]

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

    def parse_statement(self, active_condition=None):
        if self.current()[0] == "IF":
            return self.parse_if()
        if self.current()[0] == "IDENTIFIER":
            if self.peek()[0] == "LPAREN":
                return self.parse_timer_call(active_condition)
            return self.parse_assign()
        raise SyntaxError(f"Unexpected token: {self.current()[0]}")

    def parse_if(self):
        self.eat("IF")
        condition = self.parse_condition()
        self.eat("THEN")
        true_branch = self.parse_block(active_condition=condition)
        false_branch = []
        if self.current()[0] == "ELSE":
            self.eat("ELSE")
            false_branch = self.parse_block()
        self.eat("END_IF")
        self.eat("SEMICOLON")
        return IfNode(condition, true_branch, false_branch)

    def parse_condition(self):
        parts = [self.parse_condition_token()]
        while self.current()[0] not in ("THEN", "EOF"):
            current_type, value = self.current()
            if current_type not in ("AND", "OR", "LPAREN", "RPAREN", "IDENTIFIER", "DOT"):
                break
            if current_type == "IDENTIFIER":
                parts.append(self.parse_condition_part())
            else:
                parts.append(value)
                self.eat(current_type)
        return " ".join(parts)

    def parse_condition_token(self):
        if self.current()[0] == "LPAREN":
            self.eat("LPAREN")
            return "("
        return self.parse_condition_part()

    def parse_condition_part(self):
        condition = self.eat("IDENTIFIER")
        if self.current()[0] == "DOT":
            self.eat("DOT")
            condition += f".{self.eat('IDENTIFIER')}"
        return condition

    def parse_block(self, active_condition=None):
        statements = []
        while self.current()[0] not in ("ELSE", "END_IF", "EOF"):
            statements.append(self.parse_statement(active_condition))
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

    def parse_timer_call(self, active_condition=None):
        name = self.eat("IDENTIFIER")
        self.eat("LPAREN")
        self.eat("IDENTIFIER")
        self.eat("ASSIGN")
        in_type, in_value = self.current()
        if in_type not in ("TRUE", "FALSE"):
            raise SyntaxError(f"Expected TRUE or FALSE, got {in_type}")
        self.eat(in_type)
        self.eat("COMMA")
        self.eat("IDENTIFIER")
        self.eat("ASSIGN")
        pt = self.eat("NUMBER")
        self.eat("RPAREN")
        self.eat("SEMICOLON")
        input_source = active_condition if in_value == "TRUE" else None
        return TimerNode(name, in_value, int(pt), input_source)
