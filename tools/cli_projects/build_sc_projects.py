# SPDX-License-Identifier: BSD-3-Clause
"""Build the single-crystal CLI projects from FullProf's references.

Each verification project reproduces one of diffraction-lib's ``sc-*`` verification pages: the
structure, extinction and scale of the FullProf ``.pcr`` the page reads, and the measured
reflections of its ``.int`` file, with the parameters the page frees left free. The fitting
examples start the same data from rough values. The FullProf files are the committed references
under ``tests/fixtures/single_crystal/fullprof/`` (diffraction-lib's ``docs/docs/verification/
fullprof/sc-*``, unchanged).

Usage (writes ``docs/user/cli/<id>/project/``, every project or the ids given)::

    python tools/cli_projects/build_sc_projects.py [--out DIR] [ID ...]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FP = ROOT / 'tests' / 'fixtures' / 'single_crystal' / 'fullprof'
# FullProf's fits of the same pages on their measured reflections, which the verification projects'
# expected values come from.
FITTED = ROOT / 'tests' / 'fixtures' / 'single_crystal' / 'fitting' / 'fullprof'
# The Becker-Coppens fit of the extinction page, which FullProf cannot make.
BECKER_COPPENS = ROOT / 'tests' / 'fixtures' / 'single_crystal' / 'fitting' / 'becker-coppens'

PR2NIO4_SITES = [
    # id, type, x, y, z, wyckoff, occupancy, adp_type, adp_iso, beta (11 22 33 12 13 23)
    (
        'Pr',
        'Pr',
        '0',
        '0',
        '0.35973',
        'i',
        '1',
        'beta',
        None,
        ('0.0071', '0.0071', '0.00084', '0', '0', '0'),
    ),
    (
        'Ni',
        'Ni',
        '0',
        '0',
        '0',
        'a',
        '1',
        'beta',
        None,
        ('0.0028', '0.0028', '0.00151', '0', '0', '0'),
    ),
    (
        'O1',
        'O',
        '0.25',
        '0.25',
        '0',
        'e',
        '1',
        'beta',
        None,
        ('0.005', '0.005', '0.00413', '-0.0014', '0', '0'),
    ),
    (
        'O2',
        'O',
        '0',
        '0',
        '0.17385',
        'i',
        '0.722965',
        'beta',
        None,
        ('0.01716', '0.01716', '0.00045', '0', '0', '0'),
    ),
    (
        'Oi',
        'O',
        '0.25',
        '0.25',
        '0.25',
        'f',
        '0.074655',
        'beta',
        None,
        ('0.01033', '0.01176', '0.001', '0', '0', '0'),
    ),
    ('Od', 'O', '0.07347', '0.07347', '0.17349', 'p', '0.074654', 'Biso', '2.31435', None),
]

TBTI_ISO_SITES = [
    ('Tb', 'Tb', '0.5', '0.5', '0.5', 'd', '1', 'Biso', '0', None),
    ('Ti', 'Ti', '0', '0', '0', 'c', '1', 'Biso', '0', None),
    ('O1', 'O', '0.32804', '0.125', '0.125', 'f', '1', 'Biso', '0', None),
    ('O2', 'O', '0.375', '0.375', '0.375', 'b', '1', 'Biso', '0', None),
]

TBTI_ANISO_SITES = [
    (
        'Tb',
        'Tb',
        '0.5',
        '0.5',
        '0.5',
        'd',
        '1',
        'beta',
        None,
        ('0.00099', '0.00099', '0.00099', '-0.00048', '-0.00048', '-0.00048'),
    ),
    (
        'Ti',
        'Ti',
        '0',
        '0',
        '0',
        'c',
        '1',
        'beta',
        None,
        ('0.00091', '0.00091', '0.00091', '-0.00017', '-0.00017', '-0.00017'),
    ),
    (
        'O1',
        'O',
        '0.32804',
        '0.125',
        '0.125',
        'f',
        '1',
        'beta',
        None,
        ('0.00123', '0.00078', '0.00078', '0', '0', '0.00041'),
    ),
    (
        'O2',
        'O',
        '0.375',
        '0.375',
        '0.375',
        'b',
        '1',
        'beta',
        None,
        ('0.00061', '0.00061', '0.00061', '0', '0', '0'),
    ),
]

TAURINE_SITES = [
    (sid, typ, x, y, z, 'e', '1', 'Biso', biso, None)
    for sid, typ, x, y, z, biso in [
        ('S1', 'S', '0.19448', '0.35173', '0.3473', '1.37018'),
        ('O1', 'O', '0.31207', '0.23951', '0.35143', '2.68011'),
        ('O2', 'O', '-0.05909', '0.33563', '0.29636', '3.50515'),
        ('O3', 'O', '0.22105', '0.41215', '0.50573', '1.83513'),
        ('N1', 'N', '0.2634', '0.62808', '0.33048', '2.07364'),
        ('H1', 'H', '0.12861', '0.58669', '0.41769', '3.31527'),
        ('H2', 'H', '0.18953', '0.71385', '0.31124', '4.46988'),
        ('H3', 'H', '0.4397', '0.62023', '0.34592', '4.34151'),
        ('C1', 'C', '0.34384', '0.44116', '0.20155', '1.73667'),
        ('H11', 'H', '0.55246', '0.43345', '0.24304', '3.32279'),
        ('H12', 'H', '0.32537', '0.3897', '0.08264', '3.05746'),
        ('C2', 'C', '0.20029', '0.55716', '0.18272', '1.66017'),
        ('H21', 'H', '0.2765', '0.60004', '0.07688', '2.15403'),
        ('H22', 'H', '-0.00383', '0.54767', '0.15762', '4.71303'),
    ]
]

PROJECTS = {
    'sc-neut-tof_taurine-senju_isotropic-adp': {
        'source': 'sc-neut-tof_taurine_basic/taurine.int',
        'reference': 'sc-neut-tof_taurine-unknown_basic',
        'structure': 'taurine',
        'experiment': 'senju',
        'title': 'Taurine [P2₁/c] · SENJU @ J-PARC',
        'instrument': 'SENJU',
        'facility': 'J-PARC',
        'description': 'Single crystal · Time of flight · Isotropic ADPs · Scale-only fit',
        'space_group': ('P 21/c', 'b1'),
        'cell': ('5.272901', '11.656488', '7.838297', '90', '94.010994', '90'),
        'sites': TAURINE_SITES,
        'scale': '2.711()',
        'extinction': None,
        'tof': True,
        # FullProf fits only the reflections it does not exclude (I > 3 sigma, and one more).
        'select': 'sc-neut-tof_taurine-unknown_basic/taurine.out',
    },
    'sc-neut-cwl_pr2nio4-5c2_anisotropic-adp': {
        'source': 'sc-neut-cwl_pr2nio4_basic/prnio.int',
        'reference': 'sc-neut-cwl_pr2nio4-5c2_basic',
        'structure': 'pr2nio4',
        'experiment': 'llb_5c2',
        'title': 'Pr₂NiO₄ [Fmmm] · 5C2 @ LLB',
        'instrument': '5C2',
        'facility': 'LLB',
        'description': 'Single crystal · Anisotropic β tensors · Scale-only fit',
        'space_group': ('F m m m', None),
        'cell': ('5.417799', '5.4146', '12.483399', '90', '90', '90'),
        'sites': PR2NIO4_SITES,
        'scale': '4.031()',
        'extinction': None,
    },
    'sc-neut-cwl_tb2ti2o7-heidi_isotropic-adp': {
        'source': 'sc-neut-cwl_tbti_basic/tbti.int',
        'reference': 'sc-neut-cwl_tb2ti2o7-heidi_basic',
        'structure': 'tb2ti2o7',
        'experiment': 'heidi',
        'title': 'Tb₂Ti₂O₇ [Fd-3m] · HEiDi @ MLZ (FRM II)',
        'instrument': 'HEiDi',
        'facility': 'MLZ (FRM II)',
        'description': 'Single crystal · Isotropic ADPs · Scale-only fit',
        'space_group': ('F d -3 m', '2'),
        'cell': ('10.13', '10.13', '10.13', '90', '90', '90'),
        'sites': TBTI_ISO_SITES,
        'scale': '3.653()',
        'extinction': None,
    },
    'sc-neut-cwl_tb2ti2o7-heidi_isotropic-extinction': {
        'source': 'sc-neut-cwl_tbti_isotropic-extinction/tbti.int',
        'structure': 'tb2ti2o7',
        'experiment': 'heidi',
        'title': 'Tb₂Ti₂O₇ [Fd-3m] · HEiDi @ MLZ (FRM II)',
        'instrument': 'HEiDi',
        'facility': 'MLZ (FRM II)',
        'description': 'Single crystal · Becker-Coppens extinction · Scale and domain radius fit',
        'space_group': ('F d -3 m', '2'),
        'cell': ('10.13', '10.13', '10.13', '90', '90', '90'),
        'sites': TBTI_ISO_SITES,
        'scale': '4.1744()',
        # cryspy's single radius, for parity: the crystal radius follows the domain radius.
        'extinction': ('becker-coppens-mixed', 'gaussian', '10()', '101810.87303', '0.01'),
        'single_radius': True,
    },
    'sc-neut-cwl_tb2ti2o7-heidi_anisotropic-adp': {
        'source': 'sc-neut-cwl_tbti_anisotropic-adp/tbti.int',
        'structure': 'tb2ti2o7',
        'experiment': 'heidi',
        'title': 'Tb₂Ti₂O₇ [Fd-3m] · HEiDi @ MLZ (FRM II)',
        'instrument': 'HEiDi',
        'facility': 'MLZ (FRM II)',
        'description': 'Single crystal · Anisotropic β tensors · Scale-only fit',
        'space_group': ('F d -3 m', '2'),
        'cell': ('10.13', '10.13', '10.13', '90', '90', '90'),
        'sites': TBTI_ANISO_SITES,
        'scale': '4.6()',
        'extinction': None,
    },
}


# FullProf's taurine project from the owner (2026-10-23, SENJU @ J-PARC, taurine.pcr): its
# positions and beta tensors as the start, every one free as FullProf refines them, and one scale
# per dataset (Sc1-Sc6).
TAURINE_FULLPROF_SITES = [
    (
        'S1',
        'S',
        '0.20300()',
        '0.34676()',
        '0.35118()',
        'e',
        '1',
        'beta',
        '0',
        ('0.00608()', '0.00124()', '0.00863()', '0.00050()', '0.00186()', '-0.00031()'),
    ),
    (
        'O1',
        'O',
        '0.33902()',
        '0.24201()',
        '0.35341()',
        'e',
        '1',
        'beta',
        '0',
        ('0.02351()', '0.00278()', '0.01353()', '0.00452()', '0.00639()', '0.00068()'),
    ),
    (
        'O2',
        'O',
        '-0.06427()',
        '0.33875()',
        '0.29137()',
        'e',
        '1',
        'beta',
        '0',
        ('0.01088()', '0.00363()', '0.01829()', '-0.00185()', '-0.00126()', '-0.00162()'),
    ),
    (
        'O3',
        'O',
        '0.23286()',
        '0.40985()',
        '0.51108()',
        'e',
        '1',
        'beta',
        '0',
        ('0.02111()', '0.00413()', '0.00713()', '0.00045()', '0.00246()', '-0.00082()'),
    ),
    (
        'N1',
        'N',
        '0.26440()',
        '0.62996()',
        '0.33158()',
        'e',
        '1',
        'beta',
        '0',
        ('0.01644()', '0.00258()', '0.00836()', '0.00055()', '0.00283()', '0.00005()'),
    ),
    (
        'H1',
        'H',
        '0.17000()',
        '0.59950()',
        '0.43173()',
        'e',
        '1',
        'beta',
        '0',
        ('0.04503()', '0.00645()', '0.01266()', '-0.00627()', '0.01230()', '0.00003()'),
    ),
    (
        'H2',
        'H',
        '0.19405()',
        '0.70895()',
        '0.30623()',
        'e',
        '1',
        'beta',
        '0',
        ('0.03957()', '0.00324()', '0.01565()', '-0.00032()', '-0.00048()', '0.00042()'),
    ),
    (
        'H3',
        'H',
        '0.45233()',
        '0.63476()',
        '0.36061()',
        'e',
        '1',
        'beta',
        '0',
        ('0.02533()', '0.00525()', '0.01906()', '0.00034()', '0.00246()', '-0.00526()'),
    ),
    (
        'C1',
        'C',
        '0.34074()',
        '0.43812()',
        '0.19983()',
        'e',
        '1',
        'beta',
        '0',
        ('0.01816()', '0.00217()', '0.00715()', '0.00028()', '0.00309()', '-0.00042()'),
    ),
    (
        'H11',
        'H',
        '0.53973()',
        '0.44320()',
        '0.23493()',
        'e',
        '1',
        'beta',
        '0',
        ('0.01829()', '0.00695()', '0.01989()', '0.00257()', '0.00840()', '-0.00019()'),
    ),
    (
        'H12',
        'H',
        '0.32105()',
        '0.39069()',
        '0.08168()',
        'e',
        '1',
        'beta',
        '0',
        ('0.05033()', '0.00504()', '0.01083()', '0.00384()', '0.00923()', '-0.00170()'),
    ),
    (
        'C2',
        'C',
        '0.20803()',
        '0.55562()',
        '0.18084()',
        'e',
        '1',
        'beta',
        '0',
        ('0.01723()', '0.00322()', '0.00721()', '-0.00006()', '-0.00007()', '0.00059()'),
    ),
    (
        'H21',
        'H',
        '0.28448()',
        '0.59948()',
        '0.07592()',
        'e',
        '1',
        'beta',
        '0',
        ('0.05136()', '0.00739()', '0.00957()', '-0.00328()', '0.01154()', '0.00254()'),
    ),
    (
        'H22',
        'H',
        '0.00169()',
        '0.54787()',
        '0.16446()',
        'e',
        '1',
        'beta',
        '0',
        ('0.02922()', '0.00655()', '0.01968()', '-0.00054()', '-0.00477()', '0.00034()'),
    ),
]
TAURINE_SCALES = ['2.762()', '3.829()', '3.211()', '2.809()', '2.739()', '2.936()']
# The example starts away from FullProf's values (the owner, 2026-10-24): every beta 0, four
# coordinates moved by 0.005 and the extinction 0, all still free.
TAURINE_MOVED = {
    ('S1', 0): '0.20800()',
    ('O1', 1): '0.23701()',
    ('N1', 2): '0.33658()',
    ('C1', 0): '0.33574()',
}
TAURINE_START_SITES = [
    (
        sid,
        typ,
        *(TAURINE_MOVED.get((sid, axis), value) for axis, value in enumerate((x, y, z))),
        wyckoff,
        occ,
        adp_type,
        adp_iso,
        tuple('0()' for _ in beta),
    )
    for sid, typ, x, y, z, wyckoff, occ, adp_type, adp_iso, beta in TAURINE_FULLPROF_SITES
]
# Its Shelx-like anisotropic extinction (Ext-Model 4): Ext1-Ext3 free, Ext4-Ext6 0 and fixed.
TAURINE_EXTINCTION = {
    'type': 'larson-anisotropic',
    'coefficient_11': '0()',
    'coefficient_22': '0()',
    'coefficient_33': '0()',
    'coefficient_12': '0',
    'coefficient_13': '0',
    'coefficient_23': '0',
}


# The app's fitting examples: displacements from a small start, one extinction parameter free
# at most, the free coordinates moved off their refined values.
U = '0.0026()'
TBTI_FIT_SITES = [
    (
        'Tb',
        'Tb',
        '0.5',
        '0.5',
        '0.5',
        'd',
        '1',
        'Uani',
        '0.0026',
        (U, '0.0026', '0.0026', '0()', '0', '0'),
    ),
    (
        'Ti',
        'Ti',
        '0',
        '0',
        '0',
        'c',
        '1',
        'Uani',
        '0.0026',
        (U, '0.0026', '0.0026', '0()', '0', '0'),
    ),
    (
        'O1',
        'O',
        '0.3300()',
        '0.125',
        '0.125',
        'f',
        '1',
        'Uani',
        '0.0026',
        (U, U, '0.0026', '0', '0', '0()'),
    ),
    (
        'O2',
        'O',
        '0.375',
        '0.375',
        '0.375',
        'b',
        '1',
        'Uani',
        '0.0026',
        (U, '0.0026', '0.0026', '0', '0', '0'),
    ),
]
# Pr2NiO4 starts every displacement at 0 and free: Bani on every site but Od, which is Biso (the
# owner, 2026-10-23). O1's site leaves B12 free as well.
B0 = ('0()', '0()', '0()', '0', '0', '0')
B0_12 = ('0()', '0()', '0()', '0()', '0', '0')
PR2NIO4_FIT_SITES = [
    ('Pr', 'Pr', '0', '0', '0.3620()', 'i', '1', 'Bani', '0', B0),
    ('Ni', 'Ni', '0', '0', '0', 'a', '1', 'Bani', '0', B0),
    ('O1', 'O', '0.25', '0.25', '0', 'e', '1', 'Bani', '0', B0_12),
    ('O2', 'O', '0', '0', '0.1760()', 'i', '0.722965', 'Bani', '0', B0),
    ('Oi', 'O', '0.25', '0.25', '0.25', 'f', '0.074655', 'Bani', '0', B0),
    ('Od', 'O', '0.0750()', '0.0750()', '0.1750()', 'p', '0.074654', 'Biso', '0()', None),
]
FIT_PROJECTS = {
    'sc-neut-tof_taurine-senju': {
        'source': 'sc-neut-tof_taurine_basic/taurine.int',
        # The owner's FullProf file: six datasets (column 6), one experiment each.
        'data': 'taurine-senju.int',
        'datasets': TAURINE_SCALES,
        'structure': 'taurine',
        'experiment': 'senju',
        'title': 'Taurine [P2₁/c] · SENJU @ J-PARC',
        'instrument': 'SENJU',
        'facility': 'J-PARC',
        'description': (
            'Single crystal · Time of flight · Six datasets · Anisotropic displacements'
        ),
        'purpose': 'refinement',
        'space_group': ('P 21/c', 'b1'),
        'cell': ('5.272901', '11.656495', '7.838298', '90', '94.010994', '90'),
        'sites': TAURINE_START_SITES,
        'scale': None,
        # FullProf's model 4, Ext1-Ext3 free; one crystal, so experiments 2-6 take experiment 1's.
        'extinction': TAURINE_EXTINCTION,
        'shared_extinction': ('coefficient_11', 'coefficient_22', 'coefficient_33'),
        # FullProf fits only reflections with F² > 3 su(F²) (taurine.pcr's Rmub 3.0).
        'fit_cutoff': 3,
        'tof': True,
    },
    'sc-neut-cwl_tb2ti2o7-heidi': {
        'source': 'sc-neut-cwl_tbti_basic/tbti.int',
        'data': 'tbti-heidi.xye',
        'structure': 'tb2ti2o7',
        'experiment': 'heidi',
        'title': 'Tb₂Ti₂O₇ [Fd-3m] · HEiDi @ MLZ (FRM II)',
        'instrument': 'HEiDi',
        'facility': 'MLZ (FRM II)',
        'description': (
            'Single crystal · Anisotropic displacements and extinction from a rough start'
        ),
        'purpose': 'refinement',
        'space_group': ('F d -3 m', '2'),
        'cell': ('10.13', '10.13', '10.13', '90', '90', '90'),
        'sites': TBTI_FIT_SITES,
        'scale': '4()',
        # The crystal radius 3 mm; the domain radius from 25 um (the owner, 2026-10-23).
        'extinction': ('becker-coppens-mixed', 'gaussian', '25()', '0()', '3'),
    },
    'sc-neut-cwl_pr2nio4-5c2': {
        'source': 'sc-neut-cwl_pr2nio4_basic/prnio.int',
        'data': 'prnio.int',
        'structure': 'pr2nio4',
        'experiment': 'llb_5c2',
        'title': 'Pr₂NiO₄ [Fmmm] · 5C2 @ LLB',
        'instrument': '5C2',
        'facility': 'LLB',
        'description': (
            'Single crystal · Anisotropic displacements and coordinates from a rough start'
        ),
        'purpose': 'refinement',
        'space_group': ('F m m m', None),
        'cell': ('5.417799', '5.4146', '12.483399', '90', '90', '90'),
        'sites': PR2NIO4_FIT_SITES,
        'scale': '4()',
        # No extinction, as in FullProf's refinement of these reflections (the owner, 2026-10-23).
        'extinction': None,
    },
}


# The catalogue cases' pages and provenance (edi ADR-0048): what each case is, where its data
# and model come from, how it starts and what this start reaches. The data file under `data/` is
# the one the project's reflections are read from.
DATA_REPOSITORY = (
    'the repository `easyscience/diffraction` at commit `3ec801667904578ea39f1a4f4aa941866543a669`'
)
DIFFRACTION_LIB = 'diffraction-lib (develop `cb2cda7be6117199be8f8cac0a666a7bccd32d90`)'
CASES = {
    'sc-neut-cwl_tb2ti2o7-heidi': {
        'heading': 'Single-crystal fit: Tb₂Ti₂O₇, HEiDi',
        'lede': (
            'Fit the pyrochlore Tb₂Ti₂O₇ to constant-wavelength neutron single-crystal data '
            'from HEiDi at MLZ, with anisotropic displacements and Becker-Coppens extinction.'
        ),
        'start': (
            'The project starts from rough values: anisotropic displacements at a small '
            'isotropic-equivalent value, the free O1 x moved off its refined value, mixed '
            'Becker-Coppens extinction with a crystal radius of 3 mm and the domain radius (from '
            '25 μm) and mosaic spread (from 0) free, and the scale to one significant figure.'
        ),
        'model': (
            "{lib}'s verification page `sc-neut-cwl_tbti_anisotropic-adp` (FullProf "
            '`tbti.pcr`): the Fd-3m structure, its sites and the wavelength 0.793 Å. The '
            'tutorial `refine-tbti-heidi` fits the same data.'
        ),
        'data': (
            '`data/tbti-heidi.xye`, dataset `meas-tbti-heidi` of {repo} (path '
            '`data/measured/tbti-heidi.xye`), licence BSD-3-Clause. The project embeds its 220 '
            'reflections unchanged (h, k, l, F², su).'
        ),
        'start_detail': (
            'Uani on every site from an isotropic-equivalent 0.0026 Å², tied by site symmetry; '
            'O1 x moved off its refined value; isotropic Becker-Coppens extinction, mixed, with '
            'the crystal radius 3 mm, the domain radius free from 25 μm and the mosaic spread '
            'free from 0 (the owner, 2026-10-23); the scale 4. Free: the scale, '
            'O1 x, the eight independent tensor components, the domain radius and the mosaic '
            'spread (12 parameters).'
        ),
        'differences': [
            (
                'The tutorial refines isotropic displacements, occupancies and the radius first '
                'and the anisotropic tensors after; here the tensors are free from the start '
                'and the occupancies are fixed.'
            ),
            (
                'The tutorial frees its one radius, crystal and domain at once, at a fixed '
                'mosaic spread; here the crystal radius describes the crystal (3 mm) and the '
                'domain radius and mosaic spread are free.'
            ),
        ],
        'result': (
            'From this start edi converges in 12 iterations to reduced χ² 1.33 over the 220 '
            'reflections (R(F²) 2.42 %), with the scale 5.899(35), the domain radius 3.0(18) μm '
            'and the mosaic spread 2732(93) rad⁻¹. FullProf 8.40 from the same start has no '
            'Becker-Coppens model and fits its own empirical extinction instead: 15 cycles to χ² '
            '1.41, RF2w 2.98 %, the scale 6.00(4). The models differ, so its values are a '
            'comparison, not a reference.'
        ),
    },
    'sc-neut-cwl_pr2nio4-5c2': {
        'heading': 'Single-crystal fit: Pr₂NiO₄, 5C2',
        'lede': (
            'Fit the layered nickelate Pr₂NiO₄ to constant-wavelength neutron single-crystal '
            'data from 5C2 at LLB, with anisotropic displacements.'
        ),
        'start': (
            'The project starts from zero: every displacement at 0 (Bani on every site but Od, '
            'which is Biso) and free, the free coordinates moved off their refined values, no '
            'extinction, and the scale to one significant figure.'
        ),
        'model': (
            "FullProf Suite's example `prnio.pcr` (Pr₂NiO₄+δ, SXTAL), as {lib} reads it on its "
            'verification page `sc-neut-cwl_pr2nio4_basic`: the Fmmm structure, its sites, '
            'occupancies and the wavelength 0.8302 Å.'
        ),
        'data': (
            "`data/prnio.int`, the reflections of FullProf Suite's example `prnio.int` as {lib} "
            'commits them '
            '(`docs/docs/verification/fullprof/sc-neut-cwl_pr2nio4_basic/prnio.int`, licence '
            'BSD-3-Clause). The project embeds its reflections unchanged (h, k, l, F², su).'
        ),
        'start_detail': (
            'Bani on every site but Od, every independent component from 0 (with B12 on O1, '
            'whose site allows it), and Biso 0 on Od, all free (the owner, 2026-10-23); the '
            'free coordinates moved off their refined values (Pr z 0.362, O2 z 0.176, Od 0.075, '
            '0.075, 0.175); no extinction (type None); the scale 4. '
            'Free: the scale, 17 displacement components and the free coordinates (23 '
            'parameters).'
        ),
        'differences': [
            (
                "FullProf's example refines anisotropic β tensors with its empirical extinction "
                'model left at zero; here the tensors are Bani, which is the same model in Å², '
                'and there is no extinction.'
            ),
        ],
        'result': (
            'From this start edi converges in 11 iterations to reduced χ² 9.75 over the 198 '
            'reflections, with the scale 4.022(28). FullProf 8.40 from the same start, with β '
            'tensors, converges in 14 cycles to χ² 9.69 and the scale 4.022(28) on this occupancy '
            "scale; all 23 values agree within 0.01 of edi's s.u."
        ),
    },
    'sc-neut-tof_taurine-senju': {
        'heading': 'Single-crystal fit: taurine, SENJU',
        'lede': (
            'Fit the amino-sulfonic acid taurine to six time-of-flight neutron single-crystal '
            'datasets from SENJU at J-PARC together, each reflection measured at its own '
            'wavelength.'
        ),
        'start': (
            "The project starts away from FullProf's fit: every beta tensor 0, four coordinates "
            "moved by 0.005, FullProf's scales and the anisotropic Larson extinction 0, every one "
            'free.'
        ),
        'model': (
            "{lib}'s verification page `sc-neut-tof_taurine_basic` (FullProf `taurine.pcr`): "
            'the P2₁/c structure and its 14 sites.'
        ),
        'data': (
            "`data/taurine-senju.int`, FullProf's reflection file of the taurine project with "
            'its six SENJU datasets (the dataset in column 6), one experiment each. The project '
            'embeds the 1540 reflections with a positive su (286, 255, 276, 221, 242 and 260) '
            'unchanged (h, k, l, F², su, wavelength).'
        ),
        'start_detail': (
            "FullProf's positions with S1 x, O1 y, N1 z and C1 x moved by 0.005 (S1 x 0.20800 for "
            '0.20300, O1 y 0.23701 for 0.24201, N1 z 0.33658 for 0.33158, C1 x 0.33574 for '
            '0.34074), every beta tensor 0, its scales Sc1-Sc6 and its extinction model 4 '
            '(anisotropic Larson) with x11, x22 and x33 0, x12, x13 and x23 0 and fixed. '
            "Experiments 2-6 take experiment 1's extinction through constraints. Free: "
            'every position and beta, the six scales and the three extinction terms (135 '
            'parameters). As FullProf (Rmub 3.0), the fit uses only reflections with '
            'F² > 3 su(F²).'
        ),
        'differences': [
            (
                'FullProf leaves the reflections it marks forbidden out; they have no su here and '
                'are not in the project.'
            ),
            (
                "FullProf multiplies each s.u. by its parameter's codeword coefficient (its "
                'manual, eq. 3.7), and this .pcr codes the six scales and the three extinction '
                'terms with 0.20, so FullProf prints their s.u. at a fifth: x11 0.000760 against '
                "edi's 0.0036. With the 0.20 undone the s.u. agree: edi's are 1.00 to 1.02 times "
                "FullProf's for the scales, 0.94 to 0.96 for the extinction, 1.04 to 1.10 for the"
                ' positions and 1.02 to 1.08 for the betas.'
            ),
            (
                'FullProf prints χ² 30.1; its own reflection list gives sum((F²obs - F²calc)/su)²'
                ' = 24676 over the 947 reflections, which is 30.39 over N - P = 812 as edi and '
                "FullProf's manual (eq. 3.8) define it. Started from FullProf's values, edi finds"
                ' 30.41 there and goes on in 4 iterations to 30.27, the minimum it reaches from '
                "this example's start: FullProf applies its scale and extinction shifts at 0.20 "
                'too (the same codewords) and stops just above the minimum.'
            ),
        ],
        'result': (
            'From this start edi converges in 8 iterations to reduced χ² 30.27, wR(F²) 12.2 %, '
            'over the same 947 reflections FullProf fits (FullProf 8.40 from the same start, '
            'converged in 40 cycles: χ² 30.1, RF2w 12.2 %). Every one of the 135 parameters is '
            "within 0.6 of edi's s.u. of FullProf's value (positions within 0.41, betas 0.38, "
            'scales 0.58, extinction 0.46): x11 0.0584(36), x22 0.0139(15) and x33 0.0076(15) '
            "against FullProf's 0.0567, 0.0135 and 0.0071, and scales "
            "2.80(6), 3.87(9), 3.25(6), 2.84(7), 2.78(6) and 2.97(6) against FullProf's 2.78, "
            '3.85, 3.23, 2.83, 2.74 and 2.96.'
        ),
    },
}


def extinction_lines(extinction: tuple | dict | None) -> list[str]:
    """The experiment's _extinction items: the type, then that type's own items."""
    if extinction is None:
        return ['_extinction.type none']
    if isinstance(extinction, dict):
        return [f'_extinction.{item} {value}' for item, value in extinction.items()]
    kind, distribution, radius, spread, crystal = extinction
    return [
        f'_extinction.type {kind}',
        f'_extinction.mosaic_distribution {distribution}',
        f'_extinction.domain_radius {radius}',
        f'_extinction.mosaic_spread {spread}',
        f'_extinction.crystal_radius {crystal}',
    ]


# A crystal radius that follows the domain radius, cryspy's single radius (mm = um / 1000).
SINGLE_RADIUS = (
    '\nloop_\n_alias.id\n_alias.parameter_unique_name\n'
    'crystal_radius {experiment}.extinction.crystal_radius\n'
    'domain_radius {experiment}.extinction.domain_radius\n'
    '\nloop_\n_constraint.id\n_constraint.expression\n'
    'crystal_radius "crystal_radius = domain_radius / 1000"\n'
)


def shared_extinction(runs: list[str], items: tuple[str, ...]) -> str:
    """The aliases and constraints that give every experiment the first one's extinction items.

    An alias is FullProf's short name with the experiment's number, x11_2 for the second
    experiment's coefficient_11, and a constraint's id is its left-hand alias.
    """
    if not items or len(runs) < 2:
        return ''

    def alias(number: int, item: str) -> str:
        return f'{item.replace("coefficient_", "x")}_{number}'

    aliases = [
        f'{alias(number, item)} {run}.extinction.{item}'
        for number, run in enumerate(runs, 1)
        for item in items
    ]
    constraints = [
        f'{alias(number, item)} "{alias(number, item)} = {alias(1, item)}"'
        for number in range(2, len(runs) + 1)
        for item in items
    ]
    return (
        '\nloop_\n_alias.id\n_alias.parameter_unique_name\n'
        + ''.join(line + '\n' for line in aliases)
        + '\nloop_\n_constraint.id\n_constraint.expression\n'
        + ''.join(line + '\n' for line in constraints)
    )


def tied_extinction(spec: dict) -> tuple | dict | None:
    """A later experiment's extinction: the items it takes from the first written without "()".

    A constrained parameter is dependent, so marking it free only draws a warning at load.
    """
    extinction, shared = spec['extinction'], spec.get('shared_extinction', ())
    if not isinstance(extinction, dict):
        return extinction
    return {
        item: value.removesuffix('()') if item in shared else value
        for item, value in extinction.items()
    }


def write_case_pages(root: Path, pid: str, spec: dict) -> None:
    """Write a catalogue case's index.md and PROVENANCE.md (edi ADR-0048)."""
    case = {
        key: [line.format(lib=DIFFRACTION_LIB, repo=DATA_REPOSITORY) for line in value]
        if isinstance(value, list)
        else value.format(lib=DIFFRACTION_LIB, repo=DATA_REPOSITORY)
        for key, value in CASES[pid].items()
    }
    data = root / pid / 'data' / spec['data']
    digest = hashlib.sha256(data.read_bytes()).hexdigest()
    (root / pid / 'index.md').write_text(
        f"""---
title: "{case['heading']}"
description: >-
  {case['lede']}
---

# {case['heading']}

{case['lede']}

The app lists it as **{spec['title']}**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/{pid}/project --dry` (fits
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [{pid}](../../tutorials/{pid}.ipynb) loads this project and works
  through it.

All three read the same files, in `docs/user/cli/{pid}/project`.

## The start

{case['start']}

## Sources

Where the data and the model come from, with the data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/{pid}/PROVENANCE.md).
""",
        encoding='utf-8',
    )
    differences = '\n'.join(f'- {line}' for line in case['differences'])
    (root / pid / 'PROVENANCE.md').write_text(
        f"""# {pid} — provenance

{case['lede']}

## Sources

- **Model:** {case['model']}
- **Data:** {case['data']} Its sha256 is `{digest}`.

## Start

Built by `tools/cli_projects/build_sc_projects.py`: {case['start_detail']}

## Differences from the source

{differences}

## Result from this start (local diagnostic)

{case['result']}
""",
        encoding='utf-8',
    )


def read_int(path: Path) -> tuple[float, list[tuple[int, int, int, str, str]]]:
    """Return the wavelength and the (h, k, l, F², su) rows of a FullProf .int file."""
    lines = path.read_text(encoding='utf-8').splitlines()
    wavelength = float(lines[2].split()[0])
    rows = []
    for line in lines[3:]:
        fields = line.split()
        if len(fields) < 5:
            continue
        rows.append((
            int(fields[0]),
            int(fields[1]),
            int(fields[2]),
            fields[3],
            fields[4],
            fields[6] if len(fields) > 6 else None,
        ))
    return wavelength, rows


def read_datasets(path: Path) -> dict[str, list[tuple[int, int, int, str, str, str | None]]]:
    """Return a FullProf .int file's (h, k, l, F², su, wavelength) rows by its column 6 dataset."""
    datasets: dict[str, list[tuple[int, int, int, str, str, str | None]]] = {}
    for line in path.read_text(encoding='utf-8').splitlines()[3:]:
        fields = line.split()
        # A reflection with no su (FullProf's forbidden ones, which it excludes) has no weight.
        if len(fields) < 7 or not float(fields[4]) > 0:
            continue
        datasets.setdefault(fields[5], []).append((
            int(fields[0]),
            int(fields[1]),
            int(fields[2]),
            fields[3],
            fields[4],
            fields[6],
        ))
    return dict(sorted(datasets.items(), key=lambda item: int(item[0])))


def read_data(path: Path) -> list[tuple[int, int, int, str, str, str | None]]:
    """Return the (h, k, l, F², su, wavelength) rows of a case's data file.

    The file is FullProf's .int, or the data repository's h k l F² su [wavelength] columns.
    """
    if path.suffix == '.int':
        return read_int(path)[1]
    rows = []
    for line in path.read_text(encoding='utf-8').splitlines():
        fields = line.split()
        if len(fields) < 5 or fields[0].startswith('#'):
            continue
        rows.append((
            int(fields[0]),
            int(fields[1]),
            int(fields[2]),
            fields[3],
            fields[4],
            fields[5] if len(fields) > 5 else None,
        ))
    return rows


def included(path: Path) -> set[tuple[int, int, int]]:
    """Return the reflections a FullProf .out lists without its `Excl` mark."""
    lines = path.read_text(encoding='utf-8').splitlines()
    start = next(n for n, line in enumerate(lines) if 'F2obs' in line and 'F2cal' in line)
    kept = set()
    for line in lines[start + 1 :]:
        fields = line.split()
        try:
            key = (int(fields[0]), int(fields[1]), int(fields[2]))
        except (ValueError, IndexError):
            break
        if 'Excl' not in line:
            kept.add(key)
    return kept


def number(text: str) -> str:
    """A FullProf number as the .edi writes it (no leading-dot form)."""
    value = float(text)
    return repr(value) if value != int(value) else str(int(value))


def quoted(text: str | None) -> str:
    return f'"{text}"' if text else '?'


def write_project(root: Path, pid: str, spec: dict) -> None:  # noqa: PLR0914 — one file per block, written in order
    project = root / pid / 'project'
    for sub in ('structures', 'experiments', 'analysis'):
        (project / sub).mkdir(parents=True, exist_ok=True)
    wavelength, rows = read_int(FP / spec['source'])
    if 'data' in spec:
        rows = read_data(root / pid / 'data' / spec['data'])
    if 'select' in spec:
        kept = included(FITTED / spec['select'])
        rows = [row for row in rows if row[:3] in kept]
    name = spec['structure']
    experiment = spec.get('experiment', name)
    (project / 'project.edi').write_text(
        '_edi.schema_version 3\n\n'
        f'_metadata.name             {pid if "data" in spec else pid.replace("-", "_")}\n'
        f'_metadata.title "{spec["title"]}"\n'
        f'_metadata.description "{spec["description"]}"\n'
        + ('_metadata.authors .\n' if 'data' in spec else '')
        + '_metadata.created          "22 Oct 2026 18:00:00"\n'
        '_metadata.last_modified    "22 Oct 2026 18:00:00"\n'
        '_metadata.timestamp        ?\n'
        f'_metadata.purpose "{spec.get("purpose", "verification")}"\n'
        '_metadata.dimensionality "1D"\n'
        f'_metadata.instrument {quoted(spec.get("instrument"))}\n'
        f'_metadata.facility {quoted(spec.get("facility"))}\n'
        '_metadata.polarisation "none"\n',
        encoding='utf-8',
    )
    # One experiment, or one per dataset of a FullProf file, each with its own scale.
    if 'datasets' in spec:
        by_dataset = read_datasets(root / pid / 'data' / spec['data'])
        runs = [
            (f'{experiment}_{code}', scale, dataset_rows)
            for (code, dataset_rows), scale in zip(
                by_dataset.items(), spec['datasets'], strict=True
            )
        ]
    else:
        runs = [(experiment, spec['scale'], rows)]
    (project / 'analysis' / 'analysis.edi').write_text(
        '_edi.schema_version 3\n\n'
        f'_fitting_mode.type {"joint" if len(runs) > 1 else "single"}\n\n'
        + (
            f'_refine_ls.threshold_sigma {spec["fit_cutoff"]}\n\n'
            if spec.get('fit_cutoff') is not None
            else ''
        )
        + 'loop_\n_joint_fit.experiment_id\n_joint_fit.weight\n'
        + ''.join(f'{run} 1\n' for run, _, _ in runs)
        + (SINGLE_RADIUS.format(experiment=experiment) if spec.get('single_radius') else '')
        + shared_extinction([run for run, _, _ in runs], spec.get('shared_extinction', ())),
        encoding='utf-8',
    )
    group, code = spec['space_group']
    a, b, c, al, be, ga = spec['cell']
    text = [
        f'data_{name}',
        '',
        '_edi.schema_version 3',
        '',
        f'_cell.length_a {a}',
        f'_cell.length_b {b}',
        f'_cell.length_c {c}',
        f'_cell.angle_alpha {al}',
        f'_cell.angle_beta {be}',
        f'_cell.angle_gamma {ga}',
        '',
        f'_space_group.name_h_m "{group}"',
    ]
    if code:
        text.append(f'_space_group.coord_system_code {code}')
    text += [
        '',
        'loop_',
        '_atom_site.id',
        '_atom_site.type_symbol',
        '_atom_site.fract_x',
        '_atom_site.fract_y',
        '_atom_site.fract_z',
        '_atom_site.wyckoff_letter',
        '_atom_site.occupancy',
        '_atom_site.adp_type',
        '_atom_site.adp_iso',
    ]
    aniso = []
    for sid, typ, x, y, z, w, occ, adp_type, adp_iso, beta in spec['sites']:
        text.append(f'{sid} {typ} {x} {y} {z} {w} {occ} {adp_type} {adp_iso or "0"}')
        if beta:
            aniso.append(f'{sid} ' + ' '.join(beta))
    if aniso:
        text += [
            '',
            'loop_',
            '_atom_site_aniso.id',
            '_atom_site_aniso.adp_11',
            '_atom_site_aniso.adp_22',
            '_atom_site_aniso.adp_33',
            '_atom_site_aniso.adp_12',
            '_atom_site_aniso.adp_13',
            '_atom_site_aniso.adp_23',
            *aniso,
        ]
    (project / 'structures' / f'{name}.edi').write_text('\n'.join(text) + '\n', encoding='utf-8')
    beam_mode = 'time-of-flight' if spec.get('tof') else 'constant wavelength'
    for index, (run, scale, run_rows) in enumerate(runs):
        run_spec = spec if index == 0 else {**spec, 'extinction': tied_extinction(spec)}
        write_experiment(project, run_spec, (run, name, scale), run_rows, (beam_mode, wavelength))


def write_experiment(
    project: Path, spec: dict, names: tuple[str, str, str], rows: list, beam: tuple[str, float]
) -> None:
    """Write one single-crystal experiment file: its (experiment, structure, scale) names."""
    experiment, name, scale = names
    beam_mode, wavelength = beam
    text = [
        f'data_{experiment}',
        '',
        '_edi.schema_version 3',
        '',
        '_experiment_type.sample_form "single crystal"',
        f'_experiment_type.beam_mode "{beam_mode}"',
        '_experiment_type.radiation_probe "neutron"',
        '_experiment_type.scattering_type "bragg"',
        '_scattering_source.neutron_scattering_length sears1992',
        '',
        '_calculator.type crysta',
        '',
        *(
            []
            if spec.get('tof')
            else [f'_instrument.setup_wavelength {number(str(wavelength))}', '']
        ),
        *extinction_lines(spec['extinction']),
        '',
        'loop_',
        '_linked_structure.structure_id',
        '_linked_structure.scale',
        f'{name} {scale}',
        '',
        'loop_',
        '_refln.id',
        '_refln.index_h',
        '_refln.index_k',
        '_refln.index_l',
        '_refln.intensity_meas',
        '_refln.intensity_meas_su',
        *(['_refln.wavelength'] if spec.get('tof') else []),
    ]
    for index, (h, k, ell, f2, su, lam) in enumerate(rows, start=1):
        text.append(
            f'{index} {h} {k} {ell} {number(f2)} {number(su)}'
            + (f' {number(lam)}' if spec.get('tof') else '')
        )
    (project / 'experiments' / f'{experiment}.edi').write_text(
        '\n'.join(text) + '\n', encoding='utf-8'
    )


def write_references(root: Path, pid: str) -> None:
    """Write a verification project's expected.json and PROVENANCE.md from its reference fit.

    The reference is FullProf's own fit of the same parameters on the same reflections, or, for
    the Becker-Coppens extinction FullProf does not have, the independent closed-form fit.
    """
    reference_id = PROJECTS[pid].get('reference', pid)
    becker_coppens = BECKER_COPPENS / reference_id
    folder = becker_coppens if becker_coppens.is_dir() else FITTED / reference_id
    reference = json.loads((folder / 'expected.json').read_text(encoding='utf-8'))
    artifact = '../../../../' + folder.relative_to(ROOT).as_posix() + '/'
    reference['source'] = {
        'engine': reference['source']['engine'],
        'artifact': artifact + reference['source']['artifact'],
        'provenance': 'PROVENANCE.md',
    }
    (root / pid / 'expected.json').write_text(
        json.dumps(reference, indent=2) + '\n', encoding='utf-8'
    )
    rows = '\n'.join(
        f'| `{name}` | {item["kind"]} | {item["value"]} | '
        + ', '.join(f'{key} {item[key]}' for key in ('tol_abs', 'tol_rel') if key in item)
        + ' |'
        for name, item in reference['quantities'].items()
    )
    if becker_coppens.is_dir():
        source = (
            'the Becker-Coppens closed form (Becker and Coppens, Acta Cryst. A30, 1974) applied '
            "to FullProf's unextincted F2 and fitted to the same reflections with the same free "
            'parameters, computed once by a tool independent of edi and crysta. FullProf has no '
            'Becker-Coppens sphere model, so its own fit cannot be the reference'
        )
        bounds = 'Each parameter bound is one s.u. of that fit'
    else:
        source = "FullProf's own fit of the same parameters on the same reflections"
        bounds = (
            "The scale's tolerance is FullProf's own uncertainty plus half its last printed digit"
        )
    (root / pid / 'PROVENANCE.md').write_text(
        f"""# {pid}: provenance

Built by `tools/cli_projects/build_sc_projects.py` from FullProf's files for the matching
diffraction-lib verification page (`tests/fixtures/single_crystal/fullprof/`). The structure,
extinction and starting scale are the page's FullProf values; the measured reflections are its
`.int` file. The parameters the page frees are free.

## Which values are references

Every value comes from {source} (`{artifact}`, see the `README.md` there), never from edi or
crysta.

| quantity | kind | value | tolerance |
| --- | --- | --- | --- |
{rows}

{bounds}; the reduced chi-square is the residual sum over N - p.
""",
        encoding='utf-8',
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--out', type=Path, default=ROOT / 'docs' / 'user' / 'cli')
    parser.add_argument('ids', nargs='*')
    args = parser.parse_args()
    projects = {**PROJECTS, **FIT_PROJECTS}
    unknown = set(args.ids) - set(projects)
    if unknown:
        parser.error(f'unknown project ids: {sorted(unknown)}')
    for pid, spec in projects.items():
        if not args.ids or pid in args.ids:
            write_project(args.out, pid, spec)
            if pid in PROJECTS:
                write_references(args.out, pid)
            else:
                write_case_pages(args.out, pid, spec)
            print('wrote', pid)
    return 0


if __name__ == '__main__':
    sys.exit(main())
