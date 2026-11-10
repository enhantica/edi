"""X1: the owner-declared GPL chart and worker supersede prior ADR text."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('number', ['0020', '0021'])
def test_new_functionality_has_the_named_adr(number):
    paths = list((ROOT / 'docs/dev/adrs').glob(f'{number}-*.md'))
    assert len(paths) == 1, (
        ' gate 6 each worker and presentation block has its distinct agreed ADR'
    )


@pytest.mark.parametrize('number', ['0006', '0008', '0015'])
def test_prior_licensing_contracts_record_the_gpl_graphs_decision(number):
    texts = '\n'.join(path.read_text() for path in (ROOT / 'docs/dev/adrs').glob(f'{number}-*.md'))
    assert 'GPLv3' in texts or 'GPL-3' in texts, (
        ' X1 prior web dependency and app ADRs record the owner GPL distribution decision'
    )


def test_dependency_manifest_and_about_notice_match_the_owner_decision():
    manifest = (ROOT / 'pixi.toml').read_text()
    dependencies = (ROOT / 'DEPENDENCIES.md').read_text()
    assert re.search(r'^qt6-graphs\s*=', manifest, re.MULTILINE), (
        ' gate 6 the actual app environment declares Qt Graphs'
    )
    assert 'Qt Graphs' in dependencies and ('GPLv3' in dependencies or 'GPL-3' in dependencies), (
        ' gate 6 dependencies declare the linked GPL component'
    )
    about = (ROOT / 'app/qml/Pages/Home/AboutDialog.qml').read_text()
    info = (ROOT / 'app/src/app_info.hpp').read_text() + (
        ROOT / 'app/src/app_info.cpp'
    ).read_text()
    assert 'model: ApplicationInfo.appLicenceIds' in about, (
        'About shows one clickable identifier for each app and source licence'
    )
    icon_link = (ROOT / 'app/qml/Components/IconLink.qml').read_text()
    assert re.search(r'^EaElements\.Button\s*\{', icon_link, re.MULTILINE), (
        'Required: the licence delegate uses the original Button click signal.'
    )
    licence_delegate = re.search(
        r'Repeater\s*\{\s*model: ApplicationInfo\.appLicenceIds\s+'
        r'IconLink\s*\{([^{}]*)\}',
        about,
    )
    assert licence_delegate and re.search(
        r'^\s*onClicked: ApplicationInfo\.aboutOpenLicence\(\)\s*$',
        licence_delegate.group(1),
        re.MULTILINE,
    ), 'Required: clicking each app licence IconLink calls its native licence-opening procedure.'
    opener = re.search(
        r'void ApplicationInfo::aboutOpenLicence\(\) const\s*{(.*?)\n}', info, re.DOTALL
    )
    assert opener, 'The About licence action has its native presentation implementation'
    body = re.sub(r'\s+', ' ', opener.group(1))
    assert 'panelUsageContextRead(f, "ApplicationInfo")' in body, (
        'Licence activation keeps the actual current ApplicationInfo receiver'
    )
    assert re.search(
        r'textIndex\(f, assistantContextField\(f, "ApplicationInfo", "appLicenceUrls"\), '
        r'assistantContextField\(f, "licenceEntry", "index"\)\)',
        body,
    ), 'Each licence identifier retains its exact indexed bundled URL selection'
    assert 'panelUsageDeferredMemberCall(f, info, "licenceText"' in body, (
        'The selected bundled URL is read through the original licenceText method'
    )
    assert 'assistantMemberWrite(f, next, "licence", licence)' in body, (
        'The same complete bundled text is published into the original licence popup'
    )
    assert 'projectInvoke(f, "licencePopup", "open")' in body, (
        'Licence activation opens the original popup after populating its full text'
    )
    assert re.search(
        r'QStringList appLicenceIds\(\) const\s*\{\s*return \{'
        r'QStringLiteral\("BSD-3-Clause"\), QStringLiteral\("GPL-3.0-only"\)\}',
        info,
    ), 'About lists the source BSD and distributed app GPL identifiers in that order'
    assert 'return {licenseUrl(), copyingUrl()};' in info, (
        'The licence identifiers map to LICENSE and COPYING in the same order'
    )
    assert 'qrc:/LICENSE' in info and 'qrc:/COPYING' in info, (
        'Both About licence links resolve to their complete bundled texts'
    )
    assert 'about.licence"' not in about and 'This app is distributed under' not in about, (
        'the About window must omit the superseded distribution sentence'
    )
