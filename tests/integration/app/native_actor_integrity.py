"""Fail-closed admission of fixture-only startup in streamed QML actors."""

import hashlib
import json
import re

from tests.integration.py.test_table_and_about_contract import tokens


def structure(source):
    words = tokens(source)
    methods = {}
    residual = []
    index = 0
    depth = 0
    while index < len(words):
        if words[index] == 'function' and depth == 1:
            name = words[index + 1]
            opening = index + 2
            while opening < len(words) and words[opening] != '{':
                opening += 1
            nesting = 1
            end = opening + 1
            while end < len(words) and nesting:
                nesting += (words[end] == '{') - (words[end] == '}')
                end += 1
            if nesting or name in methods:
                raise ValueError('Unbalanced or duplicate actor member function')
            methods[name] = words[opening + 1 : end - 1]
            index = end
            continue
        residual.append(words[index])
        depth += (words[index] == '{') - (words[index] == '}')
        index += 1
    if depth:
        raise ValueError('Unbalanced actor structure')
    return methods, residual


def fixture_regression_pin(source):
    methods, declarations = structure(source)
    # Pin the reviewed fixture admission guards and every eager declaration, including
    # Component.onCompleted. Behavior methods are deliberately outside this fixture pin.
    startup = {name: body for name, body in methods.items() if name.endswith('TestCase')}
    return hashlib.sha256(json.dumps([declarations, startup]).encode()).hexdigest()


def problems(source, reporter, fixture_pin=None, *, shared_startup=False):
    methods, _ = structure(source)
    failures = []
    call = ', message => test.warn(message)' if reporter == 'direct' else ''
    begin = tokens(f'gateTurnSelector = Turn.begin(test, Probe{call});')
    end = tokens(f'Turn.end(gateTurnSelector{call});')
    initial = methods.get('init', [])
    cleanup = methods.get('cleanup', [])
    if initial[: len(begin)] != begin or initial.count('Turn.begin') != 1:
        failures.append('every behavior row must wait for its own request before setup')
    if cleanup[-len(end) :] != end or cleanup.count('Turn.end') != 1:
        failures.append('every behavior row must finish its own work before completion')
    if not shared_startup and any(name.endswith('TestCase') for name in methods):
        failures.append('unapproved shared lifecycle startup')
    if fixture_pin is None or fixture_regression_pin(source) != fixture_pin:
        failures.append('startup or eager declarations exceed reviewed fixture-only work')
    # Direct behavior invocation from an eager signal handler is refused even in
    # actors that have no shared fixture. Normal QtTest discovers these methods itself.
    _, declarations = structure(source)
    if any(re.fullmatch(r'(?:test\.)?test_\w+', word) for word in declarations):
        failures.append('eager declarations cannot invoke behavior methods')
    return failures
