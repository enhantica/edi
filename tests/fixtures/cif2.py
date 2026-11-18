"""CIF2 compound-token projection for independent Gemmi scalar/category checks.

ADR-0097 permits nested, quoted and multiline list cells. Gemmi's scalar CIF
reader sees each complete list as one quoted cell; its contents are retained.
This is not a product loader and never supplies expected numerical values.
"""

import gemmi


def quoted_end(text, start):
    quote = text[start]
    delimiter = quote * 3 if text.startswith(quote * 3, start) else quote
    cursor = start + len(delimiter)
    while cursor < len(text):
        if text.startswith(delimiter, cursor):
            end = cursor + len(delimiter)
            if len(delimiter) == 3 or end == len(text) or text[end].isspace() or text[end] in '[]':
                return end
        cursor += 1
    message = 'Unclosed quoted CIF token'
    raise ValueError(message)


def list_end(text, start):
    depth, cursor = 0, start
    while cursor < len(text):
        char = text[cursor]
        if char == '#':
            end = text.find('\n', cursor)
            cursor = len(text) if end < 0 else end + 1
            continue
        if char in '"\'':
            cursor = quoted_end(text, cursor)
            continue
        if char == '[':
            depth += 1
        elif char == ']':
            depth -= 1
            if depth == 0:
                return cursor + 1
        cursor += 1
    message = 'Unclosed CIF2 list'
    raise ValueError(message)


def scalar_text(text):
    output, cursor = [], 0
    while cursor < len(text):
        char = text[cursor]
        if char == '#':
            end = text.find('\n', cursor)
            end = len(text) if end < 0 else end + 1
        elif char in '"\'':
            end = quoted_end(text, cursor)
        elif char == ';' and (cursor == 0 or text[cursor - 1] == '\n'):
            close = text.find('\n;', cursor + 1)
            if close < 0:
                message = 'Unclosed CIF text field'
                raise ValueError(message)
            end = close + 2
        elif char == '[' and (cursor == 0 or text[cursor - 1].isspace()):
            assert text.startswith('#\\#CIF_2.0'), (
                'A compound cell must carry the ADR-0097 CIF2 file heading'
            )
            end = list_end(text, cursor)
            output.append('\n' + gemmi.cif.quote(text[cursor:end]) + '\n')
            cursor = end
            continue
        else:
            end = cursor + 1
        output.append(text[cursor:end])
        cursor = end
    return ''.join(output)


def read_block(text):
    return gemmi.cif.read_string(scalar_text(text)).sole_block()
