"""Interpreter-free product sources are part of the expression contract."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
INTERPRETER = re.compile(
    r'(?<![.\w])(?:eval|exec)\s*\(|\b(?:asteval|PyRun_[A-Za-z_]+|PyEval_[A-Za-z_]+|QJSEngine)\b'
)


def test_product_constraint_code_cannot_delegate_to_an_interpreter():
    hits = []
    for directory in ('src', 'include', 'core', 'lib'):
        for path in (ROOT / directory).rglob('*'):
            if path.suffix not in {'.py', '.cpp', '.hpp', '.h', '.cc'}:
                continue
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if line.lstrip().startswith(('# ', '//', '*')):
                    continue
                if INTERPRETER.search(line):
                    hits.append(f'{path.relative_to(ROOT)}:{number}')
    assert not hits, (
        'product constraints must parse typed trees without an interpreter: ' + ', '.join(hits)
    )


def test_interpreter_symbol_detector_reaches_each_escape():
    for planted in (
        'eval(text)',
        'exec(text)',
        'asteval.Interpreter()',
        'PyRun_String(text)',
        'PyEval_EvalCode(code)',
        'QJSEngine engine;',
    ):
        assert INTERPRETER.search(planted), (
            'each interpreter escape must be reached by the source gate'
        )
    assert not INTERPRETER.search('context.evaluate(tree)'), (
        'ordinary typed-tree evaluation must remain admissible'
    )
