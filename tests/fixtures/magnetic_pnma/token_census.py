"""Source census for the ADR-0108 magnetic token boundary; no product code imported."""

import hashlib
import json
import re
from bisect import bisect_right
from collections import Counter, defaultdict
from functools import cache
from pathlib import Path

LEXICAL = re.compile(
    r'//[^\n]*|/\*[\s\S]*?\*/'
    r'|R"([^ ()\\\t\n]{0,16})\([\s\S]*?\)\1"'
    r'|"(?:\\.|[^"\\\n])*"'
    r"|(?<![\w])'(?:\\.|[^'\\\n])*'"
)
DEFINITION = re.compile(r'(?m)^[ \t]*[\w][^;{}=\n]*?\b([A-Za-z_]\w*)\s*\(')
# These consume already decoded domain values or dictionary metadata, not CIF lexemes.
TERMINALS = {
    'half_last_digit',
    'bracketed_number',
    'shortest',
    'shortest_text',
    'shortest_round_trip_double',
    'render_number',
    'split_scientific',
    'ion_table',
    'magnetic_ion_table',
    'dictionary_tag',
    'dictionary_unit',
    'require_model_token',
    'model_token_from_file',
    'file_token_from_model',
    'file_tokens',
    'is_representable_id',
    'space_group_from_file',
    'resolve_space_group_by_hm',
    'magnetic_operations',
    'family_group',
    'magnetic_ion_of',
    'kept_token_value',
    'bare_is_legal',
    'resolve_instrument_label',
}
TERMINAL_SITES = {
    'src/core/symmetry.cpp:resolve_space_group_by_hm',
    'src/core/dictionary.cpp:dictionary_unit',
    'src/core/tokens.cpp:require_model_token',
    'src/core/cif_import.cpp:shortest_text',
    'src/core/magnetic.cpp:magnetic_operations',
    'src/core/magnetic.cpp:magnetic_ion_of',
    'src/core/cif_import.cpp:half_last_digit',
    'src/core/tokens.cpp:file_tokens',
    'src/core/kept_iso.cpp:kept_token_value',
    'src/core/dictionary.cpp:dictionary_tag',
    'src/core/cif_import.cpp:bracketed_number',
    'src/core/double_text.hpp:split_scientific',
    'src/core/cif_import.cpp:shortest',
    'src/core/tokens.cpp:model_token_from_file',
    'src/core/double_text.hpp:shortest_round_trip_double',
    'src/core/tokens.cpp:space_group_from_file',
    'src/core/magnetic.cpp:ion_table',
    'src/core/magnetic.cpp:magnetic_ion_table',
    'src/core/model.cpp:dictionary_tag',
    'src/core/identity.cpp:is_representable_id',
    'src/core/tokens.cpp:file_token_from_model',
    'src/core/expression.cpp:render_number',
    'src/core/magnetic.cpp:family_group',
    'src/core/identity.cpp:bare_is_legal',
}


def terminal(key):
    return key.rsplit(':', 1)[0].removeprefix('engine/') in TERMINAL_SITES


LEXICAL_HELPER = re.compile(
    r'(?:parse|read|token|unquote|unknown|published|bracket|half_last|decode|parameter|literal|component|fraction|triplet|without_blanks|row_moment|moment_form|id_text)',
    re.IGNORECASE,
)
CONTROL_PREFIX = re.compile(r'\s*(?:if|for|while|return|throw|case|else|switch|catch)\b')
CALL = re.compile(r'(?<![\w])\b([A-Za-z_]\w*)\s*\(')
ACCESS = re.compile(
    r'\b(?:get|find|require|scalar|loop|loop_with|loop_cell|column|column_index|row_moment|parse_parameter)\s*\('
)
NON_READER = re.compile(
    r'(?:write|save|document|report|encode|check|validate|columns|keys|categories|map|spec|dictionary|serialize|register|emit|settle)',
    re.IGNORECASE,
)
PRIMITIVE = re.compile(
    r'\b(?:std::)?(?:stod|stof|stold|strtod|strtof|strtold|strtol|strtoll|strtoul|strtoull|atof|atoi|atol|atoll|stoi|stol|stoll|stoul|stoull|from_chars)\s*\('
)
LOCAL_DECODE = re.compile(
    r'(?:==|!=)\s*"[?.]"|"[?.]"\s*(?:==|!=)'
    r'|\.(?:compare|starts_with|ends_with)\s*\(\s*"[?.]"'
    r'|\bstrcmp\s*\([^;]*"[?.]"'
    r'|\.substr\(1,.*size\(\).*2'
)
NUMERIC_ALIAS = re.compile(r'\bstd::(?:stod|stof|strtod|atof|atoi|stoi)\b(?!\s*\()')


def masked(text):
    table = {ord(c): ' ' for c in set(text) if c != '\n'}
    return LEXICAL.sub(lambda match: match[0].translate(table), text)


def delimiter_pairs(clean):
    stacks = {'(': [], '{': []}
    opening = {')': '(', '}': '{'}
    pairs = {}
    for token in re.finditer(r'[(){}]', clean):
        char = token[0]
        if char in stacks:
            stacks[char].append(token.start())
        elif stacks[opening[char]]:
            pairs[stacks[opening[char]].pop()] = token.start()
    return pairs


def matching(text, start, left, right):
    depth = 0
    for i in range(start, len(text)):
        depth += (text[i] == left) - (text[i] == right)
        if depth == 0:
            return i
    raise ValueError('Unbalanced C++ source at ' + str(start))


def functions(sources):
    result = {}
    for path, raw in sources.items():
        clean = masked(raw)
        uncommented = LEXICAL.sub(
            lambda m: ' ' * len(m[0]) if m[0].startswith(('//', '/*')) else m[0], raw
        )
        pairs = delimiter_pairs(clean)
        lines = [-1] + [m.start() for m in re.finditer(r'\n', raw)]
        for macro in re.finditer(r'(?m)^#\s*define\s+(\w+)\s*\(', clean):
            opening = clean.find('(', macro.start())
            closing = pairs[opening]
            end = clean.find('\n', closing)
            end = len(clean) if end < 0 else end
            while end < len(clean) and clean[end - 1] == '\\':
                following = clean.find('\n', end + 1)
                end = len(clean) if following < 0 else following
            key = f'{path}:{macro[1]}:{bisect_right(lines, macro.start())}'
            result[key] = {
                'name': macro[1],
                'body': raw[closing + 1 : end],
                'clean': clean[closing + 1 : end].replace('\\\n', ''),
                'signature': raw[macro.start() : closing + 1],
            }
        for found in DEFINITION.finditer(clean):
            if CONTROL_PREFIX.match(clean, found.start()):
                continue
            name = found[1]
            if name in {'if', 'for', 'while', 'switch', 'catch', 'return', 'sizeof', 'decltype'}:
                continue
            opening = clean.find('(', found.start())
            closing = pairs[opening]
            brace = clean.find('{', closing)
            stop = clean.find(';', closing)
            if brace < 0 or (stop >= 0 and stop < brace):
                continue
            if '=' in clean[closing + 1 : brace] or len(clean[closing + 1 : brace]) > 100:
                continue
            end = pairs[brace]
            key = f'{path}:{name}:{bisect_right(lines, found.start())}'
            result[key] = {
                'name': name,
                'body': uncommented[brace + 1 : end],
                'clean': clean[brace + 1 : end],
                'signature': raw[found.start() : brace],
            }
    return result


def census(sources):
    nodes = functions(sources)
    tags = {}
    for path, text in sources.items():
        joined = re.sub(r'"\s*"', '', text)
        tags[path] = {
            name
            for name, tag in re.findall(
                r'\b(\w+)\s*=\s*"(_?(?:atom_site_moment|magnetic_form_factor|space_group_magn|parent_space_group|parent_propagation_vector)[._][^"\n]*)"',
                joined,
            )
        }
    by_name = defaultdict(set)
    for key, row in nodes.items():
        by_name[row['name']].add(key)

    @cache
    def eligible(child):
        return bool(
            not terminal(child)
            and (
                LEXICAL_HELPER.search(nodes[child]['name'])
                or FIELD_ACCESS.search(nodes[child]['clean'])
                or PRIMITIVE.search(nodes[child]['clean'])
                or LOCAL_DECODE.search(nodes[child]['body'])
                or (
                    re.search(
                        r'(?:\b(?:auto|EdiBlock|CifNames|EdiLoop|Block|Loop)\b|std::(?:string|string_view))',
                        nodes[child]['signature'],
                    )
                )
            )
        )

    edges = {}
    roots = {
        key
        for key, row in nodes.items()
        if (
            re.search(
                r'"_?(?:edi_)?(?:atom_site_moment|magnetic_form_factor|space_group_magn|parent_space_group|parent_propagation_vector)[._]',
                re.sub(r'"\s*"', '', row['body']),
            )
            or any(
                re.search(r'\b' + re.escape(tag) + r'\b', row['clean'])
                for tag in tags[key.rsplit(':', 2)[0]]
            )
        )
        and ACCESS.search(row['clean'])
        and (
            re.search(r'\b(?:EdiBlock|CifNames|EdiLoop|Block|Loop)\b', row['signature'])
            or any(
                re.search(
                    r'\b'
                    + re.escape(param)
                    + r'\s*\)*\s*(?:\.|->)\s*(?:get|require|scalar|loop|loop_with|column)\s*\(',
                    row['clean'],
                )
                for param in re.findall(r'\b(\w+)\s*[,)]', row['signature'])
            )
        )
    }
    # Generic row helpers have no magnetic tag literal and are reached through their callers.
    model_readers = {
        key
        for key, row in nodes.items()
        if re.search(r'\b(?:Structure|ParentSpaceGroup|MagneticDescription)\b', row['signature'])
        and FIELD_ACCESS.search(row['clean'])
        and not re.search(r'^(?:write_|save_|encode_|emit_)|(?:_document|_text)$', row['name'])
    }
    pending = list(roots | model_readers)
    reached = set(pending)
    while pending:
        key = pending.pop()
        row = nodes[key]
        calls = CALL.findall(row['clean']) + re.findall(r'=\s*&?\s*(\w+)\s*;', row['clean'])
        edges[key] = set()
        for name in calls:
            candidates = by_name[name]
            local = {
                child for child in candidates if child.rsplit(':', 2)[0] == key.rsplit(':', 2)[0]
            }
            edges[key].update(child for child in (local or candidates) if eligible(child))
        for child in edges[key] - reached:
            reached.add(child)
            pending.append(child)
    return nodes, edges, roots, reached


def source_tree(root, engine_root=None):
    result = {}
    for home in ('src', 'core', 'include'):
        for path in sorted((root / home).rglob('*')):
            if path.suffix in {'.cpp', '.hpp', '.h'}:
                result[path.relative_to(root).as_posix()] = path.read_text()
    if (root / 'core/include/edi/model.hpp').exists():
        engine_root = root / 'build/crysta-src' if engine_root is None else engine_root
        if not (engine_root / 'src/core/magnetic.cpp').is_file():
            message = (
                'The edi census requires the paired SDK source bundle, including magnetic.cpp'
            )
            raise ValueError(message)
        for path, text in source_tree(engine_root).items():
            result['engine/' + path] = text
    return result


def value_paths(nodes, edges, reached):
    """Conservatively trace field-bearing statements and their string handoffs.

    Whole model functions also handle nuclear fields. Their unrelated marker
    decisions are not magnetic decoders. The field/consumer inventory remains
    complete; this narrows admission diagnostics to magnetic value paths.
    """
    incoming = defaultdict(set)
    selected = {}
    changed = True
    while changed:
        changed = False
        for key in reached:
            row = nodes[key]
            names = set(incoming[key])
            pieces = list(re.finditer(r'[^;{}]+', row['clean']))
            active = []
            for _ in range(len(pieces) + 1):
                previous = set(names)
                active = []
                for piece in pieces:
                    clean = piece[0]
                    raw = row['body'][piece.start() : piece.end()]
                    if (
                        FIELD_ACCESS.search(clean)
                        or TAG.search(raw)
                        or re.search(
                            r'"_?(?:edi_)?(?:atom_site_moment|magnetic_form_factor|space_group_magn|parent_space_group|parent_propagation_vector)[._]',
                            raw,
                        )
                        or any(re.search(r'\b' + re.escape(name) + r'\b', clean) for name in names)
                    ):
                        active.append(piece)
                        names.update(re.findall(r'\b(\w+)\s*=(?!=)', clean))
                if names == previous:
                    break
            for piece in pieces:
                alias = re.search(
                    r'\b(\w+)\s*=\s*std::(?:stod|stof|strtod|atof|atoi|stoi)\b', piece[0]
                )
                if (
                    alias
                    and any(re.search(r'\b' + alias[1] + r'\s*\(', part[0]) for part in active)
                    and piece not in active
                ):
                    active.append(piece)
            selected[key] = active
            calls = {call for piece in active for call in CALL.findall(piece[0])}
            for child in edges.get(key, ()):
                if nodes[child]['name'] not in calls:
                    continue
                params = set(re.findall(r'\b(\w+)\s*(?:,|\))', nodes[child]['signature']))
                if not params <= incoming[child]:
                    incoming[child].update(params)
                    changed = True
    return selected


def legacy_followups(nodes, paths):
    """Regression pins: only unchanged pre-task bodies and call instances are owed.

    Decision 7cadf1c72 scopes the review-20 census; it does not permit another
    caller, a copied helper or a change inside one of the four old helpers.
    """
    pins = json.loads(Path(__file__).with_name('token-followups.json').read_text())
    definitions = defaultdict(list)
    for key in nodes:
        site = key.rsplit(':', 1)[0].removeprefix('engine/')
        if site in pins['bodies']:
            definitions[site].append(key)
    kept = set()
    for site, keys in definitions.items():
        if len(keys) == 1:
            key = keys[0]
            digest = hashlib.sha256(nodes[key]['body'].encode()).hexdigest()
            if digest == pins['bodies'][site]:
                kept.add(key)
    names = {site.rsplit(':', 1)[1] for site in pins['bodies']}
    calls = Counter()
    for key, pieces in paths.items():
        row = nodes[key]
        owner = key.rsplit(':', 1)[0].removeprefix('engine/')
        owner += ':' + ' '.join(row['signature'].split())
        for call in CALL.finditer(row['clean']):
            if call[1] not in names or not any(
                piece.start() <= call.start() < piece.end() for piece in pieces
            ):
                continue
            opening = row['clean'].find('(', call.start())
            end = matching(row['clean'], opening, '(', ')')
            text = ' '.join(row['body'][call.start() : end + 1].split())
            calls[owner + '\n' + text] += 1
    errors = [
        owner + ': new magnetic call instance reaches a known legacy follow-up'
        for owner in calls - Counter(pins['calls'])
    ]
    return kept, errors


def violations(sources, graph=None):  # noqa: PLR0914, PLR0912 — source graph and admission witnesses
    nodes, edges, roots, reached = census(sources) if graph is None else graph
    errors = []
    for key in sorted(roots):
        todo, seen, decoded = [key], set(), False
        while todo:
            current = todo.pop()
            if current in seen:
                continue
            seen.add(current)
            row = nodes[current]
            if re.search(r'\bkept_token_value\s*\(', row['clean']):
                decoded = True
            todo.extend(edges[current] - seen)
        if not decoded:
            errors.append(key + ': magnetic value path does not reach kept_token_value')
    paths = value_paths(nodes, edges, reached)
    legacy, new_calls = legacy_followups(nodes, paths)
    errors.extend(new_calls)
    for key in sorted(reached):
        row = nodes[key]
        active_body = '\n'.join(row['body'][piece.start() : piece.end()] for piece in paths[key])
        active_clean = '\n'.join(piece[0] for piece in paths[key])
        # ADR-0108 section 12 explicitly names stored_token as the stored-cell
        # adapter of the one decoder. A same-named helper elsewhere is not that
        # provider; roots must still reach its kept_token_value call above.
        decoder_site = key.rsplit(':', 1)[0].removeprefix('engine/')
        shared_decoder = decoder_site in {
            'src/core/kept_iso.cpp:kept_token_value',
            'src/core/kept_iso.cpp:stored_token',
        }
        if not shared_decoder and key not in legacy and LOCAL_DECODE.search(active_body):
            errors.append(key + ': local marker/delimiter decision outside the shared decoder')
        if NUMERIC_ALIAS.search(active_clean):
            errors.append(key + ': aliased numeric primitive bypasses the shared strict parser')
        for numeric in PRIMITIVE.finditer(row['clean']):
            if not any(piece.start() <= numeric.start() < piece.end() for piece in paths[key]):
                continue
            opening = row['clean'].find('(', numeric.start())
            end = matching(row['clean'], opening, '(', ')')
            args = row['clean'][opening + 1 : end]
            tail = row['clean'][end:]
            # This one operand is an internal fit-label array index, not a
            # magnetic CIF value. Keep the consumer and all its other numeric
            # expressions in scope; a new magnetic operand here still fails.
            metadata_index = (
                decoder_site == 'core/src/parameter_paths.cpp:resolve_instrument_label'
                and 'stoul' in numeric[0]
                and re.sub(r'\s+', '', args) == 'label.substr(11,label.size()-12)'
                and 'label.rfind("background[", 0)' in row['body']
                and "label.back() == ']'" in row['body']
            )
            if (
                metadata_index
                and not TAG.search(re.sub(r'"\s*"', '', row['body']))
                and not re.search(r'\b(?:get|require|scalar|loop|column)\s*\(', row['clean'])
                and not re.search(
                    r'\b(?:EdiBlock|CifNames|EdiLoop|Block|Loop)\b', row['signature']
                )
            ):
                continue
            # A primitive is admitted only with an end position checked against the whole
            # string and a finite-value check. Delegation is found by the call graph.
            endpoint = re.search(r'&\s*(\w+)\s*$', args)
            if 'from_chars' in numeric[0]:
                binding = re.search(
                    r'\[\s*(\w+)\s*,[^]]*\]\s*=\s*$', row['clean'][: numeric.start()]
                )
                endpoint = binding
            whole = endpoint and re.search(
                re.escape(endpoint[1]) + r'\b[^;{}]*(?:size|length|end|strlen)\s*\(', tail
            )
            finite = 'isfinite' in row['clean']
            target = args.rsplit(',', 1)[-1].strip()
            integer = any(name in numeric[0] for name in ('stoi', 'stol', 'atoi')) or (
                'from_chars' in numeric[0]
                and re.search(
                    r'\b(?:int|long(?:\s+long)?|std::u?int\d+_t)\s+' + re.escape(target) + r'\b',
                    row['clean'],
                )
            )
            if (
                key.rsplit(':', 1)[0].removeprefix('engine/')
                == 'src/core/cif_import.cpp:magnetic_parent'
            ):
                # BNS is family.serial, not an integer token. Both complete BNS
                # admission and the separate parent integer are behaviour-gated.
                # A strict parser may consume each numeric atom up to its separator.
                continue
            if row['name'] == 'read_operator' and 'strtod' in numeric[0]:
                # This is the structured xyz grammar: its cursor consumes the whole expression.
                # Behaviour witnesses exercise junk after every whole operator, not numeric atoms.
                continue
            if not whole or (not finite and not integer):
                errors.append(key + ': numeric conversion lacks whole-token/finite admission')
    return errors


# This list names stored magnetic fields, independently of reader/helper names.
# All qualified and unqualified accesses count, including Structure's own members.
FIELD_TAGS = {
    'symmform': ('_atom_site_moment.symmform',),
    'atom_site_moment': tuple('_atom_site_moment.crystalaxis_' + a for a in 'xyz'),
    'propagation_vectors': ('_parent_propagation_vector.kxkykz',),
    'child_transform_pp_abc': ('_parent_space_group.child_transform_Pp_abc',),
    'transform_pp_abc': ('_parent_space_group.transform_Pp_abc',),
    'magnetic_operations': ('_space_group_symop_magn_operation.xyz',),
    'magnetic_centerings': ('_space_group_symop_magn_centering.xyz',),
    'magnetic_transforms': (
        '_space_group_magn_transforms.Pp_abc',
        '_space_group_magn_transforms.source',
    ),
    'j2_coefficient': ('_magnetic_form_factor.j2_coefficient',),
    'j4_coefficient': ('_magnetic_form_factor.j4_coefficient',),
    'j6_coefficient': ('_magnetic_form_factor.j6_coefficient',),
    'ion': ('_magnetic_form_factor.ion',),
    'approximation': ('_magnetic_form_factor.approximation',),
}
for _member, _tag in {
    'number_bns': '_space_group_magn.number_BNS',
    'name_bns': '_space_group_magn.name_BNS',
    'name_uni': '_space_group_magn.name_UNI',
    'number_og': '_space_group_magn.number_OG',
    'name_og': '_space_group_magn.name_OG',
    'point_group_name_uni': '_space_group_magn.point_group_name_UNI',
    'point_group_number_litvin': '_space_group_magn.point_group_number_Litvin',
    'name_h_m_alt': '_parent_space_group.name_H-M_alt',
    'it_number': '_parent_space_group.IT_number',
    'reference_setting': '_parent_space_group.reference_setting',
}.items():
    FIELD_TAGS[_member] = (_tag,)
FIELD_ACCESS = re.compile(r'\b(?:' + '|'.join(FIELD_TAGS) + r')\b')
TAG = re.compile(
    r'"(_(?:edi_)?(?:atom_site_moment|magnetic_form_factor|space_group_magn(?:_transforms)?'
    r'|space_group_symop_magn_(?:operation|centering)|parent_space_group'
    r'|parent_propagation_vector)\.[A-Za-z][A-Za-z0-9_-]*)'
)


def field_consumers(sources, nodes=None):  # noqa: PLR0912 — explicit member families and graph closure  # noqa: C901 — explicit lexical cases and consumer obligations
    """Return every discovered field/function obligation, with full member call edges.

    A newly used field in an old function changes this inventory. A new member
    continuation is followed even when its name and signature reveal no parser.
    No function-purpose/name exclusion is used here.
    """
    nodes = functions(sources) if nodes is None else nodes
    by_name = defaultdict(set)
    for key, row in nodes.items():
        by_name[row['name']].add(key)
    edges = {
        key: {child for call in CALL.findall(row['clean']) for child in by_name[call]}
        for key, row in nodes.items()
    }
    obligations = {}
    for key, row in nodes.items():
        fields = set(TAG.findall(re.sub(r'"\s*"', '', row['body'])))
        for field, tags in FIELD_TAGS.items():
            if re.search(r'\b' + field + r'\b', row['clean']):
                fields.update(tags)
        for field, tags in TYPED_SHORT_FIELDS.items():
            if re.search(r'\b' + field + r'\b', row['clean']) and re.search(
                r'\b(?:MagneticTransform|ParentSpaceGroup|magnetic_transforms|parent_space_group)\b',
                row['signature'] + row['clean'],
            ):
                fields.update(tags)
        # Edi's description uses short member names; native moment/radial rows
        # also expose aggregates rather than the serialized component names.
        context = row['signature'] + row['clean']
        if 'MagneticDescription' in context or re.search(r'\.magnetic\b', row['clean']):
            for member, aliases in {
                'operations': ('magnetic_operations',),
                'centerings': ('magnetic_centerings',),
                'transforms': ('magnetic_transforms',),
                'parent': (
                    'child_transform_pp_abc',
                    'transform_pp_abc',
                    'name_h_m_alt',
                    'it_number',
                    'reference_setting',
                ),
                'group': (
                    'number_bns',
                    'name_bns',
                    'name_uni',
                    'number_og',
                    'name_og',
                    'point_group_name_uni',
                    'point_group_number_litvin',
                ),
            }.items():
                if re.search(r'\b' + member + r'\b', row['clean']):
                    fields.update(tag for alias in aliases for tag in FIELD_TAGS[alias])
        if 'AtomSiteMoment' in context and re.search(r'\bmoment\b', row['clean']):
            fields.update(FIELD_TAGS['atom_site_moment'])
        if 'MagneticFormFactor' in context and re.search(r'\bcoefficients\b', row['clean']):
            fields.update('_magnetic_form_factor.j' + str(n) + '_coefficient' for n in (2, 4, 6))
        if not fields:
            continue
        # Follow helpers/member handoffs, but don't pretend unrelated calls carry
        # all fields: explicit witness registration reviews each resulting pair.
        pending, seen = [key], set()
        while pending:
            target = pending.pop()
            if target in seen:
                continue
            seen.add(target)
            if target != key and terminal(target):
                continue
            obligations.setdefault(target, set()).update(fields)
            # Complete graph is retained separately; only lexical/domain helpers
            # continue the token obligation, rather than all numerical kernels.
            pending.extend(
                child
                for child in edges[target] - seen
                if LEXICAL_HELPER.search(nodes[child]['name'])
                or FIELD_ACCESS.search(nodes[child]['clean'])
                or LOCAL_DECODE.search(nodes[child]['body'])
                or PRIMITIVE.search(nodes[child]['clean'])
                or 'complete_atom_site_moment' in nodes[child]['name']
            )
    return nodes, edges, {k: sorted(v) for k, v in sorted(obligations.items())}


def normalized_consumers(nodes, obligations, aliases):
    result = {}
    for key, fields in obligations.items():
        identity = key.rsplit(':', 1)[0] + ':' + ' '.join(nodes[key]['signature'].split())
        result[identity] = sorted({aliases.get(tag, tag) for tag in fields})
    return result


TYPED_SHORT_FIELDS = {
    'pp_abc': ('_space_group_magn_transforms.Pp_abc',),
    'source': ('_space_group_magn_transforms.source',),
    'derived': ('_parent_space_group.derived',),
}
