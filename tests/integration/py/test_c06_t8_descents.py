"""The retired snap descents migrate on load and cannot be selected as active flows."""

import importlib
import json
import re
import shutil
import warnings
from pathlib import Path

import pytest

from tests.fixtures.c06_t8.descent_contract import RETIRED, VALID, advertisements

ROOT = Path(__file__).resolve().parents[3]
PRODUCT = 'edi'
SOURCE = ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project'
SCOPES = {
    'feature_docs': ('docs/dev/features.md',),
    'gui_capture': ('website/surfaces/docs/assets/gui/scan/scan-analysis-extras.json',),
    'reference_docs': ('website/surfaces/docs/physics', 'website/surfaces/docs/assets/reference'),
    'user_docs': ('docs/user', 'website/surfaces/docs/user-guide'),
    'examples': ('examples', 'app/examples', 'app/tutorials'),
}


def module():
    return importlib.import_module(PRODUCT)


def copied(tmp_path, descent):
    target = tmp_path / 'project'
    shutil.copytree(SOURCE, target)
    path = target / 'analysis/analysis.edi'
    text = re.sub(r'(?m)^_minimizer\.descent[^\n]*\n?', '', path.read_text())
    if descent is not None:
        text += '\n_minimizer.descent ' + descent + '\n'
    path.write_text(text)
    return target


@pytest.mark.parametrize('token', RETIRED)
def test_retired_project_descent_warns_once_migrates_and_stays_migrated(tmp_path, capfd, token):
    engine = module()
    source = copied(tmp_path, token)
    capfd.readouterr()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        project = engine.Project.load(source)
    output = capfd.readouterr()
    lines = (output.out + output.err).splitlines() + [str(item.message) for item in caught]
    notices = [line for line in lines if token in line]
    assert len(notices) == 1, (
        'A retired descent declaration must produce exactly one migration warning'
    )
    assert re.search(r'retir|remov|replac|migrat|no longer', notices[0], re.IGNORECASE), (
        'The warning must explain why the retired descent changed'
    )
    assert 'fast_descent' in notices[0].replace(token, ''), (
        'The warning must name the replacement descent separately from the retired name'
    )
    actual = project.analysis.descent if PRODUCT == 'edi' else project._minimizer_descent
    assert actual == 'fast_descent', 'Legacy input must load as the retained fast descent'
    for index in range(2):
        destination = tmp_path / f'saved-{index}'
        project.save_as(destination)
        text = (destination / 'analysis/analysis.edi').read_text()
        assert not any(name in text for name in RETIRED), (
            'Saving migrated input must never resurrect a retired descent'
        )
        capfd.readouterr()
        with warnings.catch_warnings(record=True) as repeated:
            warnings.simplefilter('always')
            project = engine.Project.load(destination)
        out = capfd.readouterr()
        assert not repeated, 'Reopening migrated input must emit no Python warning'
        assert not (out.out + out.err).strip(), (
            'Reopening migrated input must emit no repeated native warning'
        )
        actual = project.analysis.descent if PRODUCT == 'edi' else project._minimizer_descent
        assert actual == 'fast_descent', 'The replacement selection must survive both round trips'


@pytest.mark.parametrize('group', SCOPES)
def test_retired_descents_are_not_advertised_on_public_surfaces(group):
    found = advertisements(ROOT, SCOPES[group])
    assert not found, 'Retired descents must not be advertised as choices: ' + '; '.join(found)


@pytest.mark.parametrize(
    ('group', 'spelling'),
    [
        (group, spelling)
        for group, scopes in SCOPES.items()
        for spelling in ['token', 'display-label', 'escaped-json']
        if spelling != 'escaped-json' or Path(scopes[0]).suffix in {'', '.json'}
    ],
)
def test_each_surface_rejects_retired_choice_spellings(tmp_path, group, spelling):
    for name in SCOPES[group]:
        path = tmp_path / name
        if path.suffix:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{}' if path.suffix == '.json' else 'clean')
        else:
            path.mkdir(parents=True, exist_ok=True)
            (path / 'clean.md').write_text('clean')
    assert not advertisements(tmp_path, SCOPES[group]), 'A clean surface is the positive control'
    target = tmp_path / SCOPES[group][0]
    if target.is_dir():
        target /= 'choice.json' if spelling == 'escaped-json' else 'choice.md'
    text = 'Fast descent with guarded linear snap' if spelling == 'display-label' else RETIRED[0]
    if target.suffix == '.json':
        text = json.dumps({'options': [text]}).replace('_snap', r'_\u0073nap')
    target.write_text(text)
    assert advertisements(tmp_path, SCOPES[group]), (
        'Every public surface must reject token, display-label and escaped JSON choice forms'
    )


def test_a_missing_surface_cannot_pass(tmp_path):
    with pytest.raises(AssertionError, match='must exist'):
        advertisements(tmp_path, ['absent'])


def test_retirement_prose_does_not_advertise_an_active_choice(tmp_path):
    path = tmp_path / 'migration.md'
    path.write_text('Legacy fast_descent_linear_snap is retired; use fast_descent.\n')
    assert not advertisements(tmp_path, [path.name]), (
        'Explicitly retired migration prose must remain possible without a selectable old flow'
    )

    path.write_text(
        'The two descents (`fast_descent_linear_snap`,\n'
        '`fast_descent_guarded_linear_snap`) are\nretired (ADR-0125).\n'
    )
    assert not advertisements(tmp_path, [path.name]), (
        'Retirement prose retains its meaning when names and the predicate wrap across lines'
    )
    for caution in (
        'Do not use fast_descent_linear_snap;\nit is retired.\n',
        'Never select fast_descent_guarded_linear_snap; it was removed.\n',
    ):
        path.write_text(caution)
        assert not advertisements(tmp_path, [path.name]), (
            'A negated invitation with an explicit retirement notice is migration prose'
        )
    for suffix in (
        'Choose fast_descent_linear_snap.\n',
        '- Select fast_descent_guarded_linear_snap\n',
        'Retired:\nUse fast_descent_linear_snap\n',
        'Retired:\n```text\nfast_descent_linear_snap is retired\n```\n',
        'Retired:\n~~~text\nfast_descent_linear_snap is retired\n~~~\n',
        'Retired:\n````text\n```\nfast_descent_linear_snap is retired\n````\n',
    ):
        path.write_text('The old choices are retired.\n' + suffix)
        assert advertisements(tmp_path, [path.name]), (
            'A retirement notice cannot conceal an active invitation list item or code example'
        )


def test_python_registry_and_default_match_the_owner_decision():
    engine = module()
    assert set(engine._descent_ids()) == VALID, (
        'The live Python registry must contain exactly the three retained descents'
    )
    assert engine._default_descent() == 'multistart_prune', (
        'The engine-advertised default must be the two-probe flow'
    )
    project = engine.Project()
    assert project.descent == project.analysis.descent == 'multistart_prune', (
        'Both public Python selectors must resolve an absent declaration to the two-probe flow'
    )
    project.analysis.descent = 'ladder'
    project.analysis.descent = None
    assert project.analysis.descent == 'multistart_prune', (
        'Clearing an explicit choice must restore the new effective default'
    )


@pytest.mark.parametrize('token', RETIRED)
@pytest.mark.parametrize('surface', ['project', 'analysis'])
def test_retired_token_cannot_remain_an_active_python_selection(token, surface):
    project = module().Project()
    owner = project if surface == 'project' else project.analysis
    refusal = None
    try:
        owner.descent = token
    except (ValueError, RuntimeError) as error:
        refusal = str(error)
    if refusal is not None:
        assert 'descent' in refusal.lower(), 'A refusal must identify the retired descent'
        return
    assert owner.descent == 'fast_descent', (
        'A compatibility alias must normalize to the retained fast descent'
    )
