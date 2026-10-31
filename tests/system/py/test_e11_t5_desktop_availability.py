"""Desktop availability remains enabled alongside the explicit WASM refusal path."""

import json

import test_e11_t5_dev_native_integration as base

main_actor = base.main_actor


def test_desktop_ai_preferences_stay_available_with_actual_main(main_actor):
    actor = main_actor([[]])
    actor.connect()
    before = base.qml(actor, 'ApplicationInfo.assistantAvailable')
    actor.command('click', name='appBar.button.preferences')
    actor.until(lambda _value: base.qml(actor, base.control_expression('preferences') + '.opened'))
    tab = base.control_expression('preferences.tab.aiAssistance')
    enabled = base.qml(actor, tab + '.enabled')
    (actor.folder / 'desktop-ai-tab-before.json').write_text(
        json.dumps({'available': before, 'enabled': enabled, 'actual': actor.last}, indent=2)
    )
    assert before is True and enabled is True, (
        'The desktop app retains an available assistant and enabled AI preferences tab'
    )
    actor.command('click', name='preferences.tab.aiAssistance')
    actor.until(lambda _value: base.qml(actor, tab + '.checked') is True)
    selected = base.qml(actor, tab + '.checked')
    (actor.folder / 'desktop-ai-tab-selected.json').write_text(
        json.dumps({'selected': selected, 'actual': actor.last}, indent=2)
    )
    assert selected is True, 'The actual enabled desktop AI tab accepts physical selection'
