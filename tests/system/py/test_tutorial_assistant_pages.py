"""Owner e8c3d7088 / 926b5e4dd / 65471c30f: assistant prompts and rerun evidence."""

import contextlib
import hashlib
import json
import re
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import pytest
from bs4 import BeautifulSoup

from tests.fixtures.tutorial_cases.assistant_hub import follow_page, local_page
from tests.fixtures.tutorial_cases.assistant_versions import (
    PREVIEW_REF,
    PROMPT_BASE,
    USER_BASE,
    assistant_version_sites,  # noqa: F401 - shared public builder
)
from tests.fixtures.tutorial_cases.contract import ROOT
from tests.fixtures.tutorial_cases.screenshots import assert_webp_asset

FIT_WORD_PARTS = ('re', 'fin')
URL = re.compile(r'https?://[^\s<>\])`"\']+')


def prompt(page):
    soup = BeautifulSoup(page.read_text(), 'html.parser')
    candidates = {
        node.get_text().strip()
        for node in soup.select(
            'main pre code, main blockquote, main textarea, [data-assistant-prompt]'
        )
        if re.search(r'\bLa\b', node.get_text())
        and re.search(r'\bBa\b', node.get_text())
        and 'fit' in node.get_text().casefold()
    }
    assert len(candidates) == 1, (
        'Gate 3/5: an assistant tutorial supplies one copyable LBCO constraint prompt'
    )
    return candidates.pop()


def normalized_prompt(text, interface):
    artifact = r'Jupyter notebook' if interface == 'python' else r'EasyDiffraction project'
    assert len(re.findall(artifact, text, re.IGNORECASE)) >= 1, (
        'Gate 3/5: each prompt declares the artifact it asks to create'
    )
    text = re.sub(r'\b(?:a|an)\s+' + artifact, '<TARGET>', text, count=1, flags=re.IGNORECASE)
    text = re.sub(
        r'ready (?:to run|for `?edi fit`?)', '<READY>', text, count=1, flags=re.IGNORECASE
    )
    links = [link for link in URL.findall(text) if '/' + interface + '/tutorials' in link]
    assert links, 'Gate 3/5: the prompt links its own tutorials collection'
    for link in links:
        text = text.replace(
            link, link.replace('/' + interface + '/tutorials', '/<INTERFACE>/tutorials')
        )
    return ' '.join(text.split())


def fetch(address, root):
    if address.startswith((PROMPT_BASE, USER_BASE)):
        return local_page(address, root / 'index.html', root).read_bytes()
    parsed = urlparse(address)
    if parsed.scheme == 'file':
        path = Path(unquote(parsed.path))
        assert path.resolve().is_relative_to(root.resolve()) and path.is_file(), (
            'Gate 3/5: a local tutorial download resolves inside the actual built site'
        )
        return path.read_bytes()
    assert parsed.scheme == 'https', 'Gate 3/5: prompt links and remote downloads use HTTPS'
    with urllib.request.urlopen(address, timeout=20) as response:  # noqa: S310 - HTTPS checked above
        assert response.status == 200, (
            'Gate 3/5: each literal published prompt/download address resolves'
        )
        return response.read()


@pytest.fixture(scope='module')
def assistant_pages(assistant_version_sites):  # noqa: F811 - shared public builder
    built_site = assistant_version_sites['preview']
    pages = {}
    for interface in ['application', 'python', 'cli']:
        choices = []
        for path in (built_site / interface).rglob('*.html'):
            soup = BeautifulSoup(path.read_text(), 'html.parser')
            title = soup.select_one('main h1')
            main = soup.select_one('main')
            if (
                title
                and main
                and 'assistant' in title.get_text().casefold()
                and (
                    re.search(r'LBCO|lbco', main.get_text())
                    or main.select_one('a[href*="pd-neut-cwl_lbco-hrpt"]')
                )
            ):
                choices.append(path)
        tutorial_pages = [path for path in choices if '/tutorials/' in path.as_posix()]
        pages[interface] = tutorial_pages or choices
    return built_site, pages


@pytest.fixture(scope='module')
def resolved_assistant_links(assistant_pages):
    root, pages = assistant_pages
    addresses = set()
    for interface, choices in pages.items():
        if len(choices) != 1:
            continue
        page = choices[0]
        soup = BeautifulSoup(page.read_text(), 'html.parser')
        addresses.update(
            urljoin(page.as_uri(), link['href'])
            for link in soup.select('main a[href]')
            if urlparse(link['href'])
            .path.lower()
            .endswith(('.cif', '.xye', '.xy', '.dat', '.hkl'))
        )
        if interface != 'application':
            # The prompt-specific gate reports malformed prompts independently.
            with contextlib.suppress(AssertionError):
                addresses.update(URL.findall(prompt(page)))

    def resolve(address):
        try:
            content = fetch(address, root)
            return address, {'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
        except (OSError, ValueError, AssertionError) as error:
            return address, {'error': str(error)}

    with ThreadPoolExecutor(max_workers=4) as pool:
        return dict(pool.map(resolve, sorted(addresses)))


@pytest.mark.parametrize('interface', ['application', 'python', 'cli'])
def test_assistant_tutorial_downloads_resolve_and_offer_both_collection_inputs(
    interface, assistant_pages, resolved_assistant_links
):
    _root, pages = assistant_pages
    assert len(pages[interface]) == 1, 'Gate 3/5: each interface has its LBCO assistant tutorial'
    page = pages[interface][0]
    soup = BeautifulSoup(page.read_text(), 'html.parser')
    downloads = {
        urljoin(page.as_uri(), link['href'])
        for link in soup.select('main a[href]')
        if urlparse(link['href']).path.lower().endswith(('.cif', '.xye', '.xy', '.dat', '.hkl'))
    }
    assert len(downloads) == 2, (
        'Gate 3/5: the assistant page offers the structure CIF and HRPT data'
    )
    assert all(resolved_assistant_links[address].get('bytes', 0) > 0 for address in downloads), (
        'Gate 3/5: both literal assistant input downloads resolve: '
        + repr(resolved_assistant_links)
    )


@pytest.mark.parametrize('interface', ['python', 'cli'])
def test_every_literal_link_in_the_assistant_prompt_resolves(
    interface, assistant_pages, resolved_assistant_links
):
    _root, pages = assistant_pages
    assert len(pages[interface]) == 1, (
        'Gate 3/5: the literal prompt has its own published tutorial page'
    )
    text = prompt(pages[interface][0])
    addresses = sorted(set(URL.findall(text)))
    assert len(addresses) >= 2, (
        'Gate 3/5: the literal prompt links the docs and its tutorials collection'
    )
    assert all(resolved_assistant_links[address].get('bytes', 0) > 0 for address in addresses), (
        'Gate 3/5: every literal prompt link resolves: ' + repr(resolved_assistant_links)
    )


def test_the_two_prompts_differ_only_in_target_and_tutorials_link_and_use_fit_free(
    assistant_pages,
):
    _root, pages = assistant_pages
    assert len(pages['python']) == len(pages['cli']) == 1, (
        'Gate 3/5: both user-assistant prompt pages exist'
    )
    prompts = {interface: prompt(pages[interface][0]) for interface in ['python', 'cli']}
    for text in prompts.values():
        words = re.findall(r'[A-Za-z]+', text.casefold())
        assert {'fit', 'free'} <= set(words) and not any(
            word.startswith(''.join(FIT_WORD_PARTS)) for word in words
        ), 'Gate 3/5: prompts use only the fit/free scientific vocabulary'
    assert normalized_prompt(prompts['python'], 'python') == normalized_prompt(
        prompts['cli'], 'cli'
    ), 'Gate 3/5: the same literal prompt changes only its declared artifact and tutorials link'


def test_application_assistant_has_light_and_dark_captures_with_a_commit_record(
    assistant_version_sites,  # noqa: F811 - public builder
):
    root = assistant_version_sites['preview']
    page = follow_page(root / 'application/assistant/index.html', root)
    soup = BeautifulSoup(page.read_text(), 'html.parser')
    images = soup.select('main img[src], main svg image[href]')
    assert images, 'Gate 4: the shared assistant overview shows its actual fitted-LBCO screenshot'
    for image in images:
        address = urlparse(urljoin(page.as_uri(), image.get('src', image.get('href'))))
        if address.scheme != 'file':
            continue
        light = Path(unquote(address.path))
        dark = light.parent / 'dark' / light.name
        if not dark.is_file():
            continue
        assert_webp_asset(light.as_uri(), page, root)
        assert_webp_asset(dark.as_uri(), page, root)
        assert light.read_bytes() != dark.read_bytes(), (
            'Gate 4: light and dark captures are distinct'
        )
        records = [
            folder / 'capture.json' for folder in light.parents if folder.is_relative_to(root)
        ]
        for path in records:
            if path.is_file():
                document = json.loads(path.read_text())
                commit = document.get('edi_build_commit', document.get('commit', ''))
                if (
                    re.fullmatch(r'[0-9a-f]{7,40}', commit)
                    and subprocess.run(
                        ['git', '-C', str(ROOT), 'cat-file', '-e', f'{commit}^{{commit}}'],
                        capture_output=True,
                        check=False,
                    ).returncode
                    == 0
                ):
                    return
    pytest.fail('Gate 4: the light/dark assistant capture has its authoring build commit record')


def assert_preview_trial(row, interface, digest):
    assert row.get('address_mapping') == {PROMPT_BASE: USER_BASE}, (
        'Gate 3/5: the preview trial explicitly maps official prompt links to the preview address'
    )
    assert row.get('site_base') == USER_BASE, (
        'Gate 3/5: the prerelease-preview trial uses the live user site, not contributor docs'
    )
    assert row.get('publication_route') == 'prerelease-preview', (
        'Gate 3/5: first-trial publication failures cannot stand in for a live preview rerun'
    )
    assert row.get('preview_ref') == PREVIEW_REF, (
        'Gate 3/5: the rerun identifies the task branch selected for the prerelease preview'
    )
    assert row.get('prompt_url') == row['site_base'] + interface + '/tutorials/assistant/', (
        'Gate 3/5: the rerun identifies the literal published preview prompt page'
    )
    assert row['prompt_sha256'] == digest, (
        'Gate 3/5: a changed preview prompt needs its own literal trial, not an older success'
    )
    assert row['model'] and re.fullmatch(r'\d{4}-\d{2}-\d{2}', row['date']), (
        'Gate 3/5: the published preview rerun names the actual model and date'
    )
    assert row['status'] in {'passed', 'failed'} and row['findings'], (
        'Gate 3/5: the preview rerun reports its pin comparison or precise execution finding'
    )


@pytest.mark.parametrize('interface', ['python', 'cli'])
def test_each_prompt_has_fresh_committed_authoring_trial_evidence(
    interface,
    assistant_version_sites,  # noqa: F811 - shared public builder
):
    evidence = json.loads(
        (ROOT / 'tests/fixtures/tutorial_cases/assistant_trials.json').read_text()
    )
    summary = 'assistant-prompt-trials'
    assert evidence['source'] and evidence['source']['document'] == summary, (
        'Gate 3/5: export the committed preview rerun summary, preserving first-trial history'
    )
    rows = [
        row
        for row in evidence['records']
        if row['interface'] == interface and row.get('publication_route') == 'prerelease-preview'
    ]
    assert rows, (
        'Gate 3/5: each prompt needs its live prerelease-preview rerun; old 404s do not qualify'
    )
    page = assistant_version_sites['preview'] / interface / 'tutorials/assistant/index.html'
    assert page.is_file(), 'Gate 3/5: the preview build publishes the literal prompt page'
    digest = hashlib.sha256(prompt(page).encode()).hexdigest()
    current = [row for row in rows if row['prompt_sha256'] == digest]
    assert current, 'Gate 3/5: the committed rerun covers the current preview prompt'
    for row in current:
        assert_preview_trial(row, interface, digest)
    soup = BeautifulSoup(page.read_text(), 'html.parser')
    assert any(
        unquote(urlparse(link['href']).path).rstrip('/').endswith('/' + summary)
        for link in soup.select('main a[href]')
    ), 'Gate 3/5: the prompt page cites the published preview rerun summary used by the gate'


def test_all_assistant_interfaces_offer_the_same_two_input_files(
    assistant_pages, resolved_assistant_links
):
    _root, pages = assistant_pages
    hashes = []
    for choices in pages.values():
        assert len(choices) == 1, 'Gate 3/5: all three assistant tutorials offer the shared inputs'
        page = choices[0]
        soup = BeautifulSoup(page.read_text(), 'html.parser')
        addresses = {
            urljoin(page.as_uri(), link['href'])
            for link in soup.select('main a[href]')
            if urlparse(link['href'])
            .path.lower()
            .endswith(('.cif', '.xye', '.xy', '.dat', '.hkl'))
        }
        assert len(addresses) == 2, (
            'Gate 3/5: each assistant tutorial offers precisely two input files'
        )
        hashes.append(
            sorted(resolved_assistant_links[address].get('sha256') for address in addresses)
        )
    assert all(values and None not in values and values == hashes[0] for values in hashes), (
        'Gate 3/5: every assistant interface offers byte-identical LBCO CIF and HRPT data'
    )


@pytest.mark.parametrize('change', ['extra-stage', 'wrong-input', 'changed-constraint'])
def test_prompt_normalization_preserves_all_non_target_instructions(change):
    common = (
        'Create {article} {target}. Fit and free La and Ba equally. '
        'Read https://example.org/{route}/tutorials/ '
        'and https://example.org/{route}/tutorials/cases/lbco/ .'
    )
    python = common.format(article='a', target='Jupyter notebook ready to run', route='python')
    cli = common.format(
        article='an', target='EasyDiffraction project ready for edi fit', route='cli'
    )
    assert normalized_prompt(python, 'python') == normalized_prompt(cli, 'cli'), (
        'Gate 3/5: declared target and tutorials-link differences normalize equally'
    )
    broken = {
        'extra-stage': cli + ' Also fit another stage.',
        'wrong-input': cli.replace('La and Ba', 'Na and Cl'),
        'changed-constraint': cli.replace('equally', 'independently'),
    }[change]
    assert normalized_prompt(python, 'python') != normalized_prompt(broken, 'cli'), (
        'Gate 3/5: input, constraint and stage changes cannot hide behind target normalization'
    )


@pytest.mark.parametrize(
    'change',
    [
        'first-trial-history',
        'wrong-prompt-page',
        'changed-prompt',
        'wrong-preview-ref',
        'wrong-official-map',
    ],
)
def test_preview_trial_evidence_refuses_history_and_other_prompts(change):
    row = {
        'interface': 'python',
        'site_base': USER_BASE,
        'address_mapping': {PROMPT_BASE: USER_BASE},
        'publication_route': 'prerelease-preview',
        'preview_ref': PREVIEW_REF,
        'prompt_url': USER_BASE + 'python/tutorials/assistant/',
        'prompt_sha256': 'current',
        'model': 'authored control',
        'date': '2026-11-09',
        'status': 'failed',
        'findings': ['authored execution control, no scientific claim'],
    }
    assert_preview_trial(row, 'python', 'current')
    if change == 'first-trial-history':
        row.pop('publication_route')
        row.pop('preview_ref')
    elif change == 'wrong-prompt-page':
        row['prompt_url'] = 'https://enhantica.github.io/edi/dev/python/tutorials/assistant/'
    elif change == 'changed-prompt':
        row['prompt_sha256'] = 'old'
    elif change == 'wrong-preview-ref':
        row['preview_ref'] = 'main'
    else:
        row['address_mapping'] = {PROMPT_BASE: 'https://example.invalid/'}
    with pytest.raises(AssertionError, match='Gate 3/5:'):
        assert_preview_trial(row, 'python', 'current')
