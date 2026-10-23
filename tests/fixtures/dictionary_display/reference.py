"""Independent reference readers and Python's display-format oracle."""

import math
import re


def key(tag):
    return tag.lower().replace('.', '_', 1)


def display(value, kind, digits):
    text = format(value, f'.{digits}{"f" if kind == "fixed" else "g"}')
    if math.isfinite(value) and re.fullmatch(r'-?0(?:\.0+)?', text):
        text = text.removeprefix('-')
    return re.sub(r'e([+-]?)(0*)(\d+)', lambda m: 'e' + ('-' if m[1] == '-' else '') + m[3], text)


def official_frames(root):
    result = {}
    for filename in ('cif_core.dic', 'cif_pow.dic'):
        text = (root / 'data/cif-dictionaries' / filename).read_text()
        # DDLm has CIF2 containers, which gemmi's CIF1 reader does not parse.
        # Only definition and alias columns are needed; descriptions are excluded.
        text = re.sub(r'(?ms)^;.*?^;[^\n]*', '', text)
        for frame in re.split(r'(?m)^save_', text)[1:]:
            found = re.search(r"_definition\.id[ \t]+['\"]?(_[^'\"\s]+)", frame)
            if found is None:
                continue
            name = found[1]
            aliases = []
            lines = frame.splitlines()
            for index, line in enumerate(lines):
                if not line.strip().startswith('_alias.definition_id'):
                    continue
                section = line.partition('_alias.definition_id')[2]
                for following in lines[index + 1 :]:
                    if following.strip().startswith('_') and not following.strip().startswith(
                        '_alias.'
                    ):
                        break
                    section += '\n' + following
                aliases.extend(re.findall(r"['\"](_[^'\"\s]+)['\"]", section))
            names = {name, *aliases}
            for spelling in names:
                result[key(spelling)] = (name, names)
    return result
