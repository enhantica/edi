"""Gate 3: bind each final visible idea to checked, committed UI-test images.

Images are regression pins, never independent correctness references. The owner
quotations are the correctness oracle; the per-image checks record the visual
review against them. The review lane independently checks those claims.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
# Idea 10 and 18 remain covered using the final withdrawal feedback. Idea 23
# replaces the intermediate prefixed tab titles of ideas 6-8.
IDEAS = set(range(1, 28))
# Test-owned image regression pins, recorded after this lane opened every mapped
# PNG with view_image and checked every listed observation against the packet's
# final owner ideas (tests seq9, 2026-10-02); rechecked for  seq4
# via /tmp/-seq4/captures-{0..8}.jpg, including every mapped PNG.
#  seq8 rechecks 23-experiment-text.png at e6579e64: the calculator
# line is visible; the same edge-to-edge Text pane and block selector checks hold.
#  seq8 visually rechecks the three Messages captures after the Examples
# list gains lif single; all per-idea observations below still hold.
# The producer map supplies candidate observations, never its own certification;
# all accepted observations and exact image bytes are independently pinned here.
# Current profile captures were opened individually: full selector names,
# U V W X Y on one TCH row with S/L D/L below, and U V W Eta0 Eta1 on one
# BeBa row with an AsyLim value field and no adjacent fit toggle. Earlier pins
# showed separate X/Y or eta rows and abbreviated FCJ labels.
VERIFIED_CAPTURES: dict[str, dict[str, object]] = {
    '01-home.png': {
        'sha256': '9ccc7ac8480cfde64c766116d04f64ab275e1a5e7ba90e2b23e2bd68615d1618',
        'checks': {
            '2': 'the mark has the same size as in the About dialog (28-home-about.png)',
            '3': 'the logo lockup is centred as one unit and "Version demo (demo '
            'build)" is centred on its own line below it',
            '4': '"Online documentation" is listed under Start (the link target is '
            'not visible in an image)',
        },
    },
    '02-project-no-project.png': {
        'sha256': 'da207fb65a8660fd4c3f2deb88224e0bd4e37f78c319c4c6518410b3a09e2999',
        'checks': {
            '10': 'final feedback: every foldable group starts '
            'folded except Get started, which is open; '
            'Examples and Recent projects are folded',
            '11': 'Recent projects, the last group shown, has no line under it',
            '24': 'the status bar ends with the warning-triangle Messages item, count 0',
            '27': 'Get started shows four buttons two by two; "Open '
            'project from URL..." is the fourth and is '
            'disabled, as is "Save project as..."',
        },
    },
    '03-project-examples.png': {
        'sha256': '21850bff265a1e34b70b0aab12a9d49b36be8140f6742320996b4eae291aa2eb',
        'checks': {
            '10': 'final feedback: Examples was opened by a click and '
            'Get started folded; no other group is open',
            '11': 'Recent projects, the last group shown, has no line under it',
        },
    },
    '04-project-loaded.png': {
        'sha256': '97982949f28bfbea1811e7bdaf67a7767e19507ec025d30dd00bfd150e3d805a',
        'checks': {
            '6': 'the main tab reads the archive icon and the project '
            'name cosio_d20_s1, not "Description"',
            '12': 'the structure name has an orange layer-group icon and '
            'the experiment name a light-blue microscope icon',
            '21': 'Location is shown: <temporary>/pd-neut-cwl_cosio-d20_start-1/project',
            '22': 'the rows read "Structures (1)" cosio and "Experiments '
            '(1)" d20: the count in the label and the block names '
            'as the value',
            '23': 'the main tab title is an icon followed by the name',
            '26': 'the calculator decision is complete: this example '
            "declares crysta, as crysta's seed does, so it opens with no message "
            'and the Messages item counts 0',
        },
    },
    '05-model-models.png': {
        'sha256': '91d5979342d0724d973aba856d464a0eedc601ee846d31b1af4413b939ca5d52',
        'checks': {
            '7': 'the main tab reads the orange layer-group icon and the '
            'structure name cosio, not "Structure view"',
            '9': 'the block selector (number, coloured icon, name) sits '
            'above the groups, under the tab bar, on Basic',
            '12': 'the Structures table has a colour column with the '
            'orange layer-group icon before the name',
            '13': '"Define structure manually" is shown, disabled, beside '
            '"Load structure from file"',
            '19': 'loop titles are plural with their count: "Structures (1)", "Atom sites (6)"',
        },
    },
    '06-model-space-group.png': {
        'sha256': '0cf269e44b098546ce2989068cf18a3cdf4ba6500d1d2748f9b8b53d84b0997c',
        'checks': {
            '9': 'the block selector (number, coloured icon, name) '
            'sits above the groups, under the tab bar while '
            'Space group is open',
            '10': 'final feedback: only the clicked group (Space '
            'group) is open; the others are folded',
        },
    },
    '07-model-cell.png': {
        'sha256': '1baa76309d57f82faed8541a02d95718e01c6012471ec3b965f82f7a9472e112',
        'checks': {
            '9': 'the block selector (number, coloured icon, name) sits '
            'above the groups, under the tab bar while Cell is open',
            '11': 'Atom sites (6), the last group shown, has no line under it',
        },
    },
    '08-model-atom-site.png': {
        'sha256': '1c9030587aa26ea5211143793d30c5aaf0f9e7688002354b3602faabe066d14d',
        'checks': {
            '9': 'the block selector (number, coloured icon, name) sits '
            'above the groups, under the tab bar while Atom sites '
            'is open',
            '19': 'the loop title is plural with its count: "Atom sites (6)"',
        },
    },
    '09-model-text-mode.png': {
        'sha256': '20debd4b735770632a77c507d6befb48a2e6c9b1acac0333852d38d8e4c4115c',
        'checks': {
            '5': 'the text view fills the sidebar width from under the '
            'selector to the bottom; Continue floats over the text',
            '9': 'the same block selector is shown on the Text tab, with the border line under it',
        },
    },
    '10-experiment-experiments.png': {
        'sha256': '4967329083db717ce6004ccc96070b11b36292ab5caec47479c296667e84492b',
        'checks': {
            '8': 'the main tab reads the microscope icon in the '
            'experiment colour and the experiment name, no '
            'word (d20), not "Chart view"',
            '9': 'the block selector (number, coloured icon, '
            'name) sits above the groups, under the tab '
            'bar, on Basic',
            '12': 'the Experiments table has a colour column '
            'with the light-blue microscope icon before '
            'the name',
            '13': '"Define experiment manually" is shown, '
            'disabled, beside "Load experiment(s) from '
            'file(s)"',
            '19': 'the loop title is plural: "Linked structures '
            '(1)"; "Background (14)" keeps its name by the '
            "owner's exception",
            '25': 'the chart area shows only the grey '
            'placeholder and the points line, no red '
            'text',
        },
    },
    '11-experiment-profile-shape.png': {
        'sha256': '99da03332047aeb94bb144fa3fe4b8bbac16c38ccc852e1cf476c158443afefa',
        'checks': {
            '18': 'withdrawn; final feedback: Peak profile has '
            'no subheadings; U V W are on one row and X '
            'Y on the next'
        },
    },
    '12-experiment-background.png': {
        'sha256': '8d2310480c9b47b02a6116ef7429d06ae30dff83572c6e5d97139c6c619f4622',
        'checks': {
            '17': '"Reset to autodetected background" is shown, '
            'disabled, beside "Append new point"',
            '19': 'the title is "Background (14)", the plural rule\'s exception',
        },
    },
    '13-analysis-basic.png': {
        'sha256': '134839f8323fa4ba24e5c771324958cd2f9c4eca316cd2eef697e068f31f92e9',
        'checks': {
            '9': 'the experiment selector reads number, light-blue '
            'microscope icon and name, as the shared block selector',
            '12': 'each parameter name is iconified: the orange '
            'structure icon, the category icon, the parameter '
            'icon, then the bold short name; Co1 has the atom icon '
            'and label in its element colour',
        },
    },
    '14-analysis-extra-minimizer.png': {
        'sha256': 'b32a903a8ce5143c67653f89114b9ea0fbdb214027a16898ea187b8389754698',
        'checks': {
            '10': 'final feedback: only the clicked group (Minimizer) is open',
            '11': 'Joint-fit weights (1), the last group shown, has no line under it',
            '19': 'the loop title is plural with its count: "Joint-fit weights (1)"',
        },
    },
    '15-summary.png': {
        'sha256': 'c236caa2d98c6783ee768c455ba1e7f7d9b82516468ec358afc15d83afe5ac21',
        'checks': {
            '24': 'the status bar ends with the Messages item on the Report page too; '
            'this project opens without a message, so it counts 0'
        },
    },
    '16-summary-preferences.png': {
        'sha256': 'b735df5034ddcb06ef1c6e5347eb00ec04a150e10a9dddca9e1696c271eedbba',
        'checks': {
            '24': 'Preferences shows the dialog frame (title, '
            'content, OK at the bottom right) that the '
            'Messages dialog repeats '
            '(t4-04-messages-list.png)'
        },
    },
    '17-experiment-profile-selector.png': {
        'sha256': '01809fd6ed10a8b2e10c1540885a09fcd67737053b4b3af65cc81b0324318472',
        'checks': {
            '8': 'the main tab reads the microscope icon in the experiment colour and '
            'the experiment name, no word (hrpt)',
            '18': 'withdrawn; final feedback: the profile list opens over a group with '
            'no subheading',
            '3': 'the profile list names each profile in full: Gaussian, Lorentzian, '
            'Pseudo-Voigt, Pseudo-Voigt + Bérar\u2013Baldinozzi asymmetry, '
            'Thompson\u2013Cox\u2013Hastings pseudo-Voigt (TCH), and the TCH with '
            'Finger\u2013Cox\u2013Jephcoat asymmetry (FCJ)',
        },
    },
    '18-experiment-tch.png': {
        'sha256': 'b2fffb665f81b7a6b94049e42a326ec4e166cdb02cf06fd238f5417b8ab458b5',
        'checks': {
            '18': 'withdrawn; final feedback: Thompson-Cox-Hastings shows U V W X Y on '
            'one row, then S/L D/L, with no "Broadening" or "Asymmetry" '
            'subheading'
        },
    },
    '19-experiment-extras.png': {
        'sha256': '329beec8a14b249099a957bb73df2d4635832e02db62c9091b6fb3156b338353',
        'checks': {
            '9': 'the block selector (number, coloured icon, name) '
            'sits above the groups, under the tab bar, on Extras '
            'as on Basic',
            '10': 'final feedback: every group on the tab starts folded',
            '11': 'Scattering source, the last group shown, has no line under it',
            '15': 'the group is titled "Measured data (3098)" and is the first group on Extras',
            '19': 'loop titles are plural: "Excluded regions (2)", "Preferred orientations (1)"',
        },
    },
    '20-experiment-tof.png': {
        'sha256': '700ff711649ea32e3580f582b2f07ddb8133eabb0486f36b6ac985ada868e809',
        'checks': {
            '18': 'withdrawn; final feedback: Jorgensen-Von Dreele shows '
            'a0 a1 b0 b1, then s0 s1 s2 size G strain G, then g0 '
            'g1 g2 size L strain L, five wide, with no '
            'subheading'
        },
    },
    '21-structure-extras.png': {
        'sha256': 'af04d8d8bcc7884d0019c75c097a2c5cf99cb74f346b87121e7a5d0bab883ab4',
        'checks': {
            '9': 'the block selector (number, coloured icon, name) '
            'sits above the groups, under the tab bar, on the '
            "Structure page's Extras tab",
            '19': 'the loop title is plural with its count: "Scattering lengths (0)"',
        },
    },
    '22-analysis-fitting-mode.png': {
        'sha256': 'fdd75d2c19f139a520fa355a65ed29914f136de3a10b6c07f18dae3eeb3b3474',
        'checks': {
            '11': 'Joint-fit weights (1), the last group shown, has no line under it',
            '19': 'the loop title is plural: "Joint-fit weights (1)"',
        },
    },
    '23-experiment-text.png': {
        'sha256': 'ea21b78a1340a18eab990527dfa319d144a09013094213dd4b56060e7a75d27d',
        'checks': {
            '5': 'the text view fills the sidebar width from under the '
            'selector to the bottom; Continue floats over the text',
            '9': 'the same block selector is shown on the Experiment '
            "page's Text tab, with the border line under it",
        },
    },
    '24-analysis-text.png': {
        'sha256': '8e8b88f7393cc2c08c9e05563f1a45fbd5ea7203f974147752fb6b3e3ee35f1d',
        'checks': {
            '5': 'the text view runs edge to edge from the tab bar to the '
            "sidebar's bottom; Continue floats over it"
        },
    },
    '25-report-tof.png': {
        'sha256': '1fea2745757a0cf4ca075e8249922d8f97f9807786883b52fba1a81bd6c1a9df',
        'checks': {
            '24': 'the status bar ends with the Messages item; this project opens '
            'without a message, so it counts 0'
        },
    },
    '26-experiment-loaded.png': {
        'sha256': '458bee4576742af6efd24c63230ab0b294c507e7284bf059f6f18658650f5ab1',
        'checks': {
            '12': 'the second experiment takes the second experiment '
            'colour (brown) in the tab title and the selector',
            '24': 'the Messages item counts 1 not-viewed message (the refusal), in red',
            '25': 'the calculation is refused, yet the chart area '
            'shows only the grey placeholder, no red text',
        },
    },
    '27-experiment-xray.png': {
        'sha256': '304ead8396ad8f09e8259e7b570b64c94466514142195c96da2311eb58d49e51',
        'checks': {
            '9': 'the block selector (number, coloured icon, name) sits '
            'above the groups, under the tab bar, on Extras',
            '11': 'Scattering source, the last group shown, has no line under it',
            '19': 'loop titles are plural: "Excluded regions (0)", "Preferred orientations (0)"',
        },
    },
    '28-home-about.png': {
        'sha256': '9b04cd6b37551c663af3591c794d914614be92cf9de2dd5fb725f48b66220b49',
        'checks': {
            '1': "the description is the owner's idea-1 sentence "
            '(`ApplicationInfo.description`), read word for word, on '
            'three lines of similar width',
            '2': 'the mark has the same size as on the Home page (01-home.png)',
            '3': 'the logo lockup is centred and "Version demo (demo build)" '
            'is centred on its own line, not grouped under the name',
        },
    },
    'ex-pd-neut-cwl_cosio-d20_scan-324f.png': {
        'sha256': '1fbe212628c05f7eb972c1ae259724c8874dce1fe1370c2ee59e07cc44573040',
        'checks': {
            '8': 'the main tab reads the microscope '
            'icon in the experiment colour and the '
            'experiment name, no word',
            '9': 'the block selector (number, coloured '
            'icon, name) sits above the groups, '
            'under the tab bar, on Basic',
            '18': 'Peak profile (cwl-tch-pseudo-voigt) has '
            'no subheading; its fields run U V W '
            'on one row and X Y on the next',
        },
    },
    'ex-pd-neut-cwl_cosio-d20_scan-3f.png': {
        'sha256': '39b445a7747b2a291ec2003bf80aca1592b555caad0f88ebbbacb60811336e57',
        'checks': {
            '8': 'the main tab reads the microscope icon '
            'in the experiment colour and the '
            'experiment name, no word',
            '9': 'the block selector (number, coloured '
            'icon, name) sits above the groups, '
            'under the tab bar, on Basic',
            '18': 'Peak profile (cwl-tch-pseudo-voigt) has no '
            'subheading; its fields run U V W on '
            'one row and X Y on the next',
            '24': 'the Messages item counts 1 not-viewed '
            'message (the "crysta (lm)" minimizer '
            'warning), in red',
        },
    },
    'ex-pd-neut-cwl_cosio-d20_start-1.png': {
        'sha256': 'f3b3182e99c3ed5ac47f4f892e3857ce13c6db2905b5da88b1fc5148a054eb8f',
        'checks': {
            '8': 'the main tab reads the microscope icon '
            'in the experiment colour and the '
            'experiment name, no word',
            '9': 'the block selector (number, coloured '
            'icon, name) sits above the groups, '
            'under the tab bar, on Basic',
            '18': 'Peak profile (cwl-tch-pseudo-voigt) has no '
            'subheading; its fields run U V W on '
            'one row and X Y on the next',
        },
    },
    'ex-pd-neut-cwl_cosio-d20_start-4.png': {
        'sha256': 'f9641620270cb76f271a4a167af72e1cd90d84a0031dc8fc76ae635e03cbdb0f',
        'checks': {
            '8': 'the main tab reads the microscope icon '
            'in the experiment colour and the '
            'experiment name, no word',
            '9': 'the block selector (number, coloured '
            'icon, name) sits above the groups, '
            'under the tab bar, on Basic',
            '18': 'Peak profile (cwl-tch-pseudo-voigt) has no '
            'subheading; its fields run U V W on '
            'one row and X Y on the next',
        },
    },
    'ex-pd-neut-cwl_lab6-echidna_fcj-asymmetry.png': {
        'sha256': 'c0c49bf8250c7b4a4d30072a9f050ab114cefa0a4b3d9690355bf683e23c8881',
        'checks': {
            '8': 'the main tab reads the '
            'microscope icon in the '
            'experiment colour and the '
            'experiment name, no word',
            '9': 'the block selector (number, '
            'coloured icon, name) sits '
            'above the groups, under the '
            'tab bar, on Basic',
            '18': 'Peak profile '
            '(cwl-tch-pseudo-voigt-fcj) '
            'has no subheading; its fields '
            'run U V W, then X Y, then '
            'asym fcj1 fcj2, a row per '
            'family',
        },
    },
    'ex-pd-neut-cwl_lbco-hrpt_start-2.png': {
        'sha256': 'ff5e751ffb9d7314cbe323edcbbcf09f2c405e263b1617c8321768b1c3183970',
        'checks': {
            '8': 'the main tab reads the microscope icon '
            'in the experiment colour and the '
            'experiment name, no word',
            '9': 'the block selector (number, coloured '
            'icon, name) sits above the groups, '
            'under the tab bar, on Basic',
            '18': 'Peak profile (cwl-tch-pseudo-voigt) has no '
            'subheading; its fields run U V W on '
            'one row and X Y on the next',
        },
    },
    'ex-pd-neut-cwl_lbco-hrpt_start-4.png': {
        'sha256': 'b226624a1b18109156129c418867185157152383e820cf615aee1210fa5f2631',
        'checks': {
            '8': 'the main tab reads the microscope icon '
            'in the experiment colour and the '
            'experiment name, no word',
            '9': 'the block selector (number, coloured '
            'icon, name) sits above the groups, '
            'under the tab bar, on Basic',
            '18': 'Peak profile (cwl-tch-pseudo-voigt) has no '
            'subheading; its fields run U V W on '
            'one row and X Y on the next',
        },
    },
    # Independently inspected committed images: explicit mixing and both phase tick rows.
    'ex-pd-neut-cwl_pbso4_beba-asymmetry.png': {
        'sha256': '1254d25f8845c438f57f91bf8fd7dbc686b3ade42b4b90dd9a23612806ea6bb2',
        'checks': {
            '8': 'the main tab reads the microscope icon in the experiment colour and '
            'the experiment name, no word',
            '9': 'the block selector (number, coloured icon, name) sits above the '
            'groups, under the tab bar, on Basic',
            '18': 'Peak profile (cwl-pseudo-voigt-berar-baldinozzi) has no subheading; '
            'its fields run U V W Eta0 Eta1 on one row, then A0 B0 A1 B1 AsyLim '
            'on the asymmetry row, AsyLim editable with no fit toggle',
        },
    },
    'ex-pd-neut-cwl_yap-spodi_3k.png': {
        'sha256': 'ecc321f3e9257db09fc81654a8d9c239341551d6d2d98ada599ccfbc1cc3abe1',
        'checks': {
            '8': 'the main tab reads the microscope icon in the experiment colour and '
            'the experiment name, no word',
            '9': 'the block selector (number, coloured icon, name) sits above the '
            'groups, under the tab bar, on Basic',
            '18': 'Peak profile (cwl-pseudo-voigt-berar-baldinozzi) has no subheading; '
            'its fields run U V W Eta0 Eta1 on one row, then A0 B0 A1 B1 AsyLim '
            'on the asymmetry row, AsyLim editable with no fit toggle; the chart '
            'shows a row of Bragg ticks for each of the two structures',
        },
    },
    'ex-pd-neut-tof_diamond-dream_basic.png': {
        'sha256': '76b98128f0a186412e689ce9cc11714f936063afe0d502567d58ac7a8540d5ee',
        'checks': {
            '8': 'the main tab reads the microscope '
            'icon in the experiment colour and the '
            'experiment name, no word',
            '9': 'the block selector (number, coloured '
            'icon, name) sits above the groups, '
            'under the tab bar, on Basic',
            '18': 'Peak profile (tof-jorgensen) has no '
            'subheading; its fields run a0 a1 b0 '
            'b1, then s0 s1 s2 size G strain G, '
            'with no Lorentzian row',
        },
    },
    'ex-pd-neut-tof_fe_pseudo-voigt.png': {
        'sha256': '6ca177f7a6ec04a5562439fb469cb27a9852a80543aac62cc847343392f032e1',
        'checks': {
            '8': 'the main tab reads the microscope icon in '
            'the experiment colour and the experiment '
            'name, no word',
            '9': 'the block selector (number, coloured '
            'icon, name) sits above the groups, under '
            'the tab bar, on Basic',
            '18': 'Peak profile (tof-pseudo-voigt) has no '
            'subheading; its fields run s0 s1 s2 size '
            'G strain G, then g0 g1 g2 size L strain '
            'L; the rise and decay fields the profile '
            'does not use are not shown',
            '26': 'the example that always has messages: '
            'the Messages item counts 3 not viewed, '
            'in red',
        },
    },
    'ex-pd-neut-tof_ncaf-wish-2bank_start-3.png': {
        'sha256': 'be25f6152e0f95c0b193ce834960adc314a2801e023969f83314cf1d64142333',
        'checks': {
            '8': 'the main tab reads the microscope '
            'icon in the experiment colour and '
            'the experiment name, no word',
            '9': 'the block selector (number, '
            'coloured icon, name) sits above '
            'the groups, under the tab bar, on '
            'Basic',
            '18': 'Peak profile (tof-jorgensen) has '
            'no subheading; its fields run a0 '
            'a1 b0 b1, then s0 s1 s2 size G '
            'strain G, with no Lorentzian '
            'row',
        },
    },
    'ex-pd-neut-tof_ncaf-wish-3bank_start-5.png': {
        'sha256': '34f08383e8421d982733748d9e4387726329e2646306c5a0228c36c97917822c',
        'checks': {
            '8': 'the main tab reads the microscope '
            'icon in the experiment colour and '
            'the experiment name, no word',
            '9': 'the block selector (number, '
            'coloured icon, name) sits above '
            'the groups, under the tab bar, on '
            'Basic',
            '18': 'Peak profile '
            '(tof-jorgensen-von-dreele) has '
            'no subheading; its fields run a0 '
            'a1 b0 b1, then s0 s1 s2 size G '
            'strain G, then g0 g1 g2 size L '
            'strain L, five wide',
        },
    },
    'ex-pd-neut-tof_ncaf-wish-5bank_start-5.png': {
        'sha256': 'e79601b94e638b6b642a8108a0d51d4d7e64984d152ec2058c159e106895ebc6',
        'checks': {
            '8': 'the main tab reads the microscope '
            'icon in the experiment colour and '
            'the experiment name, no word',
            '9': 'the block selector (number, '
            'coloured icon, name) sits above '
            'the groups, under the tab bar, on '
            'Basic',
            '18': 'Peak profile '
            '(tof-jorgensen-von-dreele) has '
            'no subheading; its fields run a0 '
            'a1 b0 b1, then s0 s1 s2 size G '
            'strain G, then g0 g1 g2 size L '
            'strain L, five wide',
        },
    },
    'ex-pd-neut-tof_ncaf-wish-5bank_start-fullprof.png': {
        'sha256': '66849d3eb003a1e34dd8b3a655d10e7c7b7d02c6bb1fe91c230194886946725a',
        'checks': {
            '8': 'the main tab reads the '
            'microscope icon in the '
            'experiment colour and the '
            'experiment name, no word',
            '9': 'the block selector '
            '(number, coloured icon, '
            'name) sits above the '
            'groups, under the tab bar, '
            'on Basic',
            '18': 'Peak profile '
            '(tof-jorgensen-von-dreele) '
            'has no subheading; its '
            'fields run a0 a1 b0 b1, '
            'then s0 s1 s2 size G '
            'strain G, then g0 g1 g2 '
            'size L strain L, five '
            'wide',
        },
    },
    'ex-pd-neut-tof_si-sepd_start-2.png': {
        'sha256': '9f1ad7ae6359e04dad9a45fddf4b6c44bb489bfa5fb881e08fd4f6ed356dc5db',
        'checks': {
            '8': 'the main tab reads the microscope icon in '
            'the experiment colour and the experiment '
            'name, no word',
            '9': 'the block selector (number, coloured '
            'icon, name) sits above the groups, under '
            'the tab bar, on Basic',
            '18': 'Peak profile (tof-jorgensen-von-dreele) '
            'has no subheading; its fields run a0 a1 '
            'b0 b1, then s0 s1 s2 size G strain G, '
            'then g0 g1 g2 size L strain L, five '
            'wide',
        },
    },
    'ex-pd-neut-tof_si-sepd_start-5.png': {
        'sha256': 'f792b3fec95a2c663d5f32ca83a2f4f2fddfa0c2d5237e71dc31c5added88a12',
        'checks': {
            '8': 'the main tab reads the microscope icon in '
            'the experiment colour and the experiment '
            'name, no word',
            '9': 'the block selector (number, coloured '
            'icon, name) sits above the groups, under '
            'the tab bar, on Basic',
            '18': 'Peak profile (tof-jorgensen-von-dreele) '
            'has no subheading; its fields run a0 a1 '
            'b0 b1, then s0 s1 s2 size G strain G, '
            'then g0 g1 g2 size L strain L, five '
            'wide',
        },
    },
    'ex-pd-xray-cwl_lif.png': {
        'sha256': 'a9cb06857c463364ed76c9d3171f46afd114d3962780403ce493b4e744c71c94',
        'checks': {
            '8': 'the main tab reads the microscope icon in the '
            'experiment colour and the experiment name, no word',
            '9': 'the block selector (number, coloured icon, name) sits '
            'above the groups, under the tab bar, on Basic',
            '18': 'Peak profile (cwl-tch-pseudo-voigt) has no subheading; '
            'its fields run U V W on one row and X Y on the next',
            '15': 'a calculation-only experiment has "Calculation '
            'range" on Basic and no Measured data group',
        },
    },
    't2-01-instrument-cw.png': {
        'sha256': '4db69458fe562cb62c636e39a8e95fc80bbbffd6f90c94ce31e8179b62f766ba',
        'checks': {
            '9': 'the block selector (number, coloured icon, name) '
            'sits above the groups, under the tab bar while '
            'Instrument is open',
            '19': 'titles: "Background (14)" above Instrument, and "Linked structures (1)" plural',
        },
    },
    't2-02-linked-structure.png': {
        'sha256': '44e6f722dbe965960477dcdb7d63edcc518ccb1b48a27f51e98ff50d51e03518',
        'checks': {
            '19': 'the loop title is plural with its count: "Linked structures (1)"',
            '20': "the row shows the linked structure's orange "
            'layer-group icon before its name cosio, then the '
            'scale and a (disabled) remove button',
        },
    },
    't2-03-experiment-extras-peak.png': {
        'sha256': '3bfd80be9751cb97ad3c8e977b0012a3ef941cfd93545c717b7561154e996adc',
        'checks': {
            '11': 'Reflections (237), the last group shown, has no line under it',
            '15': 'the group is titled "Measured data (1418)" and is the first group on Extras',
            '19': 'loop titles are plural: "Excluded regions '
            '(0)", "Preferred orientations (0)", '
            '"Reflections (237)"',
        },
    },
    't2-04-analysis-slider.png': {
        'sha256': '87745913aaa33153d152848038743c531164b9a1a8390138b7cf84989f9cbd58',
        'checks': {
            '12': 'parameter names are iconified (structure icon in '
            'orange, category icon, parameter icon, bold short '
            'name); the Co1 atom icon and label are in the '
            'element colour'
        },
    },
    't2-05-report-text.png': {
        'sha256': 'fddc3115bab37dfdf06e5782a37719a3edc0a5af92a2e67afd8d893acc6095a9',
        'checks': {
            '5': "the Report page's Text view fills the sidebar from the "
            'tab bar to the bottom, edge to edge'
        },
    },
    't2-06-dark-experiment.png': {
        'sha256': 'fe678fadc9352c8fa9f6d000b191a48e8687abe768f012bcdf32c7be07c2654b',
        'checks': {
            '12': 'dark theme: the experiment icon is the light-blue '
            'dark-theme tone in the tab title and the selector',
            '20': 'dark theme: the linked structure row shows the '
            "layer-group icon in the structure's dark-theme "
            'orange before cosio',
        },
    },
    't2-07-dark-analysis.png': {
        'sha256': '6a2afc735064c8c3aca0add9112331430c7ba1249494946ae03f71c8265cb114',
        'checks': {
            '12': 'dark theme: parameter names keep their icons; the '
            'structure icon is the dark-theme orange and Co1 its '
            'element colour'
        },
    },
    't2-08-dark-structure-text.png': {
        'sha256': 'd0f0c8d01a81a523cf0ce67a45dd68398e884162754a263716b41c0800b12456',
        'checks': {
            '5': 'dark theme: the text view fills the sidebar '
            'under the selector; Continue floats over the '
            'text',
            '9': 'dark theme: the block selector is shown on the Text tab',
        },
    },
    't2-09-system-dark-report.png': {
        'sha256': 'cb367cff5f83ccc2f26fb3e96a1e0307e8f3505de7fba1e10b0bbc71aa91fd6c',
        'checks': {
            '24': 'system theme on a dark platform: the status bar ends with the '
            'Messages item; this project opens without a message, so it counts 0'
        },
    },
    't2-10-system-light-report.png': {
        'sha256': 'fddc3115bab37dfdf06e5782a37719a3edc0a5af92a2e67afd8d893acc6095a9',
        'checks': {
            '24': 'system theme on a light platform: the status bar ends with the '
            'Messages item; this project opens without a message, so it counts 0'
        },
    },
    't2-11-project-text.png': {
        'sha256': '419b983f3dfa710fdb2f4c808e11d7898c0c51235a107079f0749fddddb075f6',
        'checks': {
            '5': "the Project page's Text view fills the sidebar from "
            'the tab bar to the bottom; Continue floats over it',
            '6': 'the main tab reads the archive icon and the project name',
            '21': 'Location is shown: <temporary>/pd-neut-cwl_cosio-d20_start-1/project',
            '22': 'the rows read "Structures (1)" cosio and "Experiments (1)" d20',
        },
    },
    't2-12-measured-data.png': {
        'sha256': 'c2e5d6720f4b2269661e8ec6e925cf90238bec79ea4ea159d8a9396bdb8d7ae9',
        'checks': {
            '15': 'the group is titled "Measured data (1418)", not '
            '"Measured range", over the summary fields and the '
            'points table',
            '16': 'inc shows a range, "0.1-0.3" (drawn with an en '
            "dash), because this scan's steps differ",
        },
    },
    't2-13-reflections.png': {
        'sha256': 'b08bfbde856690cc5c3c631b401344437c6740fe43de9ed3b878335a79e43f89',
        'checks': {
            '11': 'Reflections (237), the last group shown, has no line under it',
            '19': 'the loop title is plural with its count: "Reflections (237)"',
        },
    },
    't2-14-joint-fit.png': {
        'sha256': 'a3cf61af511cb984fa4d8dcad9049ed72e9ebae7112777b347857ed9923a418e',
        'checks': {
            '12': "the row shows the experiment's light-blue microscope icon before d20",
            '19': 'the loop title is plural with its count: "Joint-fit weights (1)"',
        },
    },
    't2-15-scan-extraction.png': {
        'sha256': '7fe5300b3adcf6b6c0d31e84f37ae695fc2c1eb3e095bd22c3955fe2e9657a30',
        'checks': {
            '19': 'loop titles are plural: "Scan extraction rules (1)", "Fit start values (39)"'
        },
    },
    't2-16-fit-start.png': {
        'sha256': 'f949df9b6e60a05a428a5ed49a828c373f98e0e7e4bfb86ed6b77407622cb2d1',
        'checks': {
            '11': 'Fit start values (39), the last group shown, has no line under it',
            '19': 'the loop title is plural with its count: "Fit start values (39)"',
        },
    },
    't2-17-instrument-cw-four.png': {
        'sha256': 'e3efc665d5b4228f983e99549f35f8d0b6f2d00b5a54ea3ef92f1d74b0358c75',
        'checks': {
            '9': 'the block selector shows the second experiment, "2 d20_shifted", with its icon',
            '12': 'the second experiment takes the second '
            'experiment colour (brown) in the tab title and '
            'the selector',
        },
    },
    't4-01-experiment-type.png': {
        'sha256': '8f8a7abc2ad75423ffe8ff38a4bdea9062a23dd2081ba0cda743e495f6a688d1',
        'checks': {
            '14': 'Experiment type is a grid three wide: sample '
            'form, beam mode and probe on the first row, '
            'scattering type on the second, leaving two free '
            'places'
        },
    },
    't4-02-measured-data-uniform.png': {
        'sha256': '9ca7a5b5e28a93d524eb8ac489e7a9d91d9e3e8c6a8097eb3ce6927a46fffb36',
        'checks': {
            '15': 'the group is titled "Measured data (3098)"',
            '16': 'inc shows one value, 0.05, because every step of this pattern is equal',
        },
    },
    't4-03-messages-not-viewed.png': {
        'sha256': 'e2bac9df2bb47860036cea07b8f800f1195e53913c839c1809a2cc389710ec01',
        'checks': {
            '21': 'Location is shown for the example: '
            '<temporary>/pd-neut-tof_fe_pseudo-voigt/project',
            '22': 'the rows read "Structures (1)" fe and "Experiments (1)" beer',
            '24': "the status bar's last item shows the number of not-viewed messages, 3, in red",
            '26': 'the example kept with unsupported values has three messages on opening',
        },
    },
    't4-04-messages-list.png': {
        'sha256': '91449f52ce34a9457ebb35dbb5e88d3bbb60bbf5a3758a966a5dff427ac6abfa',
        'checks': {
            '24': 'a click opened the Messages dialog: a framed list, '
            'one row per message with its own dismiss button, '
            '"Dismiss all" beside OK; the status-bar count is '
            'now 0',
            '26': 'the three rows are the unsupported calculator "cryspy", the '
            'unsupported minimizer "bumps (lm)" and the unsupported plot renderer '
            '"plotly"; a save writes the calculator as crysta, '
            'which no capture shows',
        },
    },
    't4-05-messages-viewed.png': {
        'sha256': 'd983ca8f4cdf1ecc6a97a50364941d5c5db86848365dd2481a28e52318296508',
        'checks': {
            '24': 'after the dialog is closed the not-viewed count '
            'is 0, in the normal colour, not red'
        },
    },
    't4-06-messages-error.png': {
        'sha256': '59860889023c93d15bd0961573aef3733750044c16d54ccedfa87c764692e500',
        'checks': {
            '24': 'the list holds a warning row (orange triangle) '
            'and, apart from it, an error row (red circle, red '
            'text)',
            '25': 'the refused calculation is in the central list '
            '("Calculation refused: ..."), and the Experiment '
            'view behind keeps only its grey placeholder',
        },
    },
}


def read(path):
    reference = os.environ.get('EDI_E04_T4_SOURCE_REF')
    if reference:
        result = subprocess.run(
            ['git', '-C', str(ROOT), 'show', f'{reference}:{path}'],
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, f' gate 3: committed capture evidence must exist at {path}'
        return result.stdout
    target = ROOT / path
    assert target.is_file(), f' gate 3: checked capture evidence must exist at {path}'
    return target.read_bytes()


def test_every_final_visible_idea_has_checked_capture_evidence():
    # Same map location convention as the prior  captures. No generated
    # list of production ideas is used as the expected set.
    payload = json.loads(read('docs/dev/design/app-example-captures.json'))
    assert isinstance(payload, list) and payload, (
        ' gate 3: capture map must contain per-image checked records'
    )
    covered = set()
    images = set()
    for row in payload:
        assert isinstance(row, dict), ' gate 3: each capture record is a mapping'
        image = row.get('image', '')
        assert isinstance(image, str) and image.endswith('.png') and '/' not in image, (
            ' gate 3: each image is a local UI-test PNG basename'
        )
        assert image not in images, ' gate 3: each capture is checked exactly once'
        images.add(image)
        verified = VERIFIED_CAPTURES.get(image)
        assert verified is not None, (
            f' gate 3: capture {image} requires an independent tests-lane visual check '
            'against its owner ideas before its bytes become a regression pin'
        )
        checks = row.get('checks')
        assert isinstance(checks, dict) and checks, (
            ' gate 3: each image carries checks against its specific ideas'
        )
        for idea, check in checks.items():
            assert idea.isdecimal() and int(idea) in IDEAS, (
                ' gate 3: capture checks name final owner idea numbers'
            )
            assert isinstance(check, str) and len(check.strip()) >= 20, (
                ' gate 3: each idea has a concrete visual observation'
            )
            covered.add(int(idea))
        assert row.get('sha256') == verified['sha256'] and checks == verified['checks'], (
            ' gate 3: producer claims must equal the independently checked image pins '
            'and per-idea observations'
        )
        content = read('docs/dev/design/app-screenshots/edi/' + image)
        assert content.startswith(b'\x89PNG\r\n\x1a\n'), (
            ' gate 3: checked artifact must be a PNG image'
        )
        assert hashlib.sha256(content).hexdigest() == row.get('sha256'), (
            ' gate 3: observations must name the exact reviewed PNG bytes'
        )
    assert images == set(VERIFIED_CAPTURES), (
        ' gate 3: every final capture must have exactly one independent visual check'
    )
    assert covered == IDEAS, (
        f' gate 3: final owner ideas missing checked captures: {sorted(IDEAS - covered)}'
    )


def test_message_demo_example_retains_independent_unsupported_inputs():
    # The owner explicitly widened idea 26 to three or more messages. An app
    # screenshot cannot supply the input oracle: inspect the committed .edi files.
    directory = 'docs/user/cli/pd-neut-tof_fe_pseudo-voigt/project/'
    analysis = read(directory + 'analysis/analysis.edi').decode()
    assert '_minimizer.type "bumps (lm)"' in analysis, (
        'idea 26: the demo example must deliberately declare the unsupported minimizer'
    )
    experiment = read(directory + 'experiments/beer.edi').decode()
    assert '_calculator.type cryspy' in experiment, (
        'idea 26: the demo example must deliberately declare the unsupported calculator'
    )


def test_producer_cannot_self_certify_or_replace_checked_image_pins(monkeypatch):
    # A retained pre-task image is a negative/regression control, never an
    # independent correctness oracle for the new About composition.
    content = (ROOT / 'docs/dev/design/app-screenshots/edi/28-home-about.png').read_bytes()
    image = 'producer-self-certification-control.png'
    checks = {
        str(idea): 'Synthetic control observation for the independent owner idea.'
        for idea in IDEAS
    }
    record = {'image': image, 'sha256': hashlib.sha256(content).hexdigest(), 'checks': checks}
    supplied = [record]
    supplied_bytes = content

    def source(path):
        return json.dumps(supplied).encode() if path.endswith('.json') else supplied_bytes

    module = sys.modules[__name__]
    monkeypatch.setattr(module, 'read', source)
    monkeypatch.setattr(module, 'VERIFIED_CAPTURES', {})
    with pytest.raises(AssertionError, match='requires an independent tests-lane visual check'):
        test_every_final_visible_idea_has_checked_capture_evidence()

    # Synthetic authoritative pin exercises retention only, not visual truth.
    monkeypatch.setattr(module, 'VERIFIED_CAPTURES', {image: copy.deepcopy(record)})
    test_every_final_visible_idea_has_checked_capture_evidence()
    supplied_bytes = content + b'changed producer image'
    with pytest.raises(AssertionError, match='exact reviewed PNG bytes'):
        test_every_final_visible_idea_has_checked_capture_evidence()
    supplied[0]['sha256'] = hashlib.sha256(supplied_bytes).hexdigest()
    with pytest.raises(AssertionError, match='independently checked image pins'):
        test_every_final_visible_idea_has_checked_capture_evidence()
    supplied_bytes = content
    supplied[0]['sha256'] = hashlib.sha256(content).hexdigest()
    supplied[0]['checks']['1'] = 'A producer substitutes an unchecked About observation.'
    with pytest.raises(AssertionError, match='independently checked image pins'):
        test_every_final_visible_idea_has_checked_capture_evidence()
