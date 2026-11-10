"""The Qt/Emscripten version seam refuses wrong and absent recommendations."""

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ('recommended', 'accepted'), [('4.0.7', True), ('4.0.8', False), ('', False)]
)
def test_qt_recommendation_enforces_the_exact_packet_pin(tmp_path, recommended, accepted):
    source = ROOT / 'tools/ci/wasm-env.sh'
    assert source.is_file(), 'requires a reusable fail-closed wasm toolchain pin check'
    kit = tmp_path / 'kit/lib/cmake/Qt6'
    kit.mkdir(parents=True)
    (kit / 'QtPublicWasmToolchainHelpers.cmake').write_text(
        f'set(QT_EMCC_RECOMMENDED_VERSION "{recommended}")\n' if recommended else ''
    )
    result = subprocess.run(
        [
            'bash',
            '-c',
            'source "$1"; wasm_check_emsdk_pin "$2"',
            'e04-pin-gate',
            str(source),
            str(tmp_path / 'kit'),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert (result.returncode == 0) == accepted, (
        'only Qt recommendation exactly 4.0.7 may pass; missing or different versions must refuse'
    )
    if not accepted:
        assert result.stderr.strip(), 'a toolchain-version refusal must give a visible reason'
