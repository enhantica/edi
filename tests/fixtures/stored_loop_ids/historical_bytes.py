"""Restore only the prior ordinal spelling after proving stored input identities."""

import re

TOKEN = re.compile(rb"'[^']*'|\"[^\"]*\"|[^\s]+")


def loop_ids(data, category):
    lines = data.splitlines(keepends=True)
    result = []
    offset = 0
    tags = None
    in_rows = False
    for line in lines:
        word = line.strip()
        if word == b'loop_':
            tags = []
            in_rows = False
        elif tags is not None and word.startswith(b'_'):
            if in_rows:
                tags = None
            else:
                tags.append(word)
        elif tags and word and not word.startswith(b'#'):
            if word.startswith((b'data_', b'loop_')):
                tags = None
            elif any(tag.startswith(category + b'.') for tag in tags):
                in_rows = True
                cells = list(TOKEN.finditer(line))
                if len(cells) != len(tags):
                    message = 'Stored-id mapping requires complete loop rows'
                    raise ValueError(message)
                if category + b'.id' not in tags:
                    result.append((offset, offset, str(len(result) + 1).encode()))
                    offset += len(line)
                    continue
                cell = cells[tags.index(category + b'.id')]
                raw = cell.group()
                decoded = raw[1:-1] if raw[:1] in {b"'", b'"'} else raw
                result.append((offset + cell.start(), offset + cell.end(), decoded))
        offset += len(line)
    return result


def historical_stored_ids(name, source, saved):
    if not name.startswith('experiments/'):
        return saved
    replacements = []
    for category in (b'_background', b'_excluded_region'):
        supplied = loop_ids(source, category)
        emitted = loop_ids(saved, category)
        if [row[2] for row in supplied] != [row[2] for row in emitted]:
            message = 'ADR-0083 saved stored ids must equal each supplied key in order'
            raise ValueError(message)
        replacements.extend(
            (start, end, str(i).encode()) for i, (start, end, _) in enumerate(emitted, 1)
        )
    for start, end, ordinal in sorted(replacements, reverse=True):
        saved = saved[:start] + ordinal + saved[end:]
    return saved
