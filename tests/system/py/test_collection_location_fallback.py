"""One logical collection tries its ordered locations without external I/O."""

import io
import json
import runpy
import sys
import urllib.error
from pathlib import Path

import edi
import pytest

PRIMARY = 'https://raw.githubusercontent.com/enhantica/edi-data/main'
SECONDARY = 'https://data.easydiffraction.org'
FIXTURE = Path(__file__).resolve().parents[2] / 'fixtures/online_sources/easydiffraction'


@pytest.mark.parametrize('interface', ['python', 'cli'])
@pytest.mark.parametrize('stage', ['index', 'file'])
@pytest.mark.parametrize('outcome', ['primary', 'fallback', 'both-fail', 'missing'])
def test_collection_locations_are_one_ordered_source(
    monkeypatch, tmp_path, capsys, interface, stage, outcome
):
    requests = []
    path = 'index.json' if stage == 'index' else 'structures/lbco.cif'

    def injected_urlopen(url, *_args, **_kwargs):
        address = getattr(url, 'full_url', str(url))
        requests.append(address)
        location = next(
            (base for base in (PRIMARY, SECONDARY) if address.startswith(base + '/')), None
        )
        assert location is not None, 'Every collection request stays within the injected locations'
        relative = address[len(location) + 1 :]
        fails = relative == path and (
            outcome == 'both-fail' or (location == PRIMARY and outcome in {'fallback', 'missing'})
        )
        if fails:
            status = 404 if outcome == 'missing' else 503
            raise urllib.error.HTTPError(address, status, 'injected unavailable', {}, None)
        return io.BytesIO((FIXTURE / relative).read_bytes())

    monkeypatch.delenv('EDI_COLLECTION', raising=False)
    monkeypatch.setattr('urllib.request.urlopen', injected_urlopen)
    error = None
    if interface == 'python':
        try:
            collection = edi.load_collection()
            result = (
                collection.fetch('lbco', tmp_path) if stage == 'file' else collection.find('lbco')
            )
        except (OSError, ValueError, RuntimeError) as failure:
            error = failure
        else:
            if stage == 'file':
                assert result.read_bytes() == (FIXTURE / path).read_bytes(), (
                    'A fallback fetch preserves the independent CIF bytes exactly'
                )
            else:
                assert result['id'] == 'lbco', (
                    'A fallback index retains the independently committed entry identity'
                )
    else:
        action = (
            ['fetch', 'lbco', '--into', str(tmp_path)] if stage == 'file' else ['find', 'lbco']
        )
        monkeypatch.setattr(sys, 'argv', ['edi', 'collection', *action])
        try:
            runpy.run_module('edi', run_name='__main__')
        except SystemExit as failure:
            if failure.code:
                error = failure
        except (OSError, ValueError, RuntimeError) as failure:
            error = failure
        output = capsys.readouterr()
        if error is None:
            if stage == 'file':
                assert (tmp_path / 'lbco.cif').read_bytes() == (FIXTURE / path).read_bytes(), (
                    'CLI fallback writes the same independently committed CIF bytes'
                )
            else:
                assert json.loads(output.out)['id'] == 'lbco', (
                    'CLI fallback publishes the same independently committed entry identity'
                )
    expected = [PRIMARY + '/' + path] + (
        [SECONDARY + '/' + path] if outcome in {'fallback', 'both-fail'} else []
    )
    observed = [url for url in requests if url.endswith('/' + path)]
    assert observed == expected, (
        'One logical source tries primary then mirror only for an unavailable location'
    )
    assert (error is not None) == (outcome in {'both-fail', 'missing'}), (
        'An available fallback succeeds; only exhausted locations or a missing file refuse'
    )
