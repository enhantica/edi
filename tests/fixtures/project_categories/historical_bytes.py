"""Permit category movement only when it recovers an immutable prior file hash.

Unit payloads (including loop keys, row order, comments and multiline values)
are never normalized. Layout candidates come from frozen pre-order documents.
This is a byte-regression adapter, not the dictionary-order correctness oracle.
"""

import functools
import hashlib
import itertools
import json
from pathlib import Path


def units(data):
    lines = data.splitlines(keepends=True)
    result, head, blank, body = [], [], [], []
    key = None
    quoted = False
    loop_keys = False

    def finish():
        if key is not None:
            while body and not body[-1].strip():
                blank.insert(0, body.pop())
            result.append((key, b''.join(body)))

    prefixes = []
    for line in lines:
        starts = not quoted and (
            line.strip() == b'loop_'
            or (line.startswith(b'_') and not (loop_keys and len(line.split()) == 1))
        )
        if starts:
            finish()
            prefixes.append(b''.join(blank))
            blank.clear()
            body = []
            key = b'loop' if line.strip() == b'loop_' else line.split()[0]
            loop_keys = key == b'loop'
        elif key == b'loop' and loop_keys and line.startswith(b'_'):
            key = b'loop:' + line.split(b'.', 1)[0]
        elif loop_keys and line.strip() and not line.startswith(b'_'):
            loop_keys = False
        if key is None:
            head.append(line)
        else:
            body.append(line)
        if line.startswith(b';'):
            quoted = not quoted
    finish()
    return b''.join(head), result, prefixes, b''.join(blank)


def layout(data):
    head, entries, prefixes, tail = units(data)
    return {
        'head': head.hex(),
        'entries': [
            [key.decode(), prefix.hex()]
            for (key, _), prefix in zip(entries, prefixes, strict=True)
        ],
        'tail': tail.hex(),
    }


def require_saved_spacing(data):
    _, entries, separators, _ = units(data)
    for index in range(1, len(entries)):
        previous, current = entries[index - 1][0], entries[index][0]
        same = (
            not previous.startswith(b'loop:')
            and not current.startswith(b'loop:')
            and previous.split(b'.', 1)[0] == current.split(b'.', 1)[0]
        )
        assert separators[index] == (b'' if same else b'\n'), (
            'Owner Text record item 4: no blank inside scalar categories; one blank between '
            'categories and around loops in the actual saved file'
        )


def check_project_spacing(directory):
    for path in Path(directory).rglob('*.edi'):
        require_saved_spacing(path.read_bytes())


@functools.cache
def layouts():
    return json.loads(Path(__file__).with_name('historical-layouts.json').read_text())['layouts']


def same_category_order(keys, old_keys):
    def category(key):
        return key.removeprefix('loop:').split('.', 1)[0]

    shared = set(keys) & set(old_keys)
    return all(
        [key for key in keys if key in shared and category(key) == group]
        == [key for key in old_keys if key in shared and category(key) == group]
        for group in {category(key) for key in shared}
    )


def candidates(data, template=None):
    head, entries, _, _ = units(data)
    keys = [key.decode() for key, _ in entries]
    if not keys:
        return  # Opaque documents have no movable category units.
    if len(keys) != len(set(keys)):
        return  # Ambiguous repeated units require a separate explicit oracle.
    payload = {key.decode(): value for key, value in entries}
    for old in [layout(template), *layouts()] if template is not None else layouts():
        old_keys = [key for key, _ in old['entries']]
        missing = [key for key in keys if key not in old_keys]
        # These explicitly declared later blocks postdate the frozen archive.
        # Try placement only; acceptance still requires the immutable whole-file hash.
        late = {
            '_calculator.type',
            '_background_estimate.mode',
            '_background_estimate.method',
            'loop:_refln',
        }
        if not set(missing).issubset(late):
            continue
        if not same_category_order(keys, old_keys):
            continue  # The decision moves categories, never the items inside one.
        # Preserve every nonempty preamble line exactly, including its spacing.
        old_head = bytes.fromhex(old['head']).splitlines(keepends=True)
        actual_head = [line for line in head.splitlines(keepends=True) if line.strip()]
        if len(actual_head) != sum(bool(line.strip()) for line in old_head):
            continue
        values = iter(actual_head)
        old_head = b''.join(next(values) if line.strip() else line for line in old_head)
        kept = [(key, bytes.fromhex(prefix)) for key, prefix in old['entries'] if key in payload]
        variants = [kept]
        if missing:
            variants = []
            for position, prefix in itertools.product(range(len(kept) + 1), (b'', b'\n')):
                inserted = [
                    (key, prefix if index == 0 else b'') for index, key in enumerate(missing)
                ]
                variants.append(kept[:position] + inserted + kept[position:])
        for variant in variants:
            yield (
                old_head
                + b''.join(prefix + payload[key] for key, prefix in variant)
                + bytes.fromhex(old['tail'])
            )


def prior_digest(data, expected, *, template=None, name=None):
    digest = hashlib.sha256(data).hexdigest()
    if digest == expected:
        return digest
    if name is not None and not name.endswith('.edi'):
        return digest
    for before in candidates(data, template):
        if hashlib.sha256(before).hexdigest() == expected:
            return expected
    return digest  # Preserve the caller's original failure and diagnostics.


def prior_bytes(data, expected, *, name):
    """Recover exact reference bytes only across declared category layout changes."""
    digest = hashlib.sha256(expected).hexdigest()
    return expected if prior_digest(data, digest, template=expected, name=name) == digest else data
