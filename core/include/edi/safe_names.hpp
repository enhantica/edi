// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <filesystem>
#include <string>
#include <string_view>

/// The one way a name that comes from outside becomes a path (ADR-0075). It admits a grammar and refuses everything
/// else. Every rule refuses an empty, `.` or `..` segment, a segment ending in a dot or space, and a Windows device
/// name (CON, PRN, AUX, NUL, COM0-9, LPT0-9, and COM or LPT with a superscript 1-3) in any case, with any extension or
/// trailing spaces before it. A nested name joins segments with single '/' and is at most 1024 bytes.
namespace edi {

enum class NameRule {
    /// Collection file names, project folders and the archives a collection serves: ASCII letters, digits, '.', '_'
    /// and '-', starting and ending with a letter, digit, '_' or '-', at most 128 bytes a segment.
    collection,
    /// A collection entry id: the collection grammar in one segment of at most 115 bytes, so that the project folder
    /// `<id>-<12 digest characters>` built from it is still an admitted collection name.
    entry_id,
    /// A project archive edi writes or opens for the user: Unicode scalar values in UTF-8 (no overlong form,
    /// surrogate or value above U+10FFFF) except control characters and / \ : * ? " < > |, at most 255 bytes a
    /// segment, so a user's own file names (accents, spaces, a leading dot) survive a save and reopen.
    project,
};

/// Whether `name` is admitted under `rule`: one segment, or '/'-joined segments when `nested`.
bool admitted_name(std::string_view name, bool nested = false, NameRule rule = NameRule::collection);

/// `name` fit to show in a message: valid UTF-8 as it is, any other byte and any control character as \xHH.
std::string shown_name(std::string_view name);

/// `name` as a relative path; throws std::invalid_argument naming it when it is not admitted.
std::filesystem::path safe_relative_path(std::string_view name, bool nested = false,
                                         NameRule rule = NameRule::collection);

}  // namespace edi
