"""R1 F1: preserve loader-legal minimizer values and presence.

Oracle: owner decision 2026-09-26; literal input values are independent of
production serializers. Equality is decoded UTF-8 value equality: changing the
CIF quoting delimiter is permitted, dropping or normalizing value bytes is not.
"""

import re
import shutil
from pathlib import Path

import edi as engine
import pytest

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / 'build/crysta-src/tests/fitting'
# Explicit pairs avoid asking the writer under test to manufacture its own inputs.
VALUES = [
    pytest.param(None, None, id='absent'),
    pytest.param('crysta', 'crysta', id='default'),
    pytest.param('""', '', id='double-quoted-empty'),
    pytest.param("''", '', id='single-quoted-empty'),
    pytest.param('\'future "A"\'', 'future "A"', id='embedded-double-quote'),
    pytest.param('"future \'A\'"', "future 'A'", id='embedded-single-quote'),
    pytest.param('" \t "', ' \t ', id='whitespace-only'),
    pytest.param('"  future\tengine  "', '  future\tengine  ', id='padded-whitespace'),
    pytest.param('"minimiseur-é ∆ 晶体"', 'minimiseur-é ∆ 晶体', id='unicode'),
    pytest.param('"?"', '?', id='literal-question'),
    pytest.param('"."', '.', id='literal-dot'),
    pytest.param('"#future"', '#future', id='comment-prefix'),
    pytest.param('"future\\engine"', 'future\\engine', id='literal-backslash'),
    pytest.param("'future \"A\" and O'Brien'", 'future "A" and O\'Brien', id='both-quotes'),
    pytest.param('\n;future "A" and \'B\'\n;', 'future "A" and \'B\'', id='text-field'),
    pytest.param('\n;future\nengine\n;', 'future\nengine', id='multiline'),
]


def staged(tmp_path, spelling):
    target = tmp_path / 'input'
    shutil.copytree(CORPUS / 'cosio-d20-s1/project', target)
    analysis = target / 'analysis/analysis.edi'
    source = re.sub(r'(?m)^_minimizer\.type[^\n]*\n?', '', analysis.read_text())
    if spelling is not None:
        source += f'\n_minimizer.type {spelling}\n'
    analysis.write_text(source, encoding='utf-8')
    return target


def saved_value(path):
    # Independent, deliberately small CIF scalar decoder. No shell escaping:
    # backslashes and quotes internal to a CIF token are literal value bytes.
    text = path.read_text(encoding='utf-8')
    matches = list(re.finditer(r'(?m)^_minimizer\.type(?=\s|$)', text))
    assert len(matches) <= 1, ' save must not duplicate the minimizer declaration'
    if not matches:
        return None
    tail = text[matches[0].end() :].lstrip()
    assert tail, ' present minimizer must have a serialized value'
    if tail[0] == ';':
        end = tail.find('\n;', 1)
        assert end >= 0, ' minimizer text field must have a closing delimiter'
        return tail[1:end]
    if tail[0] in '"\'':
        delimiter = tail[0]
        for index in range(1, len(tail)):
            if tail[index] == delimiter and (index + 1 == len(tail) or tail[index + 1].isspace()):
                return tail[1:index]
        pytest.fail(' saved minimizer must have a closing quote')
    return tail.split()[0]


@pytest.mark.parametrize(('spelling', 'expected'), VALUES)
def test_loader_legal_type_survives_repeated_save(tmp_path, capfd, spelling, expected):
    source = staged(tmp_path, spelling)
    for index in range(2):
        capfd.readouterr()
        project = engine.Project.load(source)
        output = capfd.readouterr()
        diagnostics = output.out + output.err
        occurrences = len(re.findall(r'(?i)unsupported _minimizer\.type', diagnostics))
        assert occurrences == (0 if expected in {None, 'crysta'} else 1), (
            ' each edi load must warn exactly once per unsupported minimizer'
        )
        if expected is not None and not expected:
            assert any(
                marker in diagnostics for marker in ('""', "''", '<empty>', 'empty value')
            ), ' warning must identify an explicitly empty minimizer value'
        elif expected not in {None, 'crysta'}:
            assert expected in diagnostics, ' warning must name the unmodified value'
        saved = tmp_path / f'saved-{index}'
        project.save_as(saved)
        output = capfd.readouterr()
        assert not re.search(r'(?i)unsupported _minimizer\.type', output.out + output.err), (
            ' delegated save must not duplicate the unsupported-minimizer load warning'
        )
        actual = saved_value(saved / 'analysis/analysis.edi')
        assert (actual is None) == (expected is None), (
            ' minimizer presence must survive independently of string emptiness'
        )
        if expected is not None:
            assert actual.encode('utf-8') == expected.encode('utf-8'), (
                ' every loader-legal minimizer value must save without byte loss'
            )
        source = saved
