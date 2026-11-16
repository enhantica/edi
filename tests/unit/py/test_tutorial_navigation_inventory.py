"""Physical module ownership retains every declared native field-row assertion."""

from collections import Counter

from tests.system.py import test_tutorial_ferrite_fields as ferrite
from tests.system.py import test_tutorial_navigation as navigation
from tests.system.py import test_tutorial_ncaf_fields as ncaf


def test_analysis_context_modules_preserve_every_original_native_row_once():
    owners = navigation.CASES + ncaf.CASES + ferrite.CASES
    assert Counter(owners) == Counter(navigation.ALL_CASES), (
        'Separating shared scientific project setup preserves every original native row '
        'exactly once, including creation and download contexts in their original owner'
    )
    for module, lesson in (
        (ncaf, 'pd-neut-tof_ncaf-wish'),
        (ferrite, 'pd-neut-tof_ferrite-austenite-beer'),
    ):
        assert module.CASES and all(
            navigation.analysis_field_case(case, lesson) for case in module.CASES
        ), 'Each shared scientific project owns only its declared Analysis field context'
        assert sorted(module.CASES, key=lambda case: case.partition(':')[0]) == module.CASES, (
            'Each real native actor still receives Qt function and original data-row order'
        )
