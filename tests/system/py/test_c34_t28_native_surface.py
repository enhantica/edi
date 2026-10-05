"""T7: the compiler reads both frozen and current public declarations.

This derives the reference from immutable main headers using the same compiler,
never from a hand-maintained implementation allowlist. Added declarations are
allowed; removing or changing a preserved public declaration is not.
"""

import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from tests.fixtures.c34_t28_compiler import crysta_headers
from tests.fixtures.c34_t28_compiler import standard_headers as _standard_headers

standard_headers = _standard_headers

ROOT = Path(__file__).resolve().parents[3]
REPO = 'edi'
PREFIX = 'core/include'


def compiler_surface(directory, include, standard_headers):
    compiler = shutil.which('clang++')
    assert compiler, ' T7 requires Clang to read both public header contracts'
    source = directory / 'surface.cpp'
    forward = (
        'namespace crysta { template<class T> class KeyedVec; template<class T> class RowVec; }'
        if REPO == 'crysta'
        else 'namespace edi { template<class T> class ItemVec; }'
    )
    source.write_text(
        forward + '\n#include "' + REPO + '/model.hpp"\n'
        '#include <type_traits>\n#include "crysta/column.hpp"\n' + trait_declarations()
    )
    includes = [
        include,
        ROOT / '.pixi/envs/cpp-ci/include',
        ROOT / '.pixi/envs/default/include',
        crysta_headers(),
        ROOT / '.pixi/envs/cpp-ci/include/eigen3',
        ROOT / '.pixi/envs/default/include/eigen3',
        Path('/usr/include/eigen3'),
    ]
    command = [
        compiler,
        '-std=c++20',
        '-fsyntax-only',
        '-include-pch',
        str(standard_headers),
        '-Xclang',
        '-ast-dump',
        '-Xclang',
        '-ast-dump-filter=' + REPO,
    ]
    for path in includes:
        command += ['-I', str(path)]
    result = subprocess.run(
        [*command, str(source)], capture_output=True, text=True, check=False, timeout=25
    )
    assert result.returncode == 0, (
        ' T7 both complete header graphs and the original class forward declarations '
        'must compile: ' + result.stderr
    )
    return public_declarations(result.stdout)


def public_declarations(text):
    declarations, scopes = set(), []
    active = False
    for line in text.splitlines():
        if line.startswith('Dumping '):
            active = line.startswith('Dumping ' + REPO + ':')
            scopes = []
            continue
        if not active:
            continue
        match = re.match(r'([| `-]*)(.*)', line)
        depth, entry = len(match[1]) // 2, match[2]
        while scopes and scopes[-1]['depth'] >= depth:
            scopes.pop()
        namespace = re.match(
            r'NamespaceDecl .+\b([A-Za-z_]\w+)\s*$',
            entry.removesuffix(' nested').removesuffix(' inline'),
        )
        record = re.match(r'CXXRecordDecl .+\b(class|struct) (\w+) definition$', entry)
        if namespace:
            scopes.append({'depth': depth, 'name': namespace[1], 'access': None})
        elif record:
            scopes.append({
                'depth': depth,
                'name': record[2],
                'access': 'private' if record[1] == 'class' else 'public',
            })
        elif scopes and scopes[-1]['access'] is not None and scopes[-1]['depth'] == depth - 1:
            record_member(declarations, scopes, entry)
    return declarations


def record_member(declarations, scopes, entry):
    owner = '::'.join(scope['name'] for scope in scopes if scope['name'])
    if entry.startswith('AccessSpecDecl '):
        scopes[-1]['access'] = entry.split()[-1]
    elif entry.startswith('public '):
        declarations.add((owner, '<base>', 'base', re.findall(r"'([^']+)'", entry)[0]))
    elif scopes[-1]['access'] == 'public':
        if entry.startswith(('FunctionTemplateDecl ', 'TypeAliasTemplateDecl ', 'FriendDecl ')):
            scopes.append({'depth': scopes[-1]['depth'] + 1, 'name': '', 'access': 'public'})
            return
        declaration = public_member(entry)
        if declaration:
            declarations.add((owner, *declaration))


def public_member(entry):
    if ' implicit ' in entry:
        return None
    kind = entry.split(' ', 1)[0]
    if kind not in {
        'FieldDecl',
        'FunctionDecl',
        'CXXMethodDecl',
        'CXXConstructorDecl',
        'CXXDestructorDecl',
        'CXXConversionDecl',
        'TypeAliasDecl',
        'TypedefDecl',
        'VarDecl',
    }:
        return None
    types = re.findall(r"'([^']+)'", entry)
    if not types:
        return None
    prefix = entry.split("'", 1)[0]
    name = (
        prefix[prefix.index('operator') :].strip() if 'operator' in prefix else prefix.split()[-1]
    )
    signature = types[0].replace(' noexcept(false)', '')
    # An uninstantiated defaulted template constructor has an unevaluated
    # exception specification. Concrete trait fields below test its real result.
    if kind == 'CXXConstructorDecl' and '<' in name:
        signature = signature.split(' noexcept', 1)[0]
    if ' delete' in entry:
        signature += ' =delete'
    return name, kind, signature


TRAIT_TYPES = [
    'Parameter',
    'ItemKey',
    'detail::Written<double>',
    'detail::Written<int>',
    'detail::Written<bool>',
    'detail::Written<std::optional<double>>',
    'detail::Written<std::vector<double>>',
    'detail::Written<std::optional<std::vector<double>>>',
    'detail::Written<std::vector<std::pair<double, double>>>',
    'detail::Written<std::map<std::string, double>>',
    'detail::Written<std::vector<std::string>>',
    'detail::Written<std::vector<std::vector<std::string>>>',
    'detail::WrittenText',
    'ComputedColumn<double>',
    'ComputedColumn<std::string>',
    'ItemVec<AtomSite>',
    'ItemVec<Structure>',
    'ItemVec<BraggPdExperiment>',
    'ItemVec<PrefOrient>',
    'ItemVec<LineSegment>',
    'ItemVec<SequentialExtractRule>',
    'PdDataBase',
    'PdCwlData',
    'PdTofData',
    'CarriedLoop',
    'SequentialExtractRule',
    'detail::KeyedBase',
    'SpaceGroup',
    'Cell',
    'PeakBase',
    'InstrumentBase',
    'AbsorptionBase',
    'LinkedStructure',
    'ExperimentType',
    'ProjectMetadata',
    'SequentialFitConfig',
    'ViewWindow',
    'CartnTransform',
    'StructureGeometry',
]


def trait_declarations():
    traits = [
        'is_default_constructible',
        'is_nothrow_default_constructible',
        'is_copy_constructible',
        'is_move_constructible',
        'is_copy_assignable',
        'is_move_assignable',
        'is_destructible',
        'is_nothrow_copy_constructible',
        'is_nothrow_move_constructible',
        'is_nothrow_copy_assignable',
        'is_nothrow_move_assignable',
        'is_nothrow_swappable',
    ]
    # I20/F21: constructor traits belong to the actual exposed owners as well
    # as their wrappers; T8's member exception grants no trait exemption.
    fields = []
    for index, name in enumerate(TRAIT_TYPES):
        bits = ' + '.join(
            f'({1 << bit} * std::{trait}_v<{REPO}::{name}>)' for bit, trait in enumerate(traits)
        )
        fields.append(f'char traits_{index}[1 + {bits}];')
    return 'namespace ' + REPO + ' { struct C34ContractTraits { ' + ' '.join(fields) + ' }; }'


def frozen_headers(directory):
    reference = ROOT / 'tests/fixtures/e04_t12_public_release/history'
    manifest = json.loads((reference / 'manifest.json').read_text())['native']
    assert manifest, 'the retained public header inventory must not be empty'
    with zipfile.ZipFile(reference / 'native.zip') as archive:
        assert set(archive.namelist()) == set(manifest), (
            'every independent reference header must be present'
        )
        for name, digest in manifest.items():
            data = archive.read(name)
            assert hashlib.sha256(data).hexdigest() == digest, (
                'every independent header must retain its pinned bytes'
            )
            target = directory / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    return directory / PREFIX


def test_every_preserved_public_declaration_keeps_its_compiler_type(tmp_path, standard_headers):
    baseline = compiler_surface(tmp_path, frozen_headers(tmp_path), standard_headers)
    actual = compiler_surface(tmp_path, ROOT / PREFIX, standard_headers)
    assert baseline, ' T7 the compiler must expose a nonempty frozen public API'
    allowed = allowed_changes()
    transitions, _ = multiphase_declaration_transition()
    assert transitions <= baseline, (
        'The multiphase migration must retain its immutable prior declarations'
    )
    require_multiphase_declarations(actual)
    missing = sorted(
        row for row in baseline - actual if row[:2] not in allowed and row not in transitions
    )
    assert not missing, (
        ' I20/T7 every preserved field, base, alias, overload, reference return and '
        'noexcept signature must retain its frozen compiler type: ' + repr(missing)
    )


def allowed_changes():
    # Exactly T8; public shape changes outside these names remain forbidden.
    return {
        ('edi::Parameter', 'uncertainty'),
        ('edi::Parameter', 'free'),
        ('edi::Parameter', 'start_value'),
        ('edi::Parameter', 'start_uncertainty'),
        ('edi::AtomSite', 'wyckoff_letter'),
        ('edi::LineSegment', 'position'),
        ('edi::PrefOrient', 'index_h'),
        ('edi::PrefOrient', 'index_k'),
        ('edi::PrefOrient', 'index_l'),
        ('edi::SequentialExtractRule', 'target'),
        ('edi::SequentialExtractRule', 'pattern'),
        ('edi::SequentialExtractRule', 'required'),
        ('edi::PdDataBase', 'intensity_meas'),
        ('edi::PdDataBase', 'intensity_meas_su'),
        ('edi::PdDataBase', 'two_theta'),
        ('edi::PdDataBase', 'time_of_flight'),
        ('edi::PdDataBase', 'write_axis'),
        ('edi::PdDataBase', 'write_column'),
        ('edi::Structure', 'scattering_lengths_fm'),
        ('edi::ExperimentBase', 'excluded_regions'),
        ('edi::CarriedLoop', 'columns'),
        ('edi::CarriedLoop', 'rows'),
    }


MUTATIONS = [
    (
        'core/include/edi/model.hpp',
        'const std::vector<double>& axis() const',
        'std::vector<double> axis() const',
    ),
    (
        'core/include/edi/model.hpp',
        'bool is_attached() const noexcept',
        'bool is_attached() const',
    ),
]


@pytest.mark.parametrize(
    ('header', 'before', 'after'), MUTATIONS, ids=['axis-by-value', 'attachment-may-throw']
)
def test_native_contract_detects_reference_and_exception_drift(
    tmp_path, header, before, after, standard_headers
):
    include = frozen_headers(tmp_path)
    expected = compiler_surface(tmp_path, include, standard_headers)
    path = tmp_path / header
    text = path.read_text()
    assert before in text, ' T7 the mutation must reach its frozen declaration'
    path.write_text(text.replace(before, after, 1))
    actual = compiler_surface(tmp_path, include, standard_headers)
    missing = expected - actual
    assert missing, ' T7 a compiling change to a reference return or noexcept must be detected'
    assert any(row[:2] not in allowed_changes() for row in missing), (
        ' T8 the member-type exception cannot hide a preserved native contract change'
    )


def multiphase_declaration_transition():
    # Exact old -> new declarations, never a blanket member-name exemption.
    # The constructor mask is a labelled post-feature REGRESSION PIN measured
    # by the existing independent Clang witness on the keyed-row representation.
    return {
        ('edi::ExperimentBase', 'linked_structure', 'FieldDecl', 'LinkedStructure'),
        ('edi::LinkedStructure', 'structure_id', 'FieldDecl', 'std::string'),
        ('edi::C34ContractTraits', 'traits_32', 'FieldDecl', 'char[3454]'),
    }, {
        ('edi::ExperimentBase', 'linked_structure', 'CXXMethodDecl', 'LinkedStructure &()'),
        (
            'edi::ExperimentBase',
            'linked_structure',
            'CXXMethodDecl',
            'const LinkedStructure &() const',
        ),
        ('edi::ExperimentBase', 'linked_structures', 'FieldDecl', 'ItemVec<LinkedStructure>'),
        ('edi::LinkedStructure', 'structure_id', 'FieldDecl', 'ItemKey'),
        ('edi::C34ContractTraits', 'traits_32', 'FieldDecl', 'char[126]'),
    }


def require_multiphase_declarations(actual):
    _, replacements = multiphase_declaration_transition()
    assert replacements <= actual, (
        'The multiphase migration must provide every exact keyed-row type, reference overload '
        'and labelled constructor-trait regression pin: ' + repr(sorted(replacements - actual))
    )


@pytest.mark.parametrize(
    'damage', ['missing-row', 'mutable-value', 'const-value', 'key-type', 'traits']
)
def test_multiphase_transition_never_exempts_its_replacement_contract(damage):
    _, declarations = multiphase_declaration_transition()
    require_multiphase_declarations(declarations)
    changed = set(declarations)
    index = {
        'missing-row': ('linked_structures', 'ItemVec<LinkedStructure>'),
        'mutable-value': ('linked_structure', 'LinkedStructure &()'),
        'const-value': ('linked_structure', 'const LinkedStructure &() const'),
        'key-type': ('structure_id', 'ItemKey'),
        'traits': ('traits_32', 'char[126]'),
    }
    member, signature = index[damage]
    original = next(row for row in changed if row[1] == member and row[3] == signature)
    changed.remove(original)
    if damage != 'missing-row':
        changed.add((
            *original[:3],
            signature.replace('&', '') if '&' in signature else 'wrong-type',
        ))
    with pytest.raises(AssertionError, match='every exact keyed-row type'):
        require_multiphase_declarations(changed)
