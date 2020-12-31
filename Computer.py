import logging
import re
import shlex
import sys
import termios
import tty


def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    return ch


class Register:
    def __init__(self, idx):
        self.idx = idx

    def __repr__(self):
        return f'Register {self.idx}'


class String:
    def __init__(self, val):
        self.val = val

    def __repr__(self):
        return f'String "{self.val}"'


class Integer:
    def __init__(self, val):
        self.val = val

    def __repr__(self):
        return f'Integer {self.val}'


class Label:
    def __init__(self, name):
        if match := re.search(r'(\w+)\[(-?\d+)\]', name):
            self.name = match.group(1)
            self.offset = int(match.group(2))
        else:
            self.name = name
            self.offset = 0

    def __repr__(self):
        return f'Label "{self.name}"'


class Statement:
    def __init__(self, operator, operands, label):
        self.operator = operator
        self.operands = operands
        self.label = label

    def __repr__(self):
        return f'Statement<{self.operator}'  + (f', "{self.label}"' if self.label else '') + '>'


def parse(text):
    if match := re.search(r'^r(\d+)', text):
        return Register(int(match.group(1)))
    elif match := re.search(r"^'(.*)'", text):
        return String(match.group(1))
    elif match := re.search(r'^-?0x[\da-fA-F]+', text):
        return Integer(int(text, 16))
    elif match := re.search(r'^-?\d+', text):
        return Integer(int(text))
    else:
        return Label(text)


class Computer:
    def __init__(self, memory_size=1024):
        self.pc = 0
        self.dc = 0
        self.label_map = {}
        self.addr_map = {}
        self.instruction_map = {}
        self.statements = []
        self.registers = [0, 1] + [0 for i in range(13)] + [0]
        self.memory = [0] * memory_size

    def register_get(self, reg):
        if reg.idx < 2:
            return reg.idx

        return self.registers[reg.idx]

    def register_set(self, reg, val):
        if reg.idx > 1:
            self.registers[reg.idx] = val

    def memory_get(self, addr):
        return self.memory[addr]

    def memory_set(self, addr, val):
        self.memory[addr] = val

    def label_to_pc(self, label):
        return self.label_map[label.name]

    def label_to_mem(self, label):
        label_pc = self.label_to_pc(label)

        return self.addr_map[label_pc] + label.offset

    def set_fs_root(self, fs_root):
        self.fs_root = fs_root

    def set_instructions(self, instructions):
        self.instruction_map = instructions

    def compile(self, call):
        # Look for a label, if applicable
        if ':' in call:
            label, call = call.split(':', 1)
            label = label.strip()
            self.label_map[label] = self.pc
        else:
            label = None

        # Catch empty lines (full-line comments, etc.)
        if not call.strip():
            return None

        # Tokenize the call, preserving quoted strings
        shlex.commenters = '#'
        tokens = shlex.split(call, comments=True, posix=False)

        # Discard comments
        if not tokens:
            return None

        operator, operands = tokens[0], tokens[1:]

        # Parse the raw operands into their appropriate types
        operands = [parse(operand) for operand in operands]

        # Handle pre-processor macros
        if operator == 'inc':
            self.load_file(operands[0].val)
            return None

        # Generate the statement
        statement = Statement(operator, operands, label)

        # Increment the program counter
        self.pc += 1

        return statement

    def execute(self, statement):
        fn = self.instruction_map.get(statement.operator, None)

        if not fn:
            logging.warning('Instruction with operator "{}" not found'.format(statement.operator))
            return

        status = fn(self, statement)
        self.register_set(Register(15), status)

    def load_file(self, filename):
        with open(f'{self.fs_root}/{filename}', 'r') as f:
            lines = f.readlines()
            for line in lines:
                statement = self.compile(line)
                if statement:
                    self.statements.append(statement)

    def boot(self):
        self.load_file('boot.nla')
        self.pc = 0

        while self.pc < len(self.statements):
            statement = self.statements[self.pc]
            self.execute(statement)

            # A status of -1 tells the computer to exit immediately
            if self.register_get(Register(15)) == -1:
                break

            self.pc += 1

