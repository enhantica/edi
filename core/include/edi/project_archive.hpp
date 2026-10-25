// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <string>
#include <string_view>
#include <utility>
#include <vector>

// A project's `.zip` archive (edi ADR-0052): one archive of the whole project folder, its members
// named relative to the folder, so every surface writes the same archive and reads every other's.
// The desktop app, the web app, the command line and Python all use these functions.

namespace edi {

// The files a project archive holds, as archive member names ('/'-separated, relative to
// `directory`), sorted: every regular file under the folder except build and cache files: hidden
// names (any path component starting with '.'), `build` and `__pycache__` folders, compiled Python
// (`*.pyc`) and a save's staged files (`*.edi-staged`). Throws IoError when `directory` is not a
// directory.
std::vector<std::string> project_archive_members(const std::string& directory);

// The archive of the project folder `directory`, as bytes. Each member is deflated and carries its
// file's modification time. Throws IoError when a file cannot be read.
std::string project_archive_bytes(const std::string& directory);

// An archive of the given members (name, bytes), in that order, each deflated: what the browser
// downloads when it hands over several files at once. Throws IoError.
std::string archive_bytes(const std::vector<std::pair<std::string, std::string>>& members);

// Write the archive of the project folder `directory` to `archive`, replacing it. Refuses an
// archive inside the folder. Throws IoError.
void write_project_archive(const std::string& directory, const std::string& archive);

// Unpack an archive's bytes into `target` (created when absent) and return the project folder in
// it: `target` when `project.edi` is at the archive's top, or its one top folder holding
// `project.edi`. Every member name is checked before anything is written: an absolute name, a
// drive, a backslash or a `..` component is outside the project folder and refuses the whole
// archive. A link is not unpacked. Throws IoError naming the member.
std::string unpack_project_archive(std::string_view bytes, const std::string& target);

// Whether `path` names a project archive: a regular file whose name ends in `.zip`, in any case.
bool is_project_archive(const std::string& path);

// A new, empty directory under the system's temporary directory for an unpacked archive; `kind`
// starts its name.
std::string fresh_archive_directory(const std::string& kind);

}  // namespace edi
