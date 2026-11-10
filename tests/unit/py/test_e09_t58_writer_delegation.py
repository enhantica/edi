"""B1: edi owns no project writer; persistence delegates to crysta."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CORE_SOURCES = tuple(sorted((ROOT / 'core/src').glob('*.cpp')))
IO_SOURCE = ROOT / 'core/src/io.cpp'
ADAPTER_SOURCE = ROOT / 'core/src/adapter.cpp'
IO_HEADER = ROOT / 'core/include/edi/io.hpp'


def _without_comments(text: str) -> str:
    return re.sub(r'//[^\n]*|/\*.*?\*/', '', text, flags=re.DOTALL)


def _function_body(text: str, signature: str) -> str:
    start = text.find(signature)
    assert start != -1, f'missing the single public {signature!r} definition'
    opening = text.find('{', start + len(signature))
    assert opening != -1, f'{signature!r} must have a function body'
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == '{':
            depth += 1
        elif text[index] == '}':
            depth -= 1
            if depth == 0:
                return text[opening + 1 : index]
    raise AssertionError(f'{signature!r} has an unterminated function body')


def test_e09_t58_edi_project_save_has_one_delegating_writer_and_no_local_serializer() -> None:
    sources = {path: _without_comments(path.read_text(encoding='utf-8')) for path in CORE_SOURCES}
    save_signature = 'void save_project(const Project& project, const std::string& directory)'
    definitions = [(path, text) for path, text in sources.items() if save_signature in text]
    assert len(definitions) == 1, (
        'edi must expose exactly one save entry point, so a second local writer cannot coexist '
        'with the delegated path'
    )
    path, source = definitions[0]
    assert path == IO_SOURCE, (
        'the single public edi save entry point must remain in core/src/io.cpp'
    )
    body = _function_body(source, save_signature)
    assert body.count('save_project_via_crysta(') == 1, (
        'core/src/io.cpp must delegate exactly once through the crysta-free adapter seam'
    )
    assert not re.search(r'\b(?:std::)?ofstream\b|\b(?:fwrite|write|rename)\s*\(', body), (
        'the public edi save body must not perform a second file write or publish'
    )
    #  names the supported minimizer in data and warnings, not C++ symbols.
    symbols = re.sub(
        r""" "(?:\\.|[^"\\])*" | '(?:\\.|[^'\\])*' """, '""', source, flags=re.VERBOSE
    )
    assert not re.search(r'(?m)^\s*#\s*include\s*[<"]crysta[/>"]', source), (
        'ADR-0003 forbids direct crysta includes even when the header uses quoted syntax'
    )
    assert not re.search(r'\bcrysta\b', symbols), (
        'ADR-0003 requires core/src/io.cpp to remain free of direct crysta symbols'
    )

    seam_signature = 'void save_project_via_crysta('
    seam_definitions = [(path, text) for path, text in sources.items() if seam_signature in text]
    assert len(seam_definitions) == 1, (
        'edi must define exactly one engine-delegation seam, so the write cannot fork again'
    )
    seam_path, seam_source = seam_definitions[0]
    assert seam_path == ADAPTER_SOURCE, (
        'ADR-0003 requires the engine-delegation seam to live in core/src/adapter.cpp'
    )
    assert IO_HEADER.read_text(encoding='utf-8').count(seam_signature) == 1, (
        'the crysta-free io.hpp boundary must declare the single adapter delegation seam'
    )
    seam_body = _function_body(seam_source, seam_signature)
    assert seam_body.count('crysta::save_project(') == 1, (
        'core/src/adapter.cpp must delegate exactly once to crysta::save_project'
    )
    assert not re.search(r'\b(?:std::)?ofstream\b|\b(?:fwrite|write|rename)\s*\(', seam_body), (
        'the adapter seam must not perform a second file write or publish beside crysta delegation'
    )

    retired_writer_symbols = {
        'format_parameter',
        'write_structure',
        'write_cwl_experiment',
        'write_experiment',
        'write_analysis',
        'StagingGuard',
    }
    joined = '\n'.join(sources.values())
    surviving = sorted(symbol for symbol in retired_writer_symbols if symbol in joined)
    assert not surviving, (
        'the retired edi serializer must be deleted, not left available to regrow the write path: '
        f'{surviving!r}'
    )
