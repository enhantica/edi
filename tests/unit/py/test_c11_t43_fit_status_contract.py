""": edi preserves crysta's complete normative fit-status vocabulary."""

from __future__ import annotations

import os
import re
from pathlib import Path

import edi

ROOT = Path(__file__).resolve().parents[3]
CRYSTA_ROOT = Path(os.environ.get('CRYSTA_CONSUMER_SRC', ROOT / 'build/crysta-src'))


def _without_cpp_comments(text: str) -> str:
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    return re.sub(r'(?m)//.*$', '', text)


def _enum_members(path: Path, enum_name: str) -> set[str]:
    text = _without_cpp_comments(path.read_text(encoding='utf-8'))
    matches = re.findall(
        rf'enum\s+class\s+{re.escape(enum_name)}\b[^{{]*{{(?P<body>.*?)}}\s*;',
        text,
        flags=re.DOTALL,
    )
    assert len(matches) == 1, (
        f' status inventory requires exactly one {enum_name} declaration in {path}'
    )
    return {
        item.split('=', 1)[0].strip()
        for item in matches[0].split(',')
        if item.split('=', 1)[0].strip()
    }


def _function_body(path: Path, signature: str) -> str:
    text = path.read_text(encoding='utf-8')
    function = re.search(
        rf'{re.escape(signature)}\s*{{(?P<body>.*?)^}}',
        text,
        flags=re.DOTALL | re.MULTILINE,
    )
    assert function is not None, f' status inventory requires {signature} in {path}'
    return function.group('body')


def _normative_vocabulary() -> set[str]:
    adr_path = CRYSTA_ROOT / 'docs/dev/adrs/0057-machine-fit-report-contract.md'
    assert adr_path.is_file(), (
        ' edi status parity requires the exact crysta source used by the consumer build '
        f'to carry ADR-0057; missing={adr_path}'
    )
    adr = adr_path.read_text(encoding='utf-8')
    lines = re.findall(r'record=(?:fit|error)\s+status\s*=\s*([^\n`]+)', adr)
    assert len(lines) == 2, (
        ' ADR-0057 must carry one record=fit and one record=error status grammar'
    )
    return {token.strip() for line in lines for token in line.split('|') if token.strip()}


def test_edi_enum_conversions_binding_and_crysta_contract_share_one_status_set() -> None:
    edi_native = _enum_members(ROOT / 'core/include/edi/model.hpp', 'FitStatus')
    to_engine = dict(
        re.findall(
            r'case\s+FitStatus::([A-Z_]+)\s*:\s*return\s+crysta::FitStatus::(\w+)\s*;',
            _function_body(
                ROOT / 'core/src/report.cpp',
                'crysta::FitStatus to_engine(FitStatus status)',
            ),
        )
    )
    to_edi = dict(
        re.findall(
            r'case\s+crysta::FitStatus::(\w+)\s*:\s*return\s+edi::FitStatus::([A-Z_]+)\s*;',
            _function_body(
                ROOT / 'core/src/adapter.cpp', 'edi::FitStatus to_edi(crysta::FitStatus status)'
            ),
        )
    )
    binding_text = (ROOT / 'lib/src/bindings.cpp').read_text(encoding='utf-8')
    bound = set(re.findall(r'\.value\("([A-Z_]+)",\s*edi::FitStatus::\1\)', binding_text))
    python = {name for name in dir(edi.FitStatus) if re.fullmatch(r'[A-Z_]+', name)}

    crysta_header = CRYSTA_ROOT / 'include/crysta/fit_report.hpp'
    crysta_native = _enum_members(crysta_header, 'FitStatus')
    label_body = _function_body(
        CRYSTA_ROOT / 'src/core/fit_report.cpp', 'const char* fit_status_label(FitStatus status)'
    )
    emitted = dict(
        re.findall(r'case\s+FitStatus::(\w+)\s*:\s*return\s+"([a-z_]+)"\s*;', label_body)
    )
    normative = _normative_vocabulary()

    assert crysta_native == set(emitted) == set(to_edi), (
        ' crysta enum, label formatter, and edi inbound switch must cover one mechanical '
        f'set; native={sorted(crysta_native)!r}, emitted={sorted(emitted)!r}, '
        f'to_edi={sorted(to_edi)!r}'
    )
    assert edi_native == set(to_engine) == set(to_edi.values()) == bound == python, (
        ' edi enum, both conversion switches, and Python binding must cover one '
        f'mechanical set; native={sorted(edi_native)!r}, to_engine={sorted(to_engine)!r}, '
        f'to_edi={sorted(to_edi.values())!r}, bound={sorted(bound)!r}, '
        f'python={sorted(python)!r}'
    )
    assert all(to_edi[engine] == surface for surface, engine in to_engine.items()), (
        ' edi status conversions must be exact inverses for every mechanically '
        'discovered enum value'
    )
    assert 'UNAVAILABLE' in edi_native, (
        ' edi must expose UNAVAILABLE as a non-trivial status value'
    )
    assert emitted.get(to_engine['UNAVAILABLE']) == 'unavailable', (
        ' edi UNAVAILABLE must reach the emitted status=unavailable wire label'
    )
    assert set(emitted.values()) == normative, (
        ' every status crossing either edi conversion switch must resolve in ADR-0057 '
        f'normative vocabulary; emitted={sorted(emitted.values())!r}, '
        f'normative={sorted(normative)!r}'
    )
