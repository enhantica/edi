"""Retain per-case Qt outcomes without certifying an incomplete shared host."""


def receipt(case, suite='OnboardingTutorials'):
    function, _, tag = case.partition(':')
    return f'::{suite}::test_{function}({tag})'


def check_observation(result, selected, requested, suite='OnboardingTutorials'):
    output = result.stdout + result.stderr
    lines = output.splitlines()
    outcomes = [line for line in lines if line.startswith(('PASS', 'FAIL!', 'SKIP'))]
    for boundary in ('initTestCase', 'cleanupTestCase'):
        matching = [line for line in outcomes if f'::{suite}::{boundary}()' in line]
        assert len(matching) == 1 and matching[0].startswith('PASS'), (
            'The shared tutorial host must start and finish successfully: ' + output
        )
    for case in requested:
        matching = [line for line in outcomes if receipt(case, suite) in line]
        assert len(matching) == 1, (
            'Every requested tutorial case must retain exactly one completed outcome: ' + output
        )
    failed = [line for line in outcomes if line.startswith('FAIL!')]
    assert all(any(receipt(case, suite) in line for case in requested) for line in failed), (
        'Failures outside the requested tutorial actions invalidate the shared host: ' + output
    )
    assert result.returncode >= 0 and ((result.returncode == 0) == (not failed)), (
        'A terminated or inconsistently reported tutorial host cannot certify outcomes: ' + output
    )
    matching = [line for line in outcomes if receipt(selected, suite) in line]
    assert len(matching) == 1 and matching[0].startswith('PASS'), (
        'Every tutorial lifecycle case must pass its own real UI actions without a skip: ' + output
    )
