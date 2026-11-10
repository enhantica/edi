"""Owner 3d85ed388: official links are independent of a docs build's address."""

import re

import pytest

from tests.fixtures.tutorial_cases.assistant_hub import local_page
from tests.fixtures.tutorial_cases.assistant_versions import (
    PROMPT_BASE,
    assistant_version_sites,  # noqa: F401 - shared public builder
)
from tests.system.py.test_tutorial_assistant_pages import URL, prompt


def assert_official_links(text, interface=None, root=None):
    addresses = set(URL.findall(text))
    addresses.update(re.findall(r'\]\(([^\s)]+)\)', text))
    addresses.update(re.findall(r'\b[a-zA-Z][\w+.-]*://[^\s<>\])`"\']+', text))
    assert addresses, 'Gate 3/5: prompts and llms.txt contain explicit documentation links'
    assert all(address.startswith(PROMPT_BASE) for address in addresses), (
        'Gate 3/5: every prompt and llms.txt link uses https://easydiffraction.org/ always'
    )
    if interface is not None:
        expected = {PROMPT_BASE, PROMPT_BASE + 'llms.txt', PROMPT_BASE + interface + '/tutorials/'}
        assert expected <= addresses, (
            'Gate 3/5: the official prompt links the docs root, assistant '
            'index and tutorials index'
        )
        assert not re.search(r'^\s*the\s+closest\s+one\s*:', text, re.IGNORECASE | re.MULTILINE), (
            'Gate 3/5: a prompt never preselects a worked example with The closest one'
        )
        assert 'closest' in text.casefold() and re.search(
            r'\b(choose|select|pick|find)\b', text, re.IGNORECASE
        ), 'Gate 3/5: the prompt asks the assistant to choose its closest worked example'
    if root is not None:
        for address in addresses:
            local_page(address, root / 'index.html', root)


@pytest.mark.parametrize('version', ['main', 'preview', 'local'])
@pytest.mark.parametrize('interface', ['python', 'cli'])
def test_built_assistant_prompt_links_use_official_base_and_resolve_in_build(
    version,
    interface,
    assistant_version_sites,  # noqa: F811 - shared public builder
):
    root = assistant_version_sites[version]
    page = root / interface / 'tutorials/assistant/index.html'
    assert page.is_file(), 'Gate 3/5: both build versions publish their assistant prompt pages'
    assert_official_links(prompt(page), interface, root)


@pytest.mark.parametrize(
    'change',
    [
        'contributor-base',
        'preview-base',
        'localhost',
        'foreign-base',
        'extra-contributor-link',
        'relative-link',
        'ftp-link',
        'closest-one',
        'no-choice',
    ],
)
def test_official_prompt_observer_refuses_other_bases_and_preselected_examples(change):
    text = ' '.join([PROMPT_BASE, PROMPT_BASE + 'llms.txt', PROMPT_BASE + 'python/tutorials/'])
    text += ' Choose the closest worked example yourself.'
    assert_official_links(text, 'python')
    assert_official_links(
        text.replace(
            'Choose the closest worked example yourself.', 'Pick the closest one yourself.'
        ),
        'python',
    )
    if change in {'contributor-base', 'preview-base', 'localhost', 'foreign-base'}:
        replacement = {
            'contributor-base': 'https://enhantica.github.io/edi/dev/',
            'preview-base': 'https://enhantica.github.io/edi/',
            'localhost': 'http://127.0.0.1:8873/',
            'foreign-base': 'https://example.org/',
        }[change]
        text = text.replace(PROMPT_BASE, replacement)
    elif change == 'extra-contributor-link':
        text += ' https://enhantica.github.io/edi/dev/physics/'
    elif change == 'relative-link':
        text += ' [Physics](physics/)'
    elif change == 'ftp-link':
        text += ' ftp://example.org/input.cif'
    elif change == 'closest-one':
        text += (
            '\nThe closest one: ' + PROMPT_BASE + 'python/tutorials/cases/pd-neut-cwl_lbco-hrpt/'
        )
    else:
        text = text.replace('Choose the closest worked example yourself.', 'Worked examples.')
    with pytest.raises(AssertionError, match='Gate 3/5:'):
        assert_official_links(text, 'python')


@pytest.mark.parametrize('version', ['main', 'preview', 'local'])
def test_built_llms_index_is_utf8_and_every_official_link_resolves(
    version,
    assistant_version_sites,  # noqa: F811 - shared public builder
):
    root = assistant_version_sites[version]
    path = root / 'llms.txt'
    assert path.is_file(), 'Gate 3/5: every docs build publishes llms.txt'
    payload = path.read_bytes()
    text = payload.decode('utf-8', errors='strict')
    assert text.encode('utf-8') == payload and '\ufffd' not in text, (
        'Gate 3/5: llms.txt is valid UTF-8 without substituted replacement characters'
    )
    assert not any(bad in text for bad in ('\u00e2\u201a', '\u00e2\u20ac', '\u00c3\u00a2')), (
        'Gate 3/5: llms.txt preserves Unicode formulas rather than UTF-8 mojibake'
    )
    assert_official_links(text, root=root)


def test_official_mapping_cannot_hide_missing_or_escaping_build_targets(tmp_path):
    (tmp_path / 'index.html').write_text('root')
    (tmp_path / 'llms.txt').write_text('index')
    valid = PROMPT_BASE + 'llms.txt'
    assert_official_links(valid, root=tmp_path)
    for address in [PROMPT_BASE + 'missing/', PROMPT_BASE + '../escape.txt']:
        with pytest.raises(AssertionError, match='Gate 3/4/5:'):
            assert_official_links(address, root=tmp_path)
