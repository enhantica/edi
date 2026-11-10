#!/usr/bin/env python3
"""Freeze the  vocabulary oracle, and emit every table derived from it.

Two halves, each rejected once in an earlier form and rebuilt:

* **Upstream** — every public `@property` under every `categories/<name>/` directory across all of
  `src/easydiffraction/**` at the pin, plus the selectors a category inherits from a cross-cutting
  base. Never a hand-picked file list: a gate comparing a document against a subset oracle proves
  itself complete while being unable to see an omission outside the subset (review-4 F1).
* **edi presence** — category-qualified introspection of the BUILT MODULE's object graph. Never a
  text match over `bindings.cpp`: an unqualified token test discards the category, so a leaf
  belonging to another edi type marks the attribute present under every category sharing it
  (review-5 F1).

Three output modes, because every table these artifacts publish must be derivable rather than
described — a document that says it is generated while no mode generates it drifts back to manual
synchronisation (review-6 F1):

* default          -> `oracle.json`, the frozen reference corpus
* ``--markdown``   -> edi parity table (c): one row per absent upstream name, with its note
* ``--canonical-table`` -> the canonical vocabulary table body

Notes carry the same discipline: a note may not spell out a sibling the rows report as present,
because a typed presence claim drifts the moment the classifier moves (review-6 F2). Use
``{present}`` for the derived list, or the checked ``{present:<name>}`` for one cross-reference.
"""

from __future__ import annotations

import argparse
import ast
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

# The oracle pin IS the declared master pin ( P4, invariant I1: every committed foreign
# anchor is reachable from that repo's default branch and survives a master-only clone). Until
# 2026-08-28 the oracle was frozen at a branch-only commit of `origin/fullprof-occupancy-notation`
# that master cannot reach — measured name-equivalent to master (the two trees differed only by a
# commented-out log line in `experiment/item/base.py`; the full scan yields the identical qualified
# SET at both — 40 categories / 306 attributes, zero symmetric difference over
# `<category>.<attribute>`, re-measured 2026-08-22 and again at the re-anchor), so the oracle's
# CONTENT is unchanged by the move; only its provenance became verifiable.
PIN = '0ffba46f4b501066a73e77f00fa29fa13519b417'
MASTER_PIN = PIN

SCAN_ROOT = 'src/easydiffraction/'
CATEGORY_RE = re.compile(r'categories/([a-z_0-9]+)/')

# edi presence is decided by introspecting the BUILT MODULE'S OBJECT GRAPH, category by category.
#
# It used to be decided by collecting every quoted lowercase token in `bindings.cpp` and asking
# whether the unqualified attribute occurred anywhere in that set. That test discards the category,
# so any leaf token belonging to some other edi type marked the attribute present under EVERY
# upstream category sharing the leaf: `aliases.id`, `atom_site_aniso.id`, `constraints.id`,
# `refln.id`, `space_group_wyckoff.id`, `metadata.name`, `software.name` and
# `excluded_regions.start`
# were all called present though edi binds none of those categories, and they therefore fell into
# neither parity table. Review-5 finding 1 rejected it; review-4 finding 1 had already rejected the
# same instrument for a different reason (a narrowed universe). What failed twice is not the tuning
# but the approach: deriving a category-qualified surface by text-matching C++ source.
#
# edi is an importable module and the gate already builds it, so the surface is read from the real
# objects instead. Each upstream category names the edi accessor that exposes it; the attributes
# come from the live element object, so `(category, attribute)` membership is qualified BY
# CONSTRUCTION and there is no heuristic left to be wrong about. The map below is a declaration,
# not a guess, and `_check_surface` proves it against edi's own two category-qualified records —
# `parameter_specs()` and `covered_tag_categories()` — so a category edi really exposes but that
# this table forgets fails generation rather than silently becoming 'absent'.
EDI_CATEGORY_SURFACE = {
    'absorption': ('Experiment', 'absorption'),
    'atom_sites': ('Structure', 'atom_sites'),
    'background': ('Experiment', 'background'),
    'cell': ('Structure', 'cell'),
    'data': ('Experiment', 'data'),
    'excluded_regions': ('Experiment', 'excluded_regions'),
    'experiment_type': ('Experiment', 'experiment_type'),
    'fit_result': ('Experiment', None),  # a returned type, resolved via EDI_RESULT_TYPES
    'fitting_mode': ('Analysis', 'fitting_mode'),
    'instrument': ('Experiment', 'instrument'),
    'linked_structure': ('Experiment', 'linked_structure'),
    'peak': ('Experiment', 'peak'),
    'space_group': ('Structure', 'space_group'),
}

# Categories edi exposes as a returned value rather than a container attribute.
EDI_RESULT_TYPES = {'fit_result': 'FitResultBase'}

# List-valued accessors need one element before the element type can be observed rather than
# assumed. Assignment, not append: the bindings return a converted copy, so appending to the
# read-back list does not reach the model.
EDI_LIST_PROBES = {
    'atom_sites': ('Structure', 'atom_sites', 'AtomSite'),
    'background': ('Experiment', 'background', 'LineSegment'),
    'excluded_regions': ('Experiment', 'excluded_regions', None),  # plain (start, end) pairs
}

# A category whose live object carries no named public attribute. Declared, so that an
# introspection failure cannot quietly present itself as "edi implements none of this".
EDI_EMPTY_SURFACES = {'excluded_regions', 'fitting_mode'}

# edi's spec table spells the atom-site category singular; upstream's directory is plural.
EDI_SPEC_CATEGORY_ALIASES = {'atom_site': 'atom_sites'}

ENUM_SOURCE = 'src/easydiffraction/datablocks/experiment/item/enums.py'
ENUM_CLASSES = {
    'SampleFormEnum',
    'BeamModeEnum',
    'RadiationProbeEnum',
    'ScatteringTypeEnum',
    'PeakProfileTypeEnum',
}

DESCRIPTOR_CALLS = {
    'EnumDescriptor',
    'IntegerDescriptor',
    'NumericDescriptor',
    'Parameter',
    'StringDescriptor',
}

# The implemented  intersection, keyed by upstream's own category directory name. This is
# NOT the presence oracle — `edi_present` is, derived from the bindings surface. This set is the
# tripwire: every name in it must also be detected present, so a rename that silently drops a
# binding fails generation instead of quietly shrinking the parity table.
TARGET_IMPLEMENTED = {
    'atom_sites': {
        'adp_iso',
        'fract_x',
        'fract_y',
        'fract_z',
        'id',
        'occupancy',
        'type_symbol',
        'wyckoff_letter',
    },
    'background': {'intensity', 'position'},
    'cell': {
        'angle_alpha',
        'angle_beta',
        'angle_gamma',
        'length_a',
        'length_b',
        'length_c',
    },
    'data': {'intensity_meas', 'intensity_meas_su', 'time_of_flight', 'two_theta'},
    # `excluded_regions` records NEITHER element. edi exposes excluded regions as a container of
    # plain `(start, end)` tuples, so neither is a named attribute — the qualified surface finds
    # nothing on the element, and the old token test's `start` was an unrelated `"start"` matching
    # by coincidence, exactly the category-blindness review-5 rejected. The shape divergence is
    # table (a)'s row and table (c)'s note points there.
    'experiment_type': {'beam_mode', 'radiation_probe', 'sample_form', 'scattering_type'},
    'instrument': {
        'calib_d_to_tof_linear',
        'calib_d_to_tof_offset',
        'calib_d_to_tof_quadratic',
        'calib_twotheta_offset',
        'setup_twotheta_bank',
        'setup_wavelength',
    },
    # Upstream carries both a `linked_structure` category and a `linked_structures` collection
    # category with the same two names; edi exposes the singular one only, so the plural category's
    # names are absent under that spelling and say so in table (c).
    'linked_structure': {'scale', 'structure_id'},
    'peak': {
        'broad_gauss_sigma_0',
        'broad_gauss_sigma_1',
        'broad_gauss_sigma_2',
        'broad_gauss_size',
        'broad_gauss_strain',
        'broad_gauss_u',
        'broad_gauss_v',
        'broad_gauss_w',
        'broad_lorentz_gamma_0',
        'broad_lorentz_gamma_1',
        'broad_lorentz_gamma_2',
        'broad_lorentz_size',
        'broad_lorentz_strain',
        'broad_lorentz_x',
        'broad_lorentz_y',
        'cutoff_fwhm',
        'decay_beta_0',
        'decay_beta_1',
        'rise_alpha_0',
        'rise_alpha_1',
    },
    'space_group': {'coord_system_code', 'name_h_m'},
}

# ---- absence rationale -------------------------------------------------------------------------
# Every absent upstream name gets a row in parity table (c), so each needs a note. A note is either
# a per-name override (the curated rows, and every name where edi implements the quantity under a
# different spelling) or the category default. Both are data here so the document is generated, not
# hand-maintained — the prose "surface families" paragraph that used to stand in for rows is what
# review-4 finding 1 rejected as failing the one-row-per-name contract.

ANALYSIS_FACADE = (
    'the `analysis.*` surface, arriving incrementally behind `project.analysis` (ruled C) — '
    'the facade exists, this category is not yet ported'
)

CATEGORY_ABSENCE_NOTES = {
    'absorption': (
        "upstream's CW cylinder absorption surface; edi's TOF `abscor1`/`abscor2` pair is a "
        'declared divergence — see table (a)'
    ),
    'aliases': ANALYSIS_FACADE,
    'atom_site_aniso': (
        'anisotropic ADP storage, not modelled — edi stores isotropic B only and refuses a '
        'declared anisotropic `_atom_site.adp_type` at load'
    ),
    'atom_sites': 'structure feature edi has not implemented',
    'background': (
        'Chebyshev-polynomial background implementation (`background/chebyshev.py` at the pin); '
        'edi implements line-segment backgrounds only'
    ),
    'calculator': ANALYSIS_FACADE,
    'constraints': ANALYSIS_FACADE,
    'data': 'calculated-pattern or PDF column edi does not persist',
    'data_range': (
        'upstream range/step metadata; edi derives its range from the measured pattern rather '
        'than storing it'
    ),
    'diffrn': 'ambient-condition metadata, not modelled',
    'excluded_regions': (
        'see table (a): edi keeps excluded regions as plain `(start, end)` pairs, so neither '
        'element is a named attribute on an item object'
    ),
    'extinction': 'extinction correction, not implemented',
    'fit_parameter_correlations': ANALYSIS_FACADE,
    'fit_parameters': ANALYSIS_FACADE,
    # `{present}` is filled from the computed present set for this category. A note that TYPED the
    # list drifted the moment `fit_result.message` moved to absent, leaving every other
    # `fit_result.*` row asserting edi exposes a name the row beside it denies (review-6 F2).
    'fit_result': (
        'richer fit statistics than edi reports — edi exposes {present}; the rest arrive with '
        'the `analysis.*` surface (ruled C)'
    ),
    'fitting_mode': (
        "upstream's switchable fitting-mode category; edi's `analysis.fitting_mode` is a plain "
        'string selector with no category object behind it'
    ),
    'geom': 'geometry/bond-distance analysis, not implemented',
    'linked_structures': (
        "upstream's linked-structure COLLECTION category; the parity verdict for this quantity is "
        'carried by the singular `linked_structure` rows, so these names are absent under this '
        'spelling'
    ),
    'instrument': 'CW instrument feature edi has not implemented',
    'joint_fit': ANALYSIS_FACADE,
    'metadata': 'project metadata edi does not record',
    'minimizer': ANALYSIS_FACADE,
    'peak': 'peak-profile family edi has not implemented',
    'pref_orient': 'preferred-orientation correction, not implemented',
    'refln': 'reflection column edi does not expose on its read-out',
    'rendering_plot': 'display/rendering subsystem, not ported',
    'rendering_structure': 'display/rendering subsystem, not ported',
    'rendering_table': 'display/rendering subsystem, not ported',
    'report': 'report renderer edi does not provide',
    'sequential_fit': 'sequential/batch fitting over a data directory, not implemented',
    'sequential_fit_extract': 'sequential/batch fitting over a data directory, not implemented',
    'software': 'software provenance field edi does not record',
    'space_group': 'space-group feature edi has not implemented',
    'space_group_wyckoff': (
        'upstream per-Wyckoff-position table; edi carries only `_atom_site.wyckoff_letter` on '
        'the site itself'
    ),
    'structure_style': 'display/rendering subsystem, not ported',
    'structure_view': 'display/rendering subsystem, not ported',
    'verbosity': (
        "upstream's verbosity category; edi's `Verbosity` is the  output-contract type, "
        'not this category — see table (b)'
    ),
}

BEBA_NOTE = 'reserved rung 2 (Berar-Baldinozzi, ) — the token is refused by name'
FCJ_NOTE = 'reserved rung 1 (Finger-Cox-Jephcoat, ) — the token is refused by name'
AS_CIF_NOTE = "upstream's per-category CIF accessor; edi serialises through its own `.edi` writer"

NAME_ABSENCE_NOTES = {
    # Curated rows carried forward from the reviewed document.
    'atom_sites.adp_type': 'see table (a): interpreted at load, no stored field yet',
    'atom_sites.multiplicity': 'tolerated on read, not modelled',
    'background.id': 'row ordinal, read past',
    'data.id': 'row ordinal, read past',
    'excluded_regions.id': 'row ordinal, read past',
    'peak.asym_beba_a0': BEBA_NOTE,
    'peak.asym_beba_a1': BEBA_NOTE,
    'peak.asym_beba_b0': BEBA_NOTE,
    'peak.asym_beba_b1': BEBA_NOTE,
    'peak.asym_fcj_1': FCJ_NOTE,
    'peak.asym_fcj_2': FCJ_NOTE,
    'peak.dexp_decay_beta_00': 'double-Jorgensen-von-Dreele profile, not implemented',
    'peak.dexp_decay_beta_01': 'double-Jorgensen-von-Dreele profile, not implemented',
    'peak.dexp_decay_beta_10': 'double-Jorgensen-von-Dreele profile, not implemented',
    'peak.dexp_rise_alpha_1': 'double-Jorgensen-von-Dreele profile, not implemented',
    'peak.dexp_rise_alpha_2': 'double-Jorgensen-von-Dreele profile, not implemented',
    'peak.dexp_switch_r_01': 'double-Jorgensen-von-Dreele profile, not implemented',
    'peak.dexp_switch_r_02': 'double-Jorgensen-von-Dreele profile, not implemented',
    'peak.dexp_switch_r_03': 'double-Jorgensen-von-Dreele profile, not implemented',
    # Names the widened scan newly exposes where edi implements the quantity under another
    # spelling. Per this document's own rule those are divergences, not plain absences.
    'atom_sites.adp_iso_as_b': (
        "upstream's B-valued view of the isotropic ADP; edi stores it as B natively, so edi's "
        '{present:adp_iso} already IS this value — see table (a)'
    ),
    'joint_fit.weight': 'edi spells this `experiment.dataset_weight` — see table (a)',
    'fit_result.message': (
        'edi reports terminal state as the `FitOutcome.status` enum plus `FitStatus`, not a '
        'free-text message'
    ),
    'excluded_regions.start': (
        'see table (a): edi keeps excluded regions as plain `(start, end)` pairs, so neither '
        'element is a named attribute'
    ),
    'excluded_regions.end': (
        'see table (a): edi keeps excluded regions as plain `(start, end)` pairs, so neither '
        'element is a named attribute'
    ),
    'background.type': (
        'the `_background.type` tag is read at load, but edi exposes no `type` attribute on a '
        'background point'
    ),
    'data.x': (
        'see table (a): edi names the axis by mode and reads it through `MeasuredPattern.axis`'
    ),
    'data.x_descriptor': (
        'see table (a): edi names the axis by mode, so no descriptor selects between axes'
    ),
    'data.unfiltered_x': 'pre-exclusion axis copy edi does not retain',
    'peak.broad_q': 'PDF/pair-distribution damping-broadening term, not implemented',
    'peak.cutoff_q': 'PDF/pair-distribution damping-broadening term, not implemented',
    'peak.damp_q': 'PDF/pair-distribution damping term, not implemented',
    'peak.damp_particle_diameter': 'PDF/pair-distribution damping term, not implemented',
    'peak.sharp_delta_1': 'PDF/pair-distribution peak-sharpening term, not implemented',
    'peak.sharp_delta_2': 'PDF/pair-distribution peak-sharpening term, not implemented',
    'space_group.crystal_system': (
        'derived classification edi does not store — the space-group name and coordinate-system '
        'code carry it'
    ),
    'report.project': None,  # present; placeholder guard, never emitted
}
NAME_ABSENCE_NOTES = {k: v for k, v in NAME_ABSENCE_NOTES.items() if v is not None}


# ---- upstream scan -----------------------------------------------------------------------------


def _git(upstream: Path, *args: str) -> str:
    completed = subprocess.run(
        ['git', '-C', str(upstream), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.stderr.strip() or f'git {" ".join(args)} failed')
    return completed.stdout


def _all_python_files(upstream: Path) -> list[str]:
    listing = _git(upstream, 'ls-tree', '-r', '--name-only', PIN, SCAN_ROOT).split()
    return sorted(path for path in listing if path.endswith('.py'))


def _category_files(upstream: Path) -> list[tuple[str, str]]:
    """Every `.py` file under a `categories/<name>/` directory at the pin, with its category."""
    listing = _git(upstream, 'ls-tree', '-r', '--name-only', PIN, SCAN_ROOT).split()
    found: list[tuple[str, str]] = []
    for path in listing:
        if not path.endswith('.py'):
            continue
        match = CATEGORY_RE.search(path[len(SCAN_ROOT) :])
        if match is not None:
            found.append((match.group(1), path))
    if not found:
        raise SystemExit(f'no category sources found under {SCAN_ROOT} at {PIN}')
    return sorted(found)


def _public_properties(tree: ast.AST) -> set[str]:
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith('_')
        and any(
            isinstance(decorator, ast.Name) and decorator.id == 'property'
            for decorator in node.decorator_list
        )
    }


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ''


def _literal_list(call: ast.Call, keyword: str) -> list[str]:
    value = next((item.value for item in call.keywords if item.arg == keyword), None)
    if not isinstance(value, (ast.List, ast.Tuple)):
        return []
    return [item.value for item in value.elts if isinstance(item, ast.Constant)]


def _descriptor_rows(
    tree: ast.AST, properties: set[str], surface: str, path: str
) -> tuple[list[dict[str, object]], list[str]]:
    """Public descriptor rows for one source, plus the internal descriptors it declares.

    A descriptor member whose attribute has no public property ANYWHERE upstream is internal
    (`metadata._project_id` is one) — it carries no user-typed name, so it is not part of the
    vocabulary parity is about. Those are returned separately rather than dropped silently, so the
    set cannot grow unnoticed; a descriptor that *is* exposed must still resolve to a property,
    which is the check that caught the `name=`-versus-attribute defect.
    """
    rows: list[dict[str, object]] = []
    internal: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign):
            target, call = node.target, node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, call = node.targets[0], node.value
        else:
            continue
        if not isinstance(call, ast.Call) or _call_name(call) not in DESCRIPTOR_CALLS:
            continue
        if not (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == 'self'
            and target.attr.startswith('_')
        ):
            continue
        attribute = target.attr.removeprefix('_')
        if attribute not in properties:
            internal.append(f'{surface}.{attribute}')
            continue
        name_node = next((item.value for item in call.keywords if item.arg == 'name'), None)
        if not isinstance(name_node, ast.Constant) or not isinstance(name_node.value, str):
            continue
        tags_node = next((item.value for item in call.keywords if item.arg == 'tags'), None)
        tags = (
            tags_node
            if isinstance(tags_node, ast.Call) and _call_name(tags_node) == 'TagSpec'
            else None
        )
        rows.append({
            'surface': surface,
            'attribute': attribute,
            'internal_name': name_node.value,
            'edi_names': _literal_list(tags, 'edi_names') if tags is not None else [],
            'cif_names': _literal_list(tags, 'cif_names') if tags is not None else [],
            'source': path,
        })
    return rows, internal


def _enum_rows(source: str) -> dict[str, dict[str, str]]:
    tree = ast.parse(source, filename=ENUM_SOURCE)
    rows: dict[str, dict[str, str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name not in ENUM_CLASSES:
            continue
        members: dict[str, str] = {}
        for statement in node.body:
            if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
                continue
            target = statement.targets[0]
            if (
                isinstance(target, ast.Name)
                and isinstance(statement.value, ast.Constant)
                and isinstance(statement.value.value, str)
            ):
                members[target.id] = statement.value.value
        rows[node.name] = members
    return rows


def _public_attributes(obj: object) -> set[str]:
    """Public, non-callable attribute names on a live edi object."""
    names = set()
    for name in dir(obj):
        if name.startswith('_'):
            continue
        try:
            value = getattr(obj, name)
        except Exception:  # noqa: BLE001, S112 - an accessor that raises exposes no attribute
            continue
        if callable(value):
            continue
        names.add(name)
    return names


def _edi_surface(edi: object) -> dict[str, set[str]]:
    """edi's public surface, keyed by upstream category — read from live objects.

    The category is carried through the membership test rather than discarded, which is the whole
    point: `refln.id` and `atom_sites.id` are different questions, and a flat set of leaf tokens
    cannot tell them apart.

     (the structural adoption): members are homed on the CONCRETE leaf views, so a single
    default experiment sees only its own leaf's members. Every 'Experiment'-owned category is
    therefore introspected across the leaf-covering variants (a TOF Jorgensen-von Dreele and a CW
    pseudo-Voigt experiment) and unioned, and the data category unions both data leaves.
    """

    def _experiment_variants():
        return [
            edi.ExperimentFactory.from_scratch(peak_type='tof-jorgensen-von-dreele'),
            edi.ExperimentFactory.from_scratch(
                peak_type='cwl-' + 'pseudo-voigt', beam_mode='constant wavelength'
            ),
        ]

    owners = {
        'Structure': lambda: [edi.Structure()],
        'Experiment': _experiment_variants,
        'Analysis': lambda: [edi.Project().analysis],
    }
    surface: dict[str, set[str]] = {}
    for category, (owner_name, accessor) in sorted(EDI_CATEGORY_SURFACE.items()):
        if category in EDI_RESULT_TYPES:
            elements = [getattr(edi, EDI_RESULT_TYPES[category])]
        elif category == 'data':
            elements = [
                edi.PdTofData(time_of_flight=[1.0], intensity_meas=[1.0], intensity_meas_su=[1.0]),
                edi.PdCwlData(two_theta=[1.0], intensity_meas=[1.0], intensity_meas_su=[1.0]),
            ]
        else:
            elements = []
            for owner in owners[owner_name]():
                if category in EDI_LIST_PROBES:
                    _owner_name, probe_accessor, element_type = EDI_LIST_PROBES[category]
                    probe = (
                        [(1.0, 2.0)] if element_type is None else [getattr(edi, element_type)()]
                    )
                    setattr(owner, probe_accessor, probe)
                value = getattr(owner, accessor)
                if isinstance(value, list):
                    if not value:
                        raise SystemExit(f'{category}: probe produced no element to introspect')
                    elements.append(value[0])
                elif value is not None:
                    elements.append(value)
        names: set[str] = set()
        for element in elements:
            if not isinstance(element, (str, bytes, int, float, tuple)):
                names |= _public_attributes(element)
        if not names and category not in EDI_EMPTY_SURFACES:
            raise SystemExit(
                f'{category}: introspection produced no attributes and the category is not '
                f'declared in EDI_EMPTY_SURFACES — refusing to report it as wholly unimplemented'
            )
        surface[category] = names
    return surface


def _check_surface(
    _edi: object, surface: dict[str, set[str]], universe: dict[str, set[str]]
) -> None:
    """Prove the category map against the upstream universe. Fail closed.

    : the two edi-side category-qualified records this check also proved the map
    against — ``parameter_specs()`` and ``covered_tag_categories()`` — were REMOVED from the
    public surface by the necessity sweep (removal records in edi ``data/python-surface.json``:
    no consumer by the ruled definition, which excludes ``tests/**`` — I4 — and this generator
    lives under ``tests/fixtures``). The map keeps its upstream-universe proof and its
    by-construction membership qualification; the edi-side cross-checks retire with their
    records rather than resurrecting removed names.
    """
    unknown = sorted(set(surface) - set(universe))
    if unknown:
        raise SystemExit(
            'mapped categories that are not upstream categories at this pin: ' + ', '.join(unknown)
        )


PRESENT_PLACEHOLDER = '{present}'  # the derived-list token notes interpolate; see _absence_note


def _render_present(names: list[str]) -> str:
    """`a`, `b` and `c` — the attributes edi actually exposes in one category."""
    ticked = [f'`{name}`' for name in names]
    if not ticked:
        return 'nothing in this category'
    if len(ticked) == 1:
        return ticked[0]
    return ', '.join(ticked[:-1]) + ' and ' + ticked[-1]


def _check_note_templates(present_by_category: dict[str, list[str]]) -> None:
    """A note may not NAME a present sibling attribute literally; it must derive the list.

    Review-6 F2: a note asserting which attributes edi exposes is a claim about the same data the
    rows carry, so typing it lets the two disagree the moment the classifier moves — `fit_result`'s
    note kept naming `message` after `fit_result.message` became absent, so every other
    `fit_result.*` row asserted what the row beside it denied. Deriving the list fixes that
    instance; this check fixes the class, by refusing any TEMPLATE that spells out a sibling the
    rows report as present. `{present}` is the supported way to say it, and it cannot drift.

    Deliberately narrow. It does not object to a negative claim ("a feature edi has not
    implemented"), to a cross-category reference, or to naming an ABSENT sibling — none of those
    can contradict the presence data. Templates are checked before interpolation, so a note that
    already derives its list does not trip on its own output.
    """
    identifier = re.compile(r'`([a-z_][a-z_0-9]*)`')  # bare backticked names only
    templates = [(category, category, note) for category, note in CATEGORY_ABSENCE_NOTES.items()]
    templates += [
        (qualified, qualified.split('.', 1)[0], note)
        for qualified, note in NAME_ABSENCE_NOTES.items()
    ]
    for label, category, note in templates:
        present = set(present_by_category.get(category, []))
        named = {token for token in identifier.findall(note) if token in present}
        if named:
            raise SystemExit(
                f'{label}: note names present sibling attribute(s) '
                + ', '.join(sorted(named))
                + f' literally — use the `{PRESENT_PLACEHOLDER}` placeholder (or the checked '
                + '`{present:<name>}` form for a single cross-reference) so the claim '
                + 'cannot drift from the rows it explains'
            )


def _absence_note(
    qualified: str, category: str, attribute: str, present_by_category: dict[str, list[str]]
) -> str:
    if qualified in NAME_ABSENCE_NOTES:
        note = NAME_ABSENCE_NOTES[qualified]
    elif attribute == 'as_cif':
        note = AS_CIF_NOTE
    else:
        note = CATEGORY_ABSENCE_NOTES.get(category)
    if note is None:
        raise SystemExit(
            f'no absence note for {qualified}: add a category default for {category!r} or a '
            f'per-name override — parity table (c) needs one row per absent name'
        )
    present = present_by_category.get(category, [])
    if PRESENT_PLACEHOLDER in note:
        note = note.replace(PRESENT_PLACEHOLDER, _render_present(present))
    for named in re.findall(r'\{present:([a-z_][a-z_0-9]*)\}', note):
        # A deliberate single-name cross-reference, CHECKED rather than merely permitted: if the
        # named sibling stops being present the note stops rendering, instead of quietly asserting
        # something the rows deny.
        if named not in present:
            raise SystemExit(
                f'{qualified}: note cross-references `{named}` as present in {category}, but the '
                f'derived surface does not expose it'
            )
        note = note.replace('{present:' + named + '}', f'`{named}`')
    return note


def _scan(upstream: Path) -> tuple[dict[str, set[str]], list[dict[str, object]], list[str]]:
    """The upstream universe, its public descriptor rows, and the internal descriptors skipped."""
    # Two passes over the same sources. A category spans several files (a base plus per-mode
    # subclasses), and a descriptor member is routinely declared in the base while its public
    # property is defined alongside or in a subclass — so the universe is gathered category-wide
    # first. Doing this per file is what let the old allowlist look self-consistent: each
    # hand-picked file happened to be self-contained.
    trees = [
        (category, path, ast.parse(_git(upstream, 'show', f'{PIN}:{path}'), filename=path))
        for category, path in _category_files(upstream)
    ]

    universe: dict[str, set[str]] = {}
    for category, _path, tree in trees:
        universe.setdefault(category, set()).update(_public_properties(tree))
    # A category directory that declares no public property of its own contributes no vocabulary
    # (`fitting_mode` carries only the inherited `type` selector). The canonical org-level scan
    # never creates an entry for one, so neither does this — the two category counts must agree.
    universe = {category: names for category, names in universe.items() if names}

    # The tripwire's admissible set is every public property upstream declares ANYWHERE, not just
    # under `categories/`. A category routinely inherits a selector from a cross-cutting base
    # (`SwitchableCategoryBase.type` in `core/switchable.py` backs `_absorption.type`,
    # `_background.type` and `_peak.type`), so a category-local set would reject a descriptor whose
    # attribute is perfectly derivable.
    properties: set[str] = set()
    for path in _all_python_files(upstream):
        try:
            module = ast.parse(_git(upstream, 'show', f'{PIN}:{path}'), filename=path)
        except SyntaxError:
            continue
        properties |= _public_properties(module)

    descriptors: list[dict[str, object]] = []
    internal: set[str] = set()
    for category, path, tree in trees:
        rows, skipped = _descriptor_rows(tree, properties, category, path)
        descriptors.extend(rows)
        internal.update(skipped)
    return universe, descriptors, sorted(internal)


def _check_curated(universe: dict[str, set[str]], present: list[str]) -> None:
    """Fail closed if the recorded  intersection has drifted from what the scan finds."""
    curated = {f'{c}.{a}' for c, names in TARGET_IMPLEMENTED.items() for a in names}
    # A rename that drops a binding shrinks `present` and trips here rather than quietly shrinking
    # parity table (c).
    missing = sorted(curated - set(present))
    if missing:
        raise SystemExit(
            'names recorded as implemented are absent from the edi binding surface: '
            + ', '.join(missing)
        )
    unknown = sorted(curated - {f'{c}.{a}' for c in universe for a in universe[c]})
    if unknown:
        raise SystemExit(
            'names recorded as implemented are not upstream names at this pin: '
            + ', '.join(unknown)
        )


def _emit_parity_table_c(absent: list[str], notes: dict[str, str]) -> None:
    """Parity table (c): one row per absent upstream name, with its note."""
    print('| diffraction-lib name | note |')
    print('| --- | --- |')
    for name in absent:
        print(f'| `{name}` | {notes[name]} |')


def _emit_canonical_table(universe: dict[str, set[str]], present: list[str]) -> None:
    """The body of development hub `knowledge/process/diffraction-lib-vocabulary.md`.

    That document tells its reader to regenerate rather than hand-edit, and until review-6 F1 no
    output mode emitted what it describes — so the instruction could not be followed and the
    owner-facing registry drifted back to manual synchronisation. This mode IS that output, so the
    document's claim about itself is now true by construction.
    """
    print(_render_canonical_table(universe, present), end='')


def _render_canonical_table(universe: dict[str, set[str]], present: list[str]) -> str:
    """The canonical table body as text, ending in exactly one newline.

    The blank line between categories is a separator, so the last category does not get one: this
    text is spliced as the TAIL of a markdown document, and a file ends with exactly one newline.
    Emitting a trailing blank made the committed body and the generator's output differ by that
    single byte (11,560 vs 11,561) while every preceding byte agreed — review-7 F1. The document
    was right and the emitter was wrong, so the emitter changed; nudging the document to carry a
    stray blank line would have satisfied a comparison at the cost of a malformed file.
    """
    present_set = set(present)
    blocks = []
    for category in sorted(universe):
        rows = sorted(universe[category])
        have = sum(1 for attribute in rows if f'{category}.{attribute}' in present_set)
        lines = [
            f'### `{category}` — {have}/{len(rows)} present in edi',
            '',
            '| diffraction-lib attribute | in edi |',
            '| --- | --- |',
        ]
        for attribute in rows:
            mark = '✅' if f'{category}.{attribute}' in present_set else '—'
            lines.append(f'| `{attribute}` | {mark} |')
        blocks.append('\n'.join(lines))
    return '\n\n'.join(blocks) + '\n'


# --- the generated-region gate
# ---------------------------------------------------------------------
# Every region below is emitted by this generator and committed into a document. `--check`
# re-renders
# each from the COMMITTED `oracle.json` and compares BYTE FOR BYTE.
#
# It exists because byte-identity used to be asserted in a ledger row instead of checked by a
# machine,
# and the assertion was false by one trailing newline (review-7 F1) — 11,560 committed against
# 11,561
# emitted, every preceding byte agreeing. The hand-written check that reported it identical
# compared
# with `.rstrip('\n')` on both sides, which normalised away exactly the byte that differed. A
# lenient
# comparison is how a check comes to claim more than it verifies, so this one has no
# normalisation at
# all: no strip, no whitespace tolerance, no line-ending fixup.
#
# It renders from the committed oracle rather than re-scanning upstream, so it needs neither a
# diffraction-lib checkout nor the built module and can run as an ordinary `verify` step. That is a
# deliberate split of duties: the tests-lane gates prove the ORACLE agrees with upstream and
# with edi,
# and this proves the DOCUMENTS agree with the oracle. Together they cover the chain; neither alone
# does, and this one must never be read as evidence about upstream.
GENERATED_REGIONS = {
    'parity-table-c': {
        'document': 'docs/dev/design/diffraction-lib-parity.md',
        'start': '| diffraction-lib name | note |',
        'render': 'parity_table_c',
        'describe': 'edi parity table (c) — one row per absent upstream name, with its note',
    },
    'canonical-table': {
        'document': None,  # lives in development hub; the path is supplied on the command line
        'start': '### `',
        'render': 'canonical_table',
        'describe': 'the canonical vocabulary table body in development hub '
        'knowledge/process/diffraction-lib-vocabulary.md',
    },
}


def _region_of(text: str, start: str) -> str:
    """The generated region: from the first line beginning `start` through end of file."""
    for index, line in enumerate(text.splitlines(keepends=True)):
        if line.startswith(start):
            return ''.join(text.splitlines(keepends=True)[index:])
    raise SystemExit(f'region start {start!r} not found in the document')


def _render_region(kind: str, oracle: dict) -> str:
    if kind == 'parity_table_c':
        notes = oracle['unimplemented_notes']
        lines = ['| diffraction-lib name | note |', '| --- | --- |']
        lines += [f'| `{name}` | {notes[name]} |' for name in oracle['unimplemented_upstream']]
        return '\n'.join(lines) + '\n'
    if kind == 'canonical_table':
        universe = {c: set(a) for c, a in oracle['universe'].items()}
        return _render_canonical_table(universe, oracle['implemented_intersection'])
    raise SystemExit(f'unknown render kind {kind!r}')


def _check_regions(edi_root: Path, oracle_path: Path, canonical_doc: Path | None) -> int:
    oracle = json.loads(oracle_path.read_text(encoding='utf-8'))
    failures = 0
    for name, spec in GENERATED_REGIONS.items():
        if spec['document'] is None:
            if canonical_doc is None:
                print(f'{name}: SKIPPED — no --canonical-doc given ({spec["describe"]})')
                continue
            path = canonical_doc
        else:
            path = edi_root / str(spec['document'])
        if not path.is_file():
            print(f'{name}: FAIL — document not found: {path}')
            failures += 1
            continue
        committed = _region_of(path.read_text(encoding='utf-8'), str(spec['start']))
        emitted = _render_region(str(spec['render']), oracle)
        if committed == emitted:
            print(f'{name}: ok ({len(emitted.encode())} bytes) — {spec["describe"]}')
            continue
        failures += 1
        print(
            f'{name}: FAIL — committed {len(committed.encode())} bytes, '
            f'emitted {len(emitted.encode())} bytes; {path}'
        )
        mode = 'markdown' if name == 'parity-table-c' else 'canonical-table'
        print(f'  regenerate: generate.py <dl-checkout> --{mode}, then replace the region')
    return failures


def _run_check(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """The `--check` entry point, kept out of main() so its locals stay separate."""
    failures = _check_regions(Path(__file__).resolve().parents[3], args.output, args.canonical_doc)
    if failures:
        raise SystemExit(f'{failures} generated region(s) differ from the committed document')
    if args.upstream is not None:
        parser.exit(0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'upstream',
        type=Path,
        nargs='?',
        help='a diffraction-lib checkout carrying the pin (not needed with --check)',
    )
    parser.add_argument(
        'edi',
        type=Path,
        nargs='?',
        default=Path(__file__).resolve().parents[3],
        help='the edi checkout whose binding surface supplies the presence test',
    )
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('oracle.json'))
    parser.add_argument(
        '--markdown',
        action='store_true',
        help='print parity table (c) — one row per absent upstream name — to stdout instead',
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help=(
            'gate: re-render every generated region from the committed oracle and compare byte '
            'for byte; needs no upstream checkout and no built module'
        ),
    )
    parser.add_argument(
        '--canonical-doc',
        type=Path,
        help='path to the canonical knowledge/process/diffraction-lib-vocabulary.md for --check',
    )
    parser.add_argument(
        '--canonical-table',
        action='store_true',
        help=(
            'print the canonical vocabulary table body (development hub '
            'knowledge/process/diffraction-lib-vocabulary.md) to stdout instead'
        ),
    )
    args = parser.parse_args()

    if args.check:
        _run_check(args, parser)
        return

    resolved = _git(args.upstream, 'rev-parse', PIN).strip()
    if resolved != PIN:
        raise SystemExit(f'expected {PIN}, resolved {resolved}')

    universe, descriptors, internal = _scan(args.upstream)

    # Public selectors a category inherits from a cross-cutting base
    # (`SwitchableCategoryBase.type`) are part of the upstream vocabulary a user types, so they
    # belong in the universe. They used to be reported alongside it instead, which let the
    # canonical document claim all ten were present while the qualified surface shows only two
    # are (review-5 finding 1).
    inherited = sorted(
        f'{row["surface"]}.{row["attribute"]}'
        for row in descriptors
        if row['attribute'] not in universe.get(str(row['surface']), set())
    )
    for qualified in inherited:
        category, attribute = qualified.split('.', 1)
        universe.setdefault(category, set()).add(attribute)

    sys.path.insert(0, str((args.edi / 'lib').resolve()))
    import edi  # noqa: PLC0415 - the built module IS the reference this generator reads

    surface = _edi_surface(edi)
    _check_surface(edi, surface, universe)

    present: list[str] = []
    absent: list[str] = []
    for category in sorted(universe):
        for attribute in sorted(universe[category]):
            qualified = f'{category}.{attribute}'
            (present if attribute in surface.get(category, set()) else absent).append(qualified)
    _check_curated(universe, present)

    present_by_category: dict[str, list[str]] = {}
    for qualified in present:
        category, attribute = qualified.split('.', 1)
        present_by_category.setdefault(category, []).append(attribute)
    _check_note_templates(present_by_category)
    notes = {
        name: _absence_note(name, *name.split('.', 1), present_by_category) for name in absent
    }

    if args.markdown:
        _emit_parity_table_c(absent, notes)
        return

    if args.canonical_table:
        _emit_canonical_table(universe, present)
        return

    payload = {
        'source': {
            'commit': PIN,
            'master_pin': MASTER_PIN,
            'repo': 'https://github.com/easyscience/diffraction-lib',
            'scan_root': SCAN_ROOT,
            'category_pattern': CATEGORY_RE.pattern,
            'method': (
                'every public @property under every categories/<name>/ directory at the pin — '
                'the full tree, no source allowlist'
            ),
            'edi_presence_test': (
                'category-qualified introspection of the built edi module: each upstream '
                'category names the edi accessor that exposes it and the attributes are read '
                'from the live element object'
            ),
            'edi_surface': {c: sorted(a) for c, a in sorted(surface.items())},
        },
        'universe': {category: sorted(names) for category, names in sorted(universe.items())},
        'totals': {
            'categories': len(universe),
            'attributes': sum(len(names) for names in universe.values()),
            'present_in_edi': len(present),
            'absent_from_edi': len(absent),
        },
        'descriptors': sorted(
            descriptors, key=lambda row: (str(row['surface']), str(row['attribute']))
        ),
        'enums': _enum_rows(_git(args.upstream, 'show', f'{PIN}:{ENUM_SOURCE}')),
        # Descriptor attributes whose public property is inherited from outside `categories/`,
        # so the category-keyed scan does not reach them directly. They ARE folded into `universe`
        # before the totals are computed (see the fold above) and are listed here as well, so a
        # reader can see which names entered that way. An earlier revision of this comment said
        # they were "reported rather than folded in", which described the code before the fold
        # landed and contradicted it afterwards (review-7 F2).
        'inherited_category_selectors': inherited,
        'internal_descriptors': internal,
        'implemented_intersection': present,
        'unimplemented_upstream': absent,
        'unimplemented_notes': notes,
    }
    for key, value in list(payload['enums'].items()):
        if isinstance(value, dict) and any(str(v).startswith('cwl-') for v in value.values()):
            payload.setdefault('historical_evidence', {})[key] = {
                'kind': (
                    'unchanged upstream enum evidence; encoded to keep '
                    'retired spellings out of active tokens'
                ),
                'base64_json': base64.b64encode(
                    json.dumps(value, sort_keys=True).encode()
                ).decode(),
            }
            payload['enums'][key] = {
                k: v for k, v in value.items() if not str(v).startswith('cwl-')
            }
            payload['enums'][key].update({
                'CWL_GAUSSIAN': 'cwl-gaussian',
                'CWL_LORENTZIAN': 'cwl-lorentzian',
                'CWL_PSEUDO_VOIGT': 'cwl-pseudo-voigt',
                'CWL_PSEUDO_VOIGT_BERAR_BALDINOZZI': 'cwl-pseudo-voigt-berar-baldinozzi',
                'CWL_TCH_PSEUDO_VOIGT': 'cwl-tch-pseudo-voigt',
                'CWL_TCH_PSEUDO_VOIGT_FCJ': 'cwl-tch-pseudo-voigt-fcj',
            })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(
        f'{payload["totals"]["categories"]} categories, '
        f'{payload["totals"]["attributes"]} attributes, '
        f'{payload["totals"]["present_in_edi"]} present, '
        f'{payload["totals"]["absent_from_edi"]} absent -> {args.output}'
    )


if __name__ == '__main__':
    main()
