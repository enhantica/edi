"""F5: every artifact API route keeps host, resource and selectors distinct."""

import json

import pytest

from tests.integration.py.test_c34_t28_pr_artifact import SHA, acquisition

ROUTES = ['release', 'runs', 'jobs', 'artifacts', 'zip']


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('damage', ['host', 'owner', 'resource', 'representation', 'operation'])
def test_artifact_transport_never_aliases_another_address(tmp_path, route, damage):
    context = acquisition(tmp_path, prepare_only=True)
    api = context['api']
    api.releases['build-' + SHA] = {'tag_name': 'build-' + SHA}
    suffix = {
        'release': '/releases/tags/build-' + SHA,
        'runs': '/actions/runs?head_sha=' + SHA + '&event=pull_request&per_page=100',
        'jobs': '/actions/runs/75090/jobs?filter=all&per_page=100',
        'artifacts': '/actions/runs/75090/artifacts?per_page=100',
        'zip': '/actions/artifacts/2806/zip',
    }[route]
    url = 'https://api.github.com/repos/enhantica/crysta' + suffix
    options = {'accept': 'application/vnd.github+json'}
    if route == 'zip':
        options['out'] = tmp_path / 'control.zip'
    good = api(url, **options)
    if route == 'zip':
        assert options['out'].read_bytes() == api.archives[suffix], (
            ' F5 the admitted route serves its independently held exact archive'
        )
        options['out'] = tmp_path / 'wrong.zip'
    else:
        assert json.loads(good), ' F5 each wrong-address case needs a nonempty legal control'
    if damage == 'host':
        url = url.replace('api.github.com', 'foreign.invalid')
    elif damage == 'owner':
        url = url.replace('enhantica/', 'foreign/')
    elif damage == 'resource':
        url = url.replace(SHA, 'c3' * 20).replace('75090', '74999').replace('2806', '2999')
    elif damage == 'representation':
        options['accept'] = 'text/html'
    else:
        options['absent_ok'] = True
        if route == 'release':
            options['out'] = tmp_path / 'wrong.json'
    try:
        body = api(url, **options)
    except context['module'].RefusedError:
        body = None
    if body is not None:
        assert json.loads(body).get('total_count') == 0, (
            ' F5 another legal head cannot return the selected head records'
        )
    assert not (tmp_path / 'wrong.zip').exists(), (
        ' F5 a wrong request cannot receive the selected artifact bytes'
    )
    if damage != 'resource':
        assert api.refusals, ' F5 unsupported transport operations must remain latched'


@pytest.mark.parametrize('selector', ['event', 'filter'])
def test_history_selectors_are_required_to_receive_complete_records(tmp_path, selector):
    context = acquisition(tmp_path, prepare_only=True)
    api = context['api']
    suffix = (
        '/actions/runs?head_sha=' + SHA + '&per_page=100'
        if selector == 'event'
        else '/actions/runs/75090/jobs?per_page=100'
    )
    with pytest.raises(context['module'].RefusedError, match='unsupported addressed'):
        api(
            'https://api.github.com/repos/enhantica/crysta' + suffix,
            accept='application/vnd.github+json',
        )
    assert api.refusals, ' F5 omitted history/event selectors cannot silently get full history'
