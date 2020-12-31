#!/usr/bin/env python3

import logging

from Computer import Computer, Register, String, Integer, Label, getch

# Here's our architecture:
# We have sixteen 64-bit registers
# Two are read-only. They are r0, which always contains zero,
# and r1, which always contains one.
# The next thirteen registers, r2-r14, are general purpose read-write
# There is an additional read-only status register, r15 aka rs


def fn_chr(computer, statement):
    if statement.label:
        computer.addr_map[computer.pc] = computer.dc

    for operand in statement.operands:
        if type(operand) is Integer:
            computer.memory_set(computer.dc, operand.val)
            computer.dc += 1
        elif type(operand) is String:
            for c in operand.val:
                computer.memory_set(computer.dc, ord(c))
                computer.dc += 1

    return 0


def fn_mov(computer, statement):
    target, source = statement.operands

    if type(source) is Integer:
        computer.register_set(target, source.val)
    elif type(source) is String:
        computer.register_set(target, ord(source.val[0]))
    elif type(source) is Register:
        computer.register_set(target, computer.register_get(source))
    elif type(source) is Label:
        if source.name not in computer.label_map:
            logging.warning('Label not found')
            return 1

        computer.register_set(target, computer.label_to_pc(source))

    return 0


def fn_sys(computer, statement):
    call = computer.register_get(Register(2))

    if call == 0x00:
        ch = ord(getch())
        computer.register_set(Register(3), ch)
    elif call == 0x01:
        start = computer.register_get(Register(3))
        length = computer.register_get(Register(4))
        addr = computer.addr_map[start]

        if length == 0:
            while ch := computer.memory_get(addr):
                print(chr(ch), end='', flush=True)
                addr += 1
        else:
            for i in range(length):
                ch = computer.memory_get(addr)
                print(chr(ch), end='', flush=True)
                addr += 1

    return 0


def fn_jmp(computer, statement):
    cond_reg, label = statement.operands

    if (cond := computer.register_get(cond_reg)) > 0:
        computer.pc = computer.label_to_pc(label) - 1

    return 0


def fn_xor(computer, statement):
    target, source = statement.operands

    if type(source) is Integer:
        computer.register_set(target, computer.register_get(target) ^ source.val)
    elif type(source) is Register:
        computer.register_set(target, computer.register_get(target) ^ computer.register_get(source))

    return 0


def fn_nop(computer, statement):
    return 0


def fn_dmp(computer, statement):
    if statement.operands:
        op = statement.operands[0]

        if type(op) is Integer:
            addr = op.val
        elif type(op) is Label:
            addr = computer.label_to_mem(op)

        print('{0:02x}'.format(computer.memory[addr]))

        return 0

    bytes_per_row = 16

    mem_list = [computer.memory[i:i+bytes_per_row] for i in range(0, len(computer.memory), bytes_per_row)]
    idx = 0

    print(' ' * 7 + ' '.join(['{0:01x}'.format(i).rjust(2) for i in range(bytes_per_row)]))

    for row in mem_list:
        print('{0:0{1}x}'.format(idx, 4)[:3] + '- | ' + ' '.join('{0:0{1}x}'.format(item, 2) for item in row))
        idx += bytes_per_row

    return 0


def fn_lbl(computer, statement):
    for label in computer.label_map:
        pc = computer.label_map[label]
        mem = '0x{0:04x}'.format(computer.addr_map[pc]) if pc in computer.addr_map else 'N/A'
        print(f'{label} ({pc}) -> {mem}')


def fn_reg(computer, statement):
    for i, reg in enumerate(computer.registers):
        print(f'{i:>2}: {reg}')
    return computer.register_get(Register(15))


def fn_add(computer, statement):
    target, a, b = statement.operands

    if type(a) is Integer:
        a = a.val
    elif type(a) is Register:
        a = computer.register_get(a)

    if type(b) is Integer:
        b = b.val
    elif type(b) is Register:
        b = computer.register_get(b)

    computer.register_set(target, a + b)

    return 0


def fn_sub(computer, statement):
    target, a, b = statement.operands

    if type(a) is Integer:
        a = a.val
    elif type(a) is Register:
        a = computer.register_get(a)

    if type(b) is Integer:
        b = b.val
    elif type(b) is Register:
        b = computer.register_get(b)

    computer.register_set(target, a - b)


def fn_div(computer, statement):
    target, a, b = statement.operands

    if type(a) is Integer:
        a = a.val
    elif type(a) is Register:
        a = computer.register_get(a)

    if type(b) is Integer:
        b = b.val
    elif type(b) is Register:
        b = computer.register_get(b)

    computer.register_set(target, a // b)

    return 0


def fn_mod(computer, statement):
    target, a, b = statement.operands

    if type(a) is Integer:
        a = a.val
    elif type(a) is Register:
        a = computer.register_get(a)

    if type(b) is Integer:
        b = b.val
    elif type(b) is Register:
        b = computer.register_get(b)

    computer.register_set(target, int(a % b))

    return 0


def fn_res(computer, statement):
    amount = statement.operands[0]

    if statement.label:
        computer.addr_map[computer.pc] = computer.dc

        if type(amount) is Integer:
            amount = amount.val
        elif type(amount) is Register:
            amount = computer.register_get(amount)

        computer.dc += amount

    return 0


def fn_ptr(computer, statement):
    target, source, offset = statement.operands

    if type(target) is Label:
        if type(offset) is Register:
            val = computer.register_get(offset)

        target_pc = computer.label_to_pc(target)
        computer.addr_map[target_pc] = computer.label_to_mem(source) + val

    return 0


def fn_swp(computer, statement):
    target = statement.operands[0]

    if type(target) is Label:
        loc = computer.label_to_mem(target)
    elif type(target) is Integer:
        loc = target.val
    else:
        return 1

    for i in range(2, 16):
        mem_idx = loc + i - 2
        val = computer.memory_get(mem_idx)
        computer.memory_set(mem_idx, computer.register_get(Register(i)))
        computer.register_set(Register(i), val)

    return 0


def fn_mem(computer, statement):
    target, source = statement.operands

    if type(source) is Label:
        val = computer.memory_get(computer.label_to_mem(source))
    elif type(source) is Register:
        val = computer.register_get(source)
    elif type(source) is Integer:
        val = computer.memory_get(source.val)
    elif type(source) is String:
        val = ord(source.val[0])
    else:
        return 1

    if type(target) is Label:
        computer.memory_set(computer.label_to_mem(target), val)
    elif type(target) is Register:
        computer.register_set(target, val)
    elif type(target) is Integer:
        computer.memory_set(target.val, val)
    else:
        return 2

    return 0


def fn_eql(computer, statement):
    target, a, b = statement.operands

    if type(a) is Integer:
        a = a.val
    elif type(a) is Register:
        a = computer.register_get(a)

    if type(b) is Integer:
        b = b.val
    elif type(b) is Register:
        b = computer.register_get(b)

    computer.register_set(target, int(a == b))

    return 0


def fn_exc(computer, statement):
    label = statement.operands[0]
    addr = computer.label_to_mem(label)

    cmd = ''

    while ch := computer.memory_get(addr):
        cmd += chr(ch)
        addr += 1

    if not cmd:
        return 1

    statement = computer.compile(cmd)

    computer.pc -= 1

    if statement:
        computer.execute(statement)

    return 0


def fn_ext(computer, statement):
    if 'exit' in computer.label_map:
        computer.pc = computer.label_map['exit'] - 1
        return 0

    return -1


def fn_cll(computer, statement):
    label = statement.operands[0]
    computer.addr_stack.append(computer.pc)
    computer.pc = computer.label_to_pc(label) - 1

    return 0


def fn_ret(computer, statement):
    if computer.addr_stack:
        computer.pc = computer.addr_stack.pop() - 1
        return 0

    return 1


instruction_map = {
    'chr': fn_chr,
    'mov': fn_mov,
    'sys': fn_sys,
    'jmp': fn_jmp,
    'xor': fn_xor,
    'nop': fn_nop,
    'dmp': fn_dmp,
    'lbl': fn_lbl,
    'reg': fn_reg,
    'add': fn_add,
    'sub': fn_sub,
    'div': fn_div,
    'mod': fn_mod,
    'res': fn_res,
    'ptr': fn_ptr,
    'swp': fn_swp,
    'mem': fn_mem,
    'eql': fn_eql,
    'exc': fn_exc,
    'ext': fn_ext
}


def main():
    computer = Computer()
    computer.set_fs_root('./fs_root')
    computer.set_instructions(instruction_map)
    computer.boot()


if __name__ == '__main__':
    main()
