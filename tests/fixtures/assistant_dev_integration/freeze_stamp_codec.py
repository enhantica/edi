"""Freeze the pre-integration dev codec; never derive expected bytes from new code."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

BASE = 'e782d2d84a984c8d9df86e6e6c4df361baf89f2c'
ROOT = Path(__file__).resolve().parents[3]
FROZEN_CODEC_SHA256 = '8b300f35b31f9f5b9bf54a5af9e4e470255f8983817ef4f463b91d46707d7800'


def write_projection(original, reference):
    if hashlib.sha256(original.encode()).hexdigest() != FROZEN_CODEC_SHA256:
        message = 'Refusing to rebase the independently frozen stamp reference'
        raise ValueError(message)
    retired = '    put_optional_parameter(out, experiment.absorption.abscor2, scope);\n'
    if original.count(retired) != 1:
        message = 'The ADR-0123 projection requires exactly the original retired slot'
        raise ValueError(message)
    projected = original.replace(
        retired,
        '    // ADR-0123: the removed coefficient has no slot in the current model stamp.\n',
    )
    Path(__file__).with_name('prechange_stamp_codec.inc').write_text(projected)
    Path(__file__).with_name('stamp_codec_retirement.json').write_text(
        json.dumps(
            {
                'reference': reference,
                'historical_source_label': BASE,
                'decision': 'ADR-0123 removes ABSCOR2 from the model and its input stamp',
                'before': original,
                'before_sha256': hashlib.sha256(original.encode()).hexdigest(),
                'after_sha256': hashlib.sha256(projected.encode()).hexdigest(),
                'removed_statement': retired.strip(),
                'unchanged': 'Every other codec byte, peak order and independent alias binding',
                'command': (
                    'python tests/fixtures/assistant_dev_integration/freeze_stamp_codec.py '
                    '--retire-abscor2'
                ),
            },
            indent=2,
        )
        + '\n'
    )


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--retire-abscor2', action='store_true')
args = parser.parse_args()
if args.retire_abscor2:
    # The inherited pre-port commit is absent in this integrated checkout. The
    # exact committed frozen reference remains independent of today's codec.
    reference = {
        'commit': 'a0a116e1a7a11e6944978c09e249e5b6514976f4',
        'path': 'tests/fixtures/assistant_dev_integration/prechange_stamp_codec.inc',
    }
    receipt = Path(__file__).with_name('stamp_codec_retirement.json')
    recorded = json.loads(receipt.read_text()) if receipt.exists() else {}
    frozen = recorded.get('before')
    if frozen is None:
        frozen = subprocess.check_output([
            'git',
            '-C',
            str(ROOT),
            'show',
            reference['commit'] + ':' + reference['path'],
        ]).decode()
    write_projection(frozen, reference)
    raise SystemExit(0)


source = subprocess.check_output([
    'git',
    '-C',
    str(ROOT),
    'show',
    f'{BASE}:core/src/canonical_encoding.cpp',
])
text = source.decode()
slots_source = subprocess.check_output([
    'git',
    '-C',
    str(ROOT),
    'show',
    f'{BASE}:core/src/parameter_paths.cpp',
])
slots = (
    slots_source
    .decode()
    .split('const std::array<std::pair<const char*, PeakSlotField>, 14> kPeakSlots', 1)[1]
    .split('}};', 1)[0]
)
slots = (
    'using PeakSlotField = Parameter& (*)(ExperimentBase&);\n'
    'const std::array<std::pair<const char*, PeakSlotField>, 14> kPrechangePeakSlots'
    + slots
    + '}};\n'
)
text = text.replace(
    '#include "parameter_paths.hpp"  // kPeakSlots: the peak[] slot order the encoding walks', ''
)
text = text.replace('namespace edi {\nnamespace {', 'namespace edi {\nnamespace {\n' + slots)
text = text.replace('detail::kPeakSlots', 'kPrechangePeakSlots')
binding = """
// Independent prior-dev cell-name/source binding used by the alias witnesses.
// This is a deliberately finite reference, not today's production name walker.
// Non-cell aliases fail closed so this reference cannot silently omit a source.
std::vector<NamedParameter> e11_prechange_relation_sources(const Project& project) {
    std::vector<NamedParameter> out;
    for (const auto& structure : project.structures) {
        const auto prefix = structure->name.value() + ".cell.";
        out.push_back({prefix + "length_a", &structure->cell.length_a});
        out.push_back({prefix + "length_b", &structure->cell.length_b});
        out.push_back({prefix + "length_c", &structure->cell.length_c});
        out.push_back({prefix + "angle_alpha", &structure->cell.angle_alpha});
        out.push_back({prefix + "angle_beta", &structure->cell.angle_beta});
        out.push_back({prefix + "angle_gamma", &structure->cell.angle_gamma});
    }
    for (const auto& alias : project.aliases) {
        const auto found = std::find_if(out.begin(), out.end(), [&](const auto& row) {
            return row.unique_name == alias->parameter_unique_name.value();
        });
        if (found == out.end())
            throw std::invalid_argument("Unsupported frozen alias-source fixture");
    }
    // Pre-change io.cpp:4363-4370 excludes dependent alias sources.
    // Known-cell validation above remains distinct from source eligibility.
    std::erase_if(out, [](const auto& row) {
        return row.parameter->dependence != Dependence::Independent;
    });
    return out;
}
"""
text = text.replace('namespace detail {', 'namespace detail {\n' + binding)
text = text.replace('named_parameters(*project)', 'e11_prechange_relation_sources(*project)')
# Keep the original codec body. Its explicit model-template instantiations are
# already supplied by edi_core and are unrelated to the frozen byte reference.
text = text.split('// ADR-0018: the table view', 1)[0]
text = text.replace('namespace detail {', 'namespace e11_prechange_codec {')
text += '\n}  // namespace edi\n'
header = (
    '// Generated by freeze_stamp_codec.py from committed pre-integration dev.\n'
    f'// Source: {BASE}:core/src/canonical_encoding.cpp\n'
    f'// Original source SHA-256: {hashlib.sha256(source).hexdigest()}\n'
    f'// Slot-table source SHA-256: {hashlib.sha256(slots_source).hexdigest()}\n'
    '// Export namespace relocated; duplicate templates removed; '
    'peak order frozen from same dev commit.\n'
)
write_projection(header + text, {'commit': BASE, 'path': 'core/src/canonical_encoding.cpp'})
