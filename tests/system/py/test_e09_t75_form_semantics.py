"""Review-12 F1: bounded update selectors and download destinations remain observable."""

from __future__ import annotations

import json
import subprocess

import pytest

from tests.integration.py.test_e09_t75_sdk_consumer import consumer
from tests.system.py.test_e09_t74_ci_crysta_resolution import harness
from tests.system.py.test_e09_t75_sdk_update import update, update_probe


@pytest.mark.parametrize('form', ['projection', 'search-extra', 'slurp', 'page-size'])
def test_f1_updater_selection_and_representation_are_observed(tmp_path, form):
    command = {
        'projection': 'gh pr list --repo enhantica/edi --limit 100 --json number',
        'search-extra': (
            'gh api "search/issues?q=repo:enhantica/edi%20is:pr%20is:open%20head:unmatched"'
        ),
        'slurp': (
            'gh api --paginate --slurp "search/issues?q=repo:enhantica/edi%20is:pr%20is:open"'
        ),
        'page-size': 'gh api "repos/enhantica/edi/pulls?per_page=1&page=2"',
    }[form]
    runs, *_ = update(tmp_path, workflow_override=update_probe(command))
    result = runs[-1]
    if result.returncode:
        assert (tmp_path / 'unsupported-commands.jsonl').exists(), (
            ' F1 unsupported selector must remain recorded'
        )
        return
    value = json.loads(result.stdout)
    if form == 'projection':
        assert all(set(row) == {'number'} for row in value), (
            ' F1 CLI JSON projection must omit fields not requested'
        )
    elif form == 'search-extra':
        assert value['items'] == [], (
            ' F1 extra search qualifier must select or refuse, never disappear'
        )
    elif form == 'slurp':
        assert isinstance(value, list) and isinstance(value[0], dict), (
            ' F1 slurp emits an array of page objects'
        )
    else:
        assert value == [], ' F1 per_page and page must select the corresponding slice'


def test_f1_download_does_not_invent_create_dirs(tmp_path):
    command = (
        'curl https://fixture.invalid/crysta-sdk-'
        + 'a7' * 20
        + '-linux-64.tar.gz --output "$DOWNLOAD_FIXTURE/nonexistent/asset"'
    )
    result, _ = consumer(tmp_path, download=True, platform='linux-64', command_override=command)
    assert result.returncode != 0, ' F1 a missing output parent must fail without --create-dirs'
    assert not (tmp_path / 'nonexistent').exists(), (
        ' F1 download transport cannot create unrequested parents'
    )


def test_f1_inherited_grant_reader_cannot_swallow_transport_refusal(tmp_path):

    build = harness(tmp_path)
    script = build.edi / 'tools/ci/fixture-probe.sh'
    script.write_text(
        'curl --unknown-format https://api.github.com/installation/repositories || true\n'
    )
    with pytest.raises(AssertionError, match='unsupported command form'):
        build.run('fixture-probe.sh')


def test_f1_inherited_grant_output_destination_is_observed(tmp_path):
    build = harness(tmp_path)
    control = subprocess.run(
        [
            str(tmp_path / 'bin/curl'),
            '-fsS',
            '-H',
            'Authorization: Bearer fixture-token-not-a-secret',
            '-H',
            'Accept: application/vnd.github+json',
            'https://api.github.com/installation/repositories',
        ],
        env=build.env,
        capture_output=True,
        text=True,
        check=False,
        timeout=2,
    )
    assert control.returncode == 0, ' F1 actual grant-reader form must admit'
    assert json.loads(control.stdout)['repositories'] == [{'full_name': 'enhantica/crysta'}], (
        ' F1 actual grant-reader control retains the independently planted grant'
    )
    output = tmp_path / 'grants.json'
    result = subprocess.run(
        [
            str(tmp_path / 'bin/curl'),
            '--output',
            str(output),
            '-H',
            'Authorization: Bearer fixture-token-not-a-secret',
            'https://api.github.com/installation/repositories',
        ],
        env=build.env,
        capture_output=True,
        text=True,
        check=False,
        timeout=2,
    )
    assert result.returncode == 64, ' F1 undeclared grant output form must refuse'
    assert (tmp_path / 'unsupported-commands.jsonl').exists(), (
        ' F1 narrowed grant output route must persist refusal'
    )
    assert not output.exists(), ' F1 refusal must precede output effects'
