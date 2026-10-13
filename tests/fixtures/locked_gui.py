"""Acquire only the declared GUI base before the disconnected consumer configure."""

import hashlib
import subprocess
from pathlib import Path


def gui_source(root, scratch, prefix):
    selected = root / 'build/app/_deps/gui_components-src'
    if selected.is_dir():
        return selected
    adapter = root / 'cmake/EdiGuiBase.cmake'
    # A changed acquisition/pin recipe gets its own build tree. CMake revalidates reused sources.
    scratch /= hashlib.sha256(adapter.read_bytes()).hexdigest()
    project, build = scratch / 'project', scratch / 'build'
    project.mkdir(parents=True, exist_ok=True)
    (project / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.26)\n'
        'project(LockedGuiPrerequisite NONE)\n'
        'function(qt_add_library)\nendfunction()\n'
        'function(qt_add_qml_module)\nendfunction()\n'
        'function(qt_add_resources)\nendfunction()\n'
        f'include("{adapter.as_posix()}")\n'
        'file(WRITE "${CMAKE_BINARY_DIR}/selected-source.txt" '
        '"${gui_components_SOURCE_DIR}")\n'
    )
    subprocess.run(
        [str(prefix / 'bin/cmake'), '-S', str(project), '-B', str(build)],
        check=True,
        capture_output=True,
        text=True,
    )
    # This is prerequisite acquisition, using the real adapter's URL/hash/tree checks.
    # The subsequent real Qt configure keeps FULLY_DISCONNECTED and all package assertions.
    selected = (build / 'selected-source.txt').read_text().strip()
    selected = Path(selected)
    if (
        not selected.is_absolute()
        or not selected.is_dir()
        or not selected.resolve().is_relative_to(build.resolve())
    ):
        raise RuntimeError('GUI acquisition must return its actual private populated source tree')
    return selected
