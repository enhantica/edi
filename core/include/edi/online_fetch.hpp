// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <string>
#include <string_view>
#include <vector>

#include "edi/online_index.hpp"

/// Reading a collection's files, once for every interface (ADR-0075). The core decides which location to read, when
/// to fall back, whether the bytes are the ones the index records, where they go and how a project archive is
/// unpacked. An interface supplies the transport: it reads the URL the core names and reports the bytes or the failure.
namespace edi::online {

/// The SHA-256 of `bytes`, lowercase hex.
std::string sha256_hex(std::string_view bytes);

/// How `bytes` differ from the file the index records: not at all, in size, or in digest (size is checked first).
enum class Mismatch { none, size, digest };
Mismatch content_mismatch(std::string_view bytes, const File& file);
/// The same as a sentence naming the file `name`, or empty when the bytes match.
std::string content_problem(std::string_view bytes, const File& file, const std::string& name);

/// The address of `path` at a location: a base URL or a folder.
std::string location_url(const std::string& base, const std::string& path);

/// One file read from a collection's locations in order (ADR-0068). Drive it until `done()`: read `url()`, then report
/// `answered(bytes)` or `failed(message, outage)`. The next location is tried only after an outage; an answer, such as
/// a 404, ends the read. With an expected file the bytes are checked and a mismatch ends the read too.
class FileRead {
   public:
    FileRead(std::vector<std::string> bases, std::string path);
    FileRead(std::vector<std::string> bases, const File& expected);
    bool done() const noexcept { return done_; }
    /// The URL to read next; valid while not done.
    const std::string& url() const noexcept { return url_; }
    void answered(std::string bytes);
    void failed(const std::string& message, bool outage);
    /// After done: whether the bytes arrived and passed the checks, the bytes, the location that served them, or why
    /// the read stopped and whether that was because every location was unreachable.
    bool ok() const noexcept { return done_ && error_.empty(); }
    const std::string& bytes() const noexcept { return bytes_; }
    const std::string& served_by() const noexcept { return served_by_; }
    const std::string& error() const noexcept { return error_; }
    bool unreachable() const noexcept { return unreachable_; }

   private:
    void next();
    std::vector<std::string> bases_;
    std::string path_;
    bool check_ = false;
    File expected_;
    std::size_t position_ = 0;
    bool done_ = false, unreachable_ = false;
    std::string url_, bytes_, served_by_, error_;
};

/// The entries a listing shows, numbered from 1 in this order: by id, as diffraction-lib lists its data, except that
/// tutorials keep the index's learning order.
std::vector<const Entry*> listing(const Index& index, const std::string& kind = {});

/// The entry a user names: an id, or a number from `listing(index, kind)`. Refuses an unknown id or a number out of
/// range, naming what is valid. A number is a row on screen, never stored.
const Entry& resolve(const Index& index, const std::string& name, const std::string& kind = {});

/// Where an entry's file goes under `destination`: the file itself, `<destination>/<file name>`, and for a project
/// archive the folder it is unpacked into, `<destination>/<entry id>-<first 12 digest characters>` (the id alone when
/// the index records no digest), so a replaced archive never reuses an old folder.
struct Placement {
    std::string file;
    std::string folder;  ///< empty unless the file is a project archive to unpack
};
Placement placement(const std::string& destination, const Entry& entry, const File& file);

/// Store verified bytes at their placement and answer the path a user opens: the unpacked project folder for an
/// archive, else the file. An existing file or folder is kept unless `overwrite`; a kept file must still match the
/// index, or it is replaced.
std::string store(const Placement& where, const File& file, std::string_view bytes, bool overwrite);

/// The path `store` would answer if a placement can be used without reading anything: the unpacked project folder, or
/// the file when it exists and matches the index; empty otherwise.
std::string stored(const Placement& where, const File& file);

}  // namespace edi::online
