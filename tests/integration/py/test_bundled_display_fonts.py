"""Display coverage uses font bytes as its oracle, never a recorded covered flag."""

import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
REFERENCE = json.loads((ROOT / 'tests/fixtures/display_fonts/cmaps.json').read_text())
# A lexer alternation consumes whole strings before comment markers inside them.
TOKENS = re.compile(
    r'//[^\n]*|/\*[\s\S]*?\*/|R"([^ ()\\]*)\([\s\S]*?\)\1"'
    r'|"(?:\\[\s\S]|[^"\\])*"|\'(?:\\[\s\S]|[^\'\\])*\'|`(?:\\[\s\S]|[^`\\])*`'
)
ESCAPES = re.compile(r'\\(?:u([\da-fA-F]{4})|U([\da-fA-F]{8})|x([\da-fA-F]+)|(.))')


def decode_cpp_literal(value):
    # C++ \x escapes denote bytes in an ordinary UTF-8 string, whereas
    # QML/JavaScript \x escapes denote Unicode code points.
    raw = bytearray()
    start = 0
    for escape in ESCAPES.finditer(value):
        raw.extend(value[start : escape.start()].encode('utf-8'))
        if escape.group(3):
            raw.append(int(escape.group(3), 16))
        elif escape.group(1) or escape.group(2):
            raw.extend(chr(int(escape.group(1) or escape.group(2), 16)).encode('utf-8'))
        else:
            raw.extend(escape.group(4).encode('utf-8'))
        start = escape.end()
    raw.extend(value[start:].encode('utf-8'))
    # A dynamic UTF-8 prefix is bytes, not an independently displayed glyph.
    return raw.decode('utf-8', errors='ignore')


def literals(text, *, cpp=False):
    tokens = list(TOKENS.finditer(text))
    index = 0
    while index < len(tokens):
        match = tokens[index]
        index += 1
        value = match.group()
        if cpp and value.startswith('"'):
            end = match.end()
            while index < len(tokens):
                following = index
                while following < len(tokens) and tokens[following].group().startswith((
                    '//',
                    '/*',
                )):
                    following += 1
                if following == len(tokens) or not tokens[following].group().startswith('"'):
                    break
                gap = re.sub(r'//[^\n]*|/\*[\s\S]*?\*/', '', text[end : tokens[following].start()])
                if gap.strip():
                    break
                value = value[:-1] + tokens[following].group()[1:]
                end = tokens[following].end()
                index = following + 1
        if value.startswith(('//', '/*')):
            continue
        if cpp and value.startswith('R"'):
            yield match.start(), value
            continue
        # Consuming escaped backslashes prevents treating "\\\\u2153" as a fraction.
        if cpp:
            yield match.start(), decode_cpp_literal(value)
            continue
        decoded = ESCAPES.sub(
            lambda escape: (
                chr(int(next(g for g in escape.groups()[:3] if g), 16))
                if any(escape.groups()[:3])
                else escape.group(4)
            ),
            value,
        )
        yield match.start(), decoded


def covered(family, char):
    return all(
        any(first <= ord(char) <= last for first, last in face['ranges'])
        for face in REFERENCE['fonts'][family]
    )


def displayed_characters():
    found = []
    for directory in ('app/qml', 'app/src', 'core/src', 'core/include'):
        for path in sorted((ROOT / directory).rglob('*')):
            if path.suffix not in {'.qml', '.js', '.cpp', '.hpp'}:
                continue
            # core/report.cpp builds terminal output; ReportViewModel composes
            # the app's separate rich text, which remains in this census.
            if path == ROOT / 'core/src/report.cpp':
                continue
            text = path.read_text()
            for at, value in literals(text, cpp=path.suffix in {'.cpp', '.hpp'}):
                found.extend(
                    (path.relative_to(ROOT).as_posix(), text.count('\n', 0, at) + 1, char)
                    for char in set(value)
                    if ord(char) >= 128
                )
    # ParameterItem::label_text emits all decimal subscripts, including digits not
    # presently in a schema label. The formatter's declared digit domain is 0..9.
    formatter = (ROOT / 'app/src/parameter_item.cpp').read_text()
    if re.search(r'QChar\(\s*0x2080\s*\+\s*\w+\.digitValue\(\)\s*\)', formatter):
        found.extend(
            ('app/src/parameter_item.cpp', 0, chr(code)) for code in range(0x2080, 0x208A)
        )
    for path in sorted((ROOT / 'app/src').glob('*.cpp')):
        text = path.read_text()
        # QChar constructed numerically is another emitted character, not a string.
        for match in re.finditer(r'QChar\(\s*(0x[\da-fA-F]+|\d+)\s*\)', text):
            code = int(match.group(1), 0)
            if code >= 128:
                found.append((
                    path.relative_to(ROOT).as_posix(),
                    text.count('\n', 0, match.start()) + 1,
                    chr(code),
                ))
    return found


def test_font_reference_is_bound_to_packaged_bytes_and_archive():
    cmake = (ROOT / 'cmake/EdiGuiBase.cmake').read_text()
    assert REFERENCE['archive_sha256'] in cmake, (
        'Display cmap references must match the hash-verified gui-components archive'
    )
    for faces in REFERENCE['fonts'].values():
        for face in faces:
            assert '"' + face['path'] + '"' in cmake or (
                '${PROJECT_SOURCE_DIR}/app/resources/fonts/' + face['path'] in cmake
            ), 'Every referenced rendering face must be included in the app resources'
            base = ROOT / (
                'build/app/_deps/gui_components-src/src/EasyApplication/Gui/Resources/Fonts'
                if face['origin'] == 'base'
                else 'app/resources/fonts'
            )
            path = base / face['path']
            if path.is_file():
                assert hashlib.sha256(path.read_bytes()).hexdigest() == face['sha256'], (
                    'Actual bundled font bytes must match their independent cmap reference'
                )
            else:
                assert face['origin'] == 'base', (
                    'Owned font resources must exist even before the app is configured'
                )


def generated_label_digit_is_bundled(char):
    # This generated domain is not a literal in the production census. Its real
    # default-text fallback is exercised independently by the Qt shaping actor.
    setup = (ROOT / 'app/src/engine_setup.cpp').read_text()
    registered = (
        'QFont::insertSubstitution(family, fallback)' in setup
        and '{"PT_Sans/PTSans-Regular.ttf", "Noto_Sans/NotoSans-Regular.ttf"}' in setup
    )
    return '\u2080' <= char <= '\u2089' and registered and covered('Noto Sans', char)


def test_display_census_includes_literals_escapes_and_formatter_domain():
    assert [value for _, value in literals(r'"\xe2\x82\xac \u00c5"', cpp=True)] == ['"€ Å"'], (
        'The C++ display observer decodes UTF-8 byte escapes '
        'and Unicode escapes as rendered glyphs'
    )
    assert [value for _, value in literals(r'"\xe2\x82" /* split */ "\xac"', cpp=True)] == [
        '"€"'
    ], 'Adjacent C++ string fragments form one rendered UTF-8 glyph even across a comment'
    assert [value for _, value in literals(r'"\xe2\x82"', cpp=True)] == ['""'], (
        'A dynamic byte prefix is never misreported as standalone Unicode display characters'
    )
    assert [value for _, value in literals(r'"\xe2\x82\xac"')] == ['"â\x82¬"'], (
        'The QML display observer retains JavaScript code-point escape semantics'
    )
    assert [value for _, value in literals(r'"\\u2153"', cpp=True)] == [r'"\u2153"'], (
        'An escaped backslash never turns a literal escape spelling into a displayed fraction'
    )
    census = json.loads((ROOT / 'data/display-glyphs.json').read_text())['characters']
    sites = {(site.rsplit(':', 1)[0], row['char']) for row in census for site in row['sites']}
    missing = sorted({
        (path, f'U+{ord(char):04X}')
        for path, _, char in displayed_characters()
        if (path, char) not in sites
        and not (path == 'app/src/parameter_item.cpp' and generated_label_digit_is_bundled(char))
    })
    assert not missing, (
        'The displayed alphabet must include escaped literals, numeric QChar values '
        'and every generated digit must have independent bundled cmap coverage: ' + repr(missing)
    )


@pytest.mark.parametrize('family', sorted(REFERENCE['fonts']))
def test_each_recorded_display_site_has_a_real_glyph_in_its_rendering_face(family):
    census = json.loads((ROOT / 'data/display-glyphs.json').read_text())['characters']
    assert all(row['font'] in REFERENCE['fonts'] for row in census), (
        'Every display row must name a rendering face with independently proven bundled glyphs'
    )
    missing = [
        (row['code'], row['sites'])
        for row in census
        if row['font'] == family
        and (
            row.get('drawn_by', row['font']) not in REFERENCE['fonts']
            or not any(
                face['weight'] == row.get('weight')
                and any(first <= ord(row['char']) <= last for first, last in face['ranges'])
                for face in REFERENCE['fonts'].get(row.get('drawn_by', row['font']), [])
            )
        )
    ]
    assert not missing, (
        'Each character must have a nonzero cmap glyph in every selected bundled face, '
        'without relying on a system substitute: ' + repr(missing)
    )


def test_wyckoff_fraction_font_selection_reaches_the_actual_delegate():
    atoms = (ROOT / 'app/qml/Pages/Structure/AtomSitesGroup.qml').read_text()
    combo = (ROOT / 'app/qml/Components/SearchableComboBox.qml').read_text()
    assert re.search(r'listFontFamily:\s*"Noto Sans"', atoms), (
        'The Wyckoff list must select the bundled fraction font at its display site'
    )
    assert re.search(r'font\.family:\s*control\.listFontFamily', combo), (
        'The actual list delegate must apply the caller-selected fraction font'
    )
    assert all(covered('Noto Sans', char) for char in '¼½¾⅓⅔⅙⅚⅛⅜⅝⅞\u2212'), (
        'The complete Wyckoff formatter alphabet must exist in the selected font'
    )


def test_default_label_formatter_alphabet_has_no_missing_glyphs():
    # These outputs flow through ParameterItem to ParameterCell/IconLine text
    # segments using the default style family, not through the Wyckoff list.
    paths = {'app/src/parameter_item.cpp', 'core/include/edi/parameter_spec.hpp'}
    alphabet = {char for path, _, char in displayed_characters() if path in paths}
    census = json.loads((ROOT / 'data/display-glyphs.json').read_text())['characters']
    rendering = {row['char']: row.get('drawn_by', row['font']) for row in census}
    missing = sorted(
        f'U+{ord(char):04X}'
        for char in alphabet
        if not generated_label_digit_is_bundled(char)
        and (rendering.get(char) not in REFERENCE['fonts'] or not covered(rendering[char], char))
    )
    assert not missing, (
        'Default label formatter outputs must have real glyphs in their bundled rendering faces: '
        + repr(missing)
    )


def test_legend_marks_are_geometry_not_displayed_characters():
    # Pattern series are drawn shapes; elements use the bundled atom icon.
    # Unicode line and circle substitutes are forbidden even with a font mapping.
    files = [
        'app/src/pattern_chart_controller.cpp',
        'app/src/structure_view_controller.cpp',
        'app/qml/Components/ChartLegend.qml',
    ]
    offenders = [
        (path, char)
        for path in files
        for _, value in literals((ROOT / path).read_text())
        for char in value
        if char in '\u2500\u2501\u2502\u25cf'
    ]
    assert not offenders, (
        'Legend marks must be drawn shapes with the same appearance on desktop and web: '
        + repr(offenders)
    )
    legend = (ROOT / 'app/qml/Components/ChartLegend.qml').read_text()
    assert not re.search(r'["\']?text["\']?\s*:\s*entry\.mark', legend), (
        'The real legend delegate must never send its mark through a text glyph pipeline'
    )


def test_structure_legend_uses_the_atom_table_icon_pipeline():
    controller = (ROOT / 'app/src/structure_view_controller.cpp').read_text()
    legend = (ROOT / 'app/qml/Components/ChartLegend.qml').read_text()
    table = (ROOT / 'app/qml/Pages/Structure/AtomSitesGroup.qml').read_text()
    colors = (ROOT / 'app/qml/Style/AppColors.qml').read_text()
    assert 'QStringLiteral("atom")' in controller, (
        'Every structure legend element must carry the atom icon instead of a circle'
    )
    assert re.search(r'["\']icon["\']\s*:\s*(?:entry\.mark|["\']atom["\'])', legend), (
        'The element legend must send its atom through the same icon segment pipeline as the table'
    )
    assert 'row.fractX.categoryIcon' in table and 'AppColors.element(row.typeSymbol)' in table, (
        'The parity witness must remain connected to the actual table element icon and colour'
    )
    assert 'structureViewOptions.colorScheme' in colors, (
        'The table element colour must follow the selected structure-view scheme'
    )
