"""Map the declared follower-flag cleanup back to the immutable NCAF byte witness.

Only the three named x,x,x rows lose their y/z uncertainty brackets. Restoring
those brackets from each unchanged x token preserves the historical regression
identity without accepting any other input or saved-byte change.
"""

import re

SITES = {'Al1', 'Na1', 'F3'}


def historical_followers(name, contents):
    if name != 'structures/ncaf.edi':
        return contents
    lines = []
    seen = set()
    for original_line in contents.decode().splitlines(keepends=True):
        line = original_line
        tokens = list(re.finditer(r'\S+', line))
        if tokens and tokens[0][0] in SITES:
            site = tokens[0][0]
            if site in seen or len(tokens) < 6:
                message = 'the follower byte mapping requires one complete row per site'
                raise ValueError(message)
            seen.add(site)
            leader = tokens[2][0]
            match = re.fullmatch(r'(.+)\(\d*\)', leader)
            if (
                match is None
                or tokens[5][0] != 'a'
                or any(tokens[index][0] != match[1] for index in (3, 4))
            ):
                message = 'the follower byte mapping requires a free x and bare x,x,x followers'
                raise ValueError(message)
            for index in (4, 3):
                token = tokens[index]
                line = line[: token.start()] + leader + line[token.end() :]
        lines.append(line)
    if seen != SITES:
        message = 'the follower byte mapping must reach exactly three declared sites'
        raise ValueError(message)
    return ''.join(lines).encode()
