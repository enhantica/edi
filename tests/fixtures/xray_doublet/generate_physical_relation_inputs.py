"""Seal authored affine relation inputs for the native diagnostic boundary.

No engine is imported. Physical intervals and all expressions live in the
visible trial_domains authoring source; values are inputs, never goldens.
"""

import argparse
import shutil
import subprocess
from pathlib import Path

import trial_domains

FAMILIES = ('ratio', 'second-line', 'polarization', 'monochromator', 'march-fraction')


def main():
    output = [
        '#pragma once\n#include <array>\n',
        'namespace physical_relation_inputs {\n',
        (
            'struct Input { const char* name; const char* target; const char* structure; '
            'const char* experiment; const char* analysis; };\n'
        ),
        'inline const std::array<Input, 5> inputs{{\n',
    ]
    for family in FAMILIES:
        structure, experiment, analysis = trial_domains.texts(family, source_kind='chain')
        data = (
            '\nloop_\n_data.two_theta\n_data.intensity_meas'
            '\n_data.intensity_meas_su\n20 1 1\n40 1 1\n60 1 1\n'
        )
        fields = (family, trial_domains.CASES[family][0], structure, experiment + data, analysis)
        output.append('{' + ',\n'.join('R"input(' + text + ')input"' for text in fields) + '},\n')
    output.append('}};\n}  // namespace physical_relation_inputs\n')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--clang-format', default=shutil.which('clang-format'))
    args = parser.parse_args()
    if not args.clang_format:
        parser.error('--clang-format is required when clang-format is not on PATH')
    rendered = subprocess.run(
        [args.clang_format, '--assume-filename=physical_relation_inputs.hpp'],
        input=''.join(output),
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    Path(__file__).with_name('physical_relation_inputs.hpp').write_text(rendered)


if __name__ == '__main__':
    main()
