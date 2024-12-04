import re

def parse_reg(line):
    def get_width(width_text):

        width_text = width_text.replace(']', '').replace('[', '').replace(' ', '')
        num_list = width_text.split(':')
        if len(num_list) != 2:
            raise ValueError(f"Invalid width format: {width_text}")
        return abs(int(num_list[0]) - int(num_list[1])) + 1

    pattern = r'(?:output\s+)?reg\s*(?:\[(.*?)\])?\s*([^\s;]*)'
    match = re.match(pattern, line)

    if not match:
        raise ValueError(f"Invalid reg declaration: {line}")

    width_text = match.group(1)
    signal_part = match.group(2)

    reg_width = get_width(width_text) if width_text else 1

    signal_names = [name.strip() for name in signal_part.split(',')]

    return {name: reg_width for name in signal_names}

# line = "reg reg [7:0] a, b, c;"
line = "output  reg [3: 0] a"

print(parse_reg(line))