"""Adapt only comments in the frozen adapter measurement; retain code and line spans."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'tests/unit/cpp/e09_t55_adapter_classification_source.txt'
MEASUREMENT = ROOT / 'tests/unit/cpp/e09_t55_adapter_classification.json'
RECEIPT = Path(__file__).with_name('adapter-comment-metadata.json')
ORIGINAL_SHA256 = '3bbd306d42fc286647076478b98fadce37724386ed06916ffe62e3d5b1fe5b33'
REPLACEMENTS = {
    63: (
        '// default 1.0 Å — the silent-wrong-answer path an engine change '
        'would otherwise open (the'
    ),
    64: (
        '// engine uses every cell length). This is exactly the tie crysta itself applies on its'
    ),
    129: "// the 4-wide instrument itself; edi's model also CARRIES the reciprocal and",
    178: '// Every label leaf equals the edi field leaf. Presence-tracked CW fields keep',
    180: '// abscor1 precedent — never a write to a value the model never had.',
    499: '// The four typed axes and all seven CW fields are part of the',
    914: (
        '// The CW conversion: the captured engine has no named CW builder, '
        'so the adapter uses the'
    ),
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    before = SOURCE.read_bytes()
    if digest(before) != ORIGINAL_SHA256:
        if RECEIPT.is_file() and digest(before) == json.loads(RECEIPT.read_text())['after_sha256']:
            return
        raise ValueError('comment adaptation requires the original retained measurement')
    lines = before.decode().splitlines(keepends=True)
    changed = []
    for index, line in enumerate(lines):
        if index + 1 in REPLACEMENTS:
            indentation = line[: len(line) - len(line.lstrip())]
            lines[index] = indentation + REPLACEMENTS[index + 1] + '\n'
            changed.append(index + 1)
    if len(changed) != len(REPLACEMENTS):
        raise ValueError('every declared comment adaptation must reach exactly one source line')
    after = ''.join(lines).encode()
    before_lines = before.decode().splitlines()
    after_lines = after.decode().splitlines()
    if len(before_lines) != len(after_lines):
        raise ValueError('comment adaptation cannot move classified function spans')
    for old, new in zip(before_lines, after_lines, strict=True):
        if old != new and not (old.lstrip().startswith('//') and new.lstrip().startswith('//')):
            raise ValueError('comment adaptation cannot change executable adapter text')
    document = json.loads(MEASUREMENT.read_text())
    if document['classification_source']['sha256'] != ORIGINAL_SHA256:
        raise ValueError('measurement must still identify the original source bytes')
    document['classification_source']['sha256'] = digest(after)
    SOURCE.write_bytes(after)
    MEASUREMENT.write_text(json.dumps(document, indent=2) + '\n')
    RECEIPT.write_text(
        json.dumps(
            {
                'before_sha256': ORIGINAL_SHA256,
                'after_sha256': digest(after),
                'changed_comment_lines': changed,
                'line_count': len(lines),
                'invariant': (
                    'Only whole-line comments change; every executable line, function span, '
                    'classification and summary remains unchanged.'
                ),
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
