"""The new popups paint their data and accept real mouse input in the Qt host."""

import re

import pytest

from tests.integration.app import test_onboarding_views as host


@pytest.mark.parametrize(
    ('actor', 'suite', 'case'),
    [
        *[
            ('tst_onboarding_changes.qml', 'OnboardingChanges', case)
            for case in (
                'manual_popup_filters_since_seen_and_sorts_newest_first',
                'show_all_changes_lists_every_entry',
                'show_all_changes_stays_in_footer:default',
                'show_all_changes_stays_in_footer:small',
                'documentation_link_opens_the_full_changes_page',
                'update_opens_once_then_restart_remembers_seen_date',
                'current_and_future_seen_dates_do_not_auto_open:current',
                'current_and_future_seen_dates_do_not_auto_open:future',
            )
        ],
        *[
            (
                'tst_onboarding_choices.qml',
                'OnboardingChoices',
                f'opened_choices_are_visible_and_selectable:{case}',
            )
            for case in ('feedback-kind', 'logging-level')
        ],
    ],
    ids=lambda value: value,
)
def test_changes_and_choices_in_the_real_host(actor, suite, case):
    host.test_production_onboarding_control(actor, suite, case)


def test_each_shipped_changes_entry_has_unique_feature_titles():
    text = (host.ROOT / 'website/surfaces/docs/changelog.md').read_text()
    entries = re.findall(
        r'^## (\d{4}-\d{2}-\d{2})\s*\n(.*?)(?=^## |\Z)', text, re.MULTILINE | re.DOTALL
    )
    assert entries, 'The shipped changes page must contain dated entries to inspect'
    for date, body in entries:
        titles = re.findall(r'^- \*\*(.+?)\*\*', body, re.MULTILINE)
        assert titles, f'Each changes entry exposes feature titles: {date}'
        normalized = [' '.join(title.strip().rstrip('.:').casefold().split()) for title in titles]
        duplicates = sorted({title for title in normalized if normalized.count(title) > 1})
        assert not duplicates, (
            f'One changes entry must not repeat a feature title, including punctuation variants: '
            f'{date}: {duplicates}'
        )
