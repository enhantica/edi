"""Source census and escape controls for the ADR-0108 magnetic token boundary."""

import os
import re
from pathlib import Path

import pytest

from tests.fixtures.magnetic_pnma import token_census, token_inputs

ENGINE_ROOT = (
    Path(os.environ['CRYSTA_CONSUMER_SRC']) if os.environ.get('CRYSTA_CONSUMER_SRC') else None
)
ROOT = Path(__file__).resolve().parents[3]
HOME = 'magnetic_pnma'


ESCAPES = [
    'local-cif-tag',
    'check-reader',
    'validate-helper',
    'model-text',
    'macro-reader',
    'macro-helper',
    'global-tag',
    'fragmented-tag',
    'helper-alias',
    'auto-helper',
    'new-file',
    'untagged-helper',
    'dummy-decoder',
    'quote-strip',
    'prefix-number',
    'missing-end-check',
    'generic-argument',
    'indented-member',
    'aliased-number',
    'renamed-marker',
    'reversed-marker',
    'strcmp-marker',
]


@pytest.mark.parametrize('escape', ESCAPES)
def test_census_detects_added_or_indirect_decoder_bypasses(escape):
    decorative = 'kept_token_value("unused"); '
    get_ion = 'auto decoded = block.get("_magnetic_form_factor.ion"); '
    get_number = 'block.get("_atom_site_moment.cartn_x")'
    bodies = {
        'local-cif-tag': (
            'return std::stod(block.get("_edi_magnetic_form_factor.j2_coefficient"));'
        ),
        'check-reader': 'return std::stod(' + get_number + ');',
        'validate-helper': decorative + 'return validate_value(' + get_number + ');',
        'model-text': 'return std::stod(structure.propagation_vectors[0].second);',
        'macro-reader': 'return READ_MAGNETIC(block);',
        'macro-helper': decorative + 'return PARSE_NUMBER(' + get_number + ');',
        'global-tag': 'return std::stod(block.get(MAGNETIC_TAG));',
        'fragmented-tag': (
            'return std::stod(block.get("_magnetic_" "form_factor.j2_coefficient"));'
        ),
        'helper-alias': 'auto parser = opaque; return parser(' + get_number + ');',
        'auto-helper': 'return opaque(' + get_number + ');',
        'new-file': 'return std::stod(' + get_number + ');',
        'generic-argument': 'return std::stod(' + get_number + ');',
        'indented-member': 'return std::stod(' + get_number + ');',
        'untagged-helper': ('return opaque(block.get("_parent_propagation_vector.kxkykz"));'),
        'dummy-decoder': decorative + get_ion + 'return decoded == "?" ? "" : decoded;',
        'renamed-marker': decorative + get_ion + 'return decoded == "." ? "" : decoded;',
        'reversed-marker': decorative + get_ion + 'return "." == decoded ? "" : decoded;',
        'strcmp-marker': (
            decorative + get_ion + 'return std::strcmp(decoded.c_str(), "?") == 0 ? "" : decoded;'
        ),
        'aliased-number': (
            decorative + 'auto parser = std::stod; return parser(' + get_number + ');'
        ),
        'quote-strip': (
            decorative
            + 'auto text = block.get("_space_group_magn_transforms.source"); '
            + 'return text.substr(1, text.size() - 2);'
        ),
        'prefix-number': decorative + 'return std::stod(' + get_number + ');',
        'missing-end-check': (
            decorative
            + 'auto text = '
            + get_number
            + '; char* end; '
            + 'auto number = std::strtod(text.c_str(), &end); '
            + 'if (!std::isfinite(number)) throw bad(); return number;'
        ),
    }
    argument = 'auto& block' if escape == 'generic-argument' else 'const EdiBlock& block'
    reader = 'auto fresh(' + argument + ') { ' + bodies[escape] + ' }'
    if escape == 'indented-member':
        reader = 'struct NewReader {\n    ' + reader + '\n};'
    sources = {
        'unanticipated/old_or_new_reader.cpp': reader,
        'unanticipated/opaque.cpp': (
            'auto opaque(const std::string& input) { return std::stod(input); }'
        ),
    }
    if escape == 'model-text':
        sources['unanticipated/old_or_new_reader.cpp'] = (
            'auto fresh(const Structure& structure) { ' + bodies[escape] + ' }'
        )
    if escape == 'check-reader':
        sources['unanticipated/old_or_new_reader.cpp'] = reader.replace('fresh(', 'check_value(')
    if escape == 'validate-helper':
        sources['unanticipated/validation.cpp'] = (
            'auto validate_value(const std::string& input) { return opaque(input); }'
        )
    if escape == 'global-tag':
        sources['unanticipated/old_or_new_reader.cpp'] = (
            'constexpr auto MAGNETIC_TAG = "_magnetic_form_factor.j2_coefficient";\n' + reader
        )
    if escape == 'auto-helper':
        sources['unanticipated/opaque.cpp'] = (
            'auto opaque(auto input) { return std::stod(input); }'
        )
    if escape == 'macro-reader':
        sources['unanticipated/macros.hpp'] = (
            '#define READ_MAGNETIC(b) std::stod((b).get("_atom_site_moment.cartn_x"))\n'
        )
    if escape == 'macro-helper':
        sources['unanticipated/macros.hpp'] = '#define PARSE_NUMBER(t) std::stod(t)\n'
    errors = token_census.violations(sources)
    assert errors, 'Added or indirect token bypasses cannot escape the census: ' + escape
    if escape == 'untagged-helper':
        assert any('opaque:' in error for error in errors), (
            'Tokens are followed into helpers without magnetic tags or reader-like names'
        )


def test_census_accepts_a_direct_shared_decoder_without_a_local_parser():
    sources = {
        'fresh.cpp': (
            'auto fresh(const EdiBlock& block) { '
            'return kept_token_value(block.get("_space_group_magn.name_BNS")); }'
        )
    }
    assert not token_census.violations(sources), (
        'A shared decoder is admitted without requiring a particular wrapper name'
    )
    label_reader = {
        'core/src/parameter_paths.cpp': 'auto resolve_instrument_label(const EdiBlock& b) { '
        'return std::stoul(b.get("_magnetic_form_factor.j2_coefficient")); }',
    }
    assert token_census.violations(label_reader), (
        'The metadata-index classification cannot exempt a new magnetic operand in the same helper'
    )
    aliased_label = {
        'core/src/parameter_paths.cpp': (
            'auto resolve_instrument_label(const EdiBlock& b) { '
            'kept_token_value("unused"); '
            'auto label=b.get("_magnetic_form_factor.j2_coefficient"); '
            'if (label.rfind("background[", 0) == 0 && label.back() == \']\') '
            'return std::stoul(label.substr(11,label.size()-12)); return 0; }'
        ),
    }
    assert token_census.violations(aliased_label), (
        'A magnetic token aliased as label remains a raw value despite the metadata-index shape'
    )
    # A follow-up name never exempts a new magnetic caller or copied helper.
    for helper in ('quoted_no_value', 'unknown_cif', 'decode_id_view', 'unquote_cif'):
        bypass = {
            'new.cpp': 'auto fresh(const EdiBlock& b) { kept_token_value("unused"); return '
            + helper
            + '(b.get("_atom_site_moment.symmform")); }',
        }
        assert any(
            'new magnetic call instance' in error for error in token_census.violations(bypass)
        ), 'Decision 7cadf1c72 pins old calls and still detects a new caller of ' + helper
        copied = {
            'src/core/cif_import.cpp': 'auto '
            + helper
            + '(const EdiBlock& b) { '
            + 'kept_token_value("unused"); auto v=b.get("_atom_site_moment.symmform"); '
            + 'return v == "." ? "" : v; }',
        }
        assert token_census.violations(copied), (
            'Decision 7cadf1c72 never exempts a changed or newly copied helper body: ' + helper
        )


def test_opaque_reader_entrances_share_the_source_scanner():
    sources = token_census.source_tree(ROOT, ENGINE_ROOT)
    candidates = {
        path: text
        for path, text in sources.items()
        if 'kept_iso_declarations' in text or 'scan_kept_iso' in text
    }
    nodes = token_census.functions(candidates)
    if (ROOT / 'src/core/kept_iso.cpp').exists():
        wrappers = [row for row in nodes.values() if row['name'] == 'kept_iso_declarations']
        assert wrappers, 'The native opaque reader exists in the source census'
        assert all('scan_kept_iso(' in row['clean'] for row in wrappers), (
            'Native opaque entrances scan original block text through scan_kept_iso'
        )
    else:
        readers = [row for row in nodes.values() if row['name'] == 'read_magnetic']
        assert readers, 'The source census finds the edi magnetic reader'
        assert all('kept_iso_declarations_of(' in row['clean'] for row in readers), (
            'Edi opaque declarations use the bridge to the same source scanner'
        )


def test_census_does_not_decode_cpp_comments_or_digit_separators():
    sources = {
        'reader.cpp': (
            "auto fresh(const EdiBlock& block) { constexpr auto n = 1'000;\n"
            '// a numeric separator and a comment with a "?" marker\n'
            'return kept_token_value(block.get("_space_group_magn.name_BNS")); }'
        )
    }
    assert not token_census.violations(sources), (
        'C++ comments and digit separators cannot manufacture or hide token readers'
    )


def test_census_accepts_whole_token_numeric_admission_without_prescribing_its_name():
    sources = {
        'boundary.cpp': (
            'auto fresh(const EdiBlock& block) { auto decoded = '
            'kept_token_value(block.get("_atom_site_moment.Cartn_x")); '
            'return independent_numeric_reader(decoded.value); }'
        ),
        'numeric.cpp': (
            'double independent_numeric_reader(const std::string& token) { '
            'std::size_t consumed; double value = std::stod(token, &consumed); '
            'if (consumed != token.size() || !std::isfinite(value)) throw bad(); '
            'return value; }'
        ),
    }
    assert not token_census.violations(sources), (
        'Strict numeric admission is a whole-token finite property, not a suggested helper name'
    )


@pytest.mark.parametrize('handoff', ['value.member', 'pointer->member', 'implicit-member'])
def test_census_follows_the_actual_decoded_member_handoff(handoff):
    call = {
        'value.member': 'structure.complete_atom_site_moment()',
        'pointer->member': 'structure->complete_atom_site_moment()',
        'implicit-member': 'complete_atom_site_moment()',
    }[handoff]
    sources = {
        'read.cpp': 'auto read(const EdiBlock& block) { auto v = kept_token_value(block.get("_atom_site_moment.symmform")); structure.symmform = v.value; '  # noqa: E501 — explicit lexical cases and consumer obligations
        + call
        + '; }',
        'model.cpp': 'void Structure::complete_atom_site_moment() { if (symmform == ".") symmform = "Mx,My,Mz"; }',  # noqa: E501 — explicit lexical cases and consumer obligations
    }
    graph = token_census.census(sources)
    nodes, edges, _, _ = graph
    readers = [key for key, row in nodes.items() if row['name'] == 'read']
    consumers = {key for key, row in nodes.items() if row['name'] == 'complete_atom_site_moment'}
    assert all(consumers <= edges[key] for key in readers), (
        'The actual caller hands the decoded field to the member consumer; independent root discovery alone is insufficient'  # noqa: E501 — explicit lexical cases and consumer obligations
    )
    errors = token_census.violations(sources, graph)
    assert any('model.cpp:complete_atom_site_moment:' in error for error in errors), (
        'Decoded magnetic text reaches the actual member consumer and its dot substitute, even with no tag or qualified field in that consumer'  # noqa: E501 — explicit lexical cases and consumer obligations
    )


def test_new_field_inside_an_old_reader_changes_the_consumer_inventory():
    before = {
        'reader.cpp': 'auto read(const EdiBlock& block) { return kept_token_value(block.get("_atom_site_moment.crystalaxis_x")); }'  # noqa: E501 — explicit lexical cases and consumer obligations
    }
    after = {
        'reader.cpp': before['reader.cpp'].replace(
            'return kept_token_value',
            'auto added = block.get("_magnetic_form_factor.ion"); return kept_token_value',
        )
    }
    original = token_census.field_consumers(before)[2]
    changed = token_census.field_consumers(after)[2]
    assert changed != original, 'A new field changes the consumer inventory'
    assert any('_magnetic_form_factor.ion' in tags for tags in changed.values()), (
        'A new field in an already registered reader cannot inherit family-level coverage'
    )


def test_compound_consumer_plan_has_each_field_and_stage():

    tier = 'integration'
    source = (
        Path(__file__).parents[2] / tier / 'cpp/test_magnetic_compound_consumers.cpp'
    ).read_text()
    pairs = set(
        re.findall(r'exercise_compound_consumer\("(\w+)", "([\w-]+)"(?:, -?\d+)?\)', source)
    )
    case_names = set(re.findall(r'TEST_CASE\("([^"\n]+)"\)', source))
    for field in ('symmform', 'k', 'child', 'operation', 'centering', 'ion', 'approximation'):
        expected = {'completion', 'save', 'second-save', 'calculate', 'fit-preparation'}
        if HOME == 'magnetic_pnma':
            expected.add('adapter-transfer')
        if field == 'child':
            expected.add('parent-view')
        assert {f'Magnetic decoded {field} reaches {stage}' for stage in expected} <= case_names, (
            'Each downstream caller is an executable native test case: ' + field
        )
        assert {(field, stage) for stage in expected} <= pairs, (
            'Each typed compound reaches each real downstream consumer after a successful load: '
            + field
        )


def test_all_declared_magnetic_text_members_have_field_witnesses():
    engine = ROOT if HOME == 'c18_t1_magnetic' else (ENGINE_ROOT or ROOT / 'build/crysta-src')
    source = (engine / 'include/crysta/magnetic_types.hpp').read_text()
    required = set()
    for owner in ('MagneticGroupName', 'MagneticTransform', 'ParentSpaceGroup'):
        block = source.split('struct ' + owner + ' {', 1)[1].split('bool empty()', 1)[0]
        required.update(re.findall(r'std::string\s+(\w+)\s*;', block))
    covered = token_census.FIELD_TAGS.keys() | token_census.TYPED_SHORT_FIELDS.keys()
    assert required <= covered, (
        'A newly declared stored magnetic text member requires discovery and field/route witnesses before a reader can use it: '  # noqa: E501 — explicit lexical cases and consumer obligations
        + repr(sorted(required - covered))
    )


def test_a_new_helper_cannot_borrow_a_reviewed_terminal_name():
    for helper in ('bare_is_legal', 'stored_token', 'kept_token_value'):
        prefix = (
            'auto fresh(const EdiBlock& block) { '
            'auto token = kept_token_value(block.get("_atom_site_moment.crystalaxis_x")); '
            'return '
        )
        sources = {
            'reader.cpp': prefix + helper + '(token.value); }',
            'new.cpp': f'double {helper}(const std::string& value) {{ return std::stod(value); }}',
        }
        errors = token_census.violations(sources)
        assert any('new.cpp:' + helper + ':' in error for error in errors), (
            'ADR-0108 reviewed decoder roles are tied to their provider site; a numeric reader cannot borrow a name'  # noqa: E501 — complete C++ escape witness
        )


def test_magnetic_row_schema_fields_cannot_inherit_older_field_coverage():
    engine = ROOT if HOME == 'c18_t1_magnetic' else (ENGINE_ROOT or ROOT / 'build/crysta-src')
    source = (engine / 'include/crysta/model.hpp').read_text()
    exercised = {case.tag for case in token_inputs.cases()}
    for row_type, category in [
        ('AtomSiteMoment', '_atom_site_moment'),
        ('MagneticFormFactor', '_magnetic_form_factor'),
    ]:
        block = source.split('struct RowSchema<' + row_type + '> {', 1)[1]
        values = block.split('static constexpr std::array items{', 1)[1].split('};', 1)[0]
        names = {name for quoted in re.findall(r'"([^"\n]+)"', values) for name in quoted.split()}
        assert {category + '.' + name for name in names} <= exercised, (
            'Every declared magnetic row field requires its own lexical and compound witnesses: '
            + category
        )


def test_compound_numeric_atoms_need_not_consume_the_whole_compound_as_an_integer():
    source = (
        'int magnetic_parent(const EdiBlock& block) { '
        'auto held = kept_token_value(block.get("_space_group_magn.number_BNS")); '
        "std::string text = held.value; auto dot = text.find('.'); "
        'if (dot == std::string::npos || dot == 0 || dot + 1 == text.size() '
        "|| text.find('.', dot + 1) != std::string::npos) throw bad(); "
        'int family, serial; '
        'auto [p, e] = std::from_chars(text.data(), text.data() + dot, family); '
        'if (e != std::errc() || p != text.data() + dot || family < 1) throw bad(); '
        'auto [q, f] = std::from_chars(text.data() + dot + 1, text.data() + text.size(), serial); '
        'if (f != std::errc() || q != text.data() + text.size() || serial < 1) throw bad(); '
        'return family; }'
    )
    assert not token_census.violations({'src/core/cif_import.cpp': source}), (
        'BNS parses as a complete compound; its strict integer atoms may end at the separator'
    )


def test_description_alias_and_numeric_aggregate_consumers_are_discovered():
    spelled = '"_atom_site_moment.symmform \'" "_parent_space_group.name_H-M_alt"'
    assert token_census.TAG.findall(spelled) == [
        '_atom_site_moment.symmform',
        '_parent_space_group.name_H-M_alt',
    ], 'CIF tag identity keeps hyphens and stops before diagnostic prose or quoting'
    sources = {
        'adapter.cpp': 'bool use_description(const MagneticDescription& input) { return input.operations.empty(); }',  # noqa: E501 — complete native alias witness
        'moment.cpp': 'double use_moment(const AtomSiteMoment& input) { return input.moment[0].value(); }',  # noqa: E501 — complete native alias witness
        'radial.cpp': 'double use_radial(const MagneticFormFactor& input) { return input.coefficients[1].value(); }',  # noqa: E501 — complete native alias witness
    }
    _, _, consumers = token_census.field_consumers(sources)
    fields = {tag for tags in consumers.values() for tag in tags}
    assert {
        '_space_group_symop_magn_operation.xyz',
        '_atom_site_moment.crystalaxis_x',
        '_magnetic_form_factor.j4_coefficient',
    } <= fields, (
        'Short description members and native numeric aggregates are decoded-field consumers even without serialized tag names'  # noqa: E501 — complete native alias witness
    )
