// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <functional>
#include <stdexcept>
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

/// The entries a listing shows, numbered from 1 in diffraction-lib's order: entries with an `order` (a tutorial's
/// learning order) first, by it, then the rest by id.
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
    bool keep_edited = false;  ///< a tutorial: an existing file is the user's and is kept unless overwriting
};
/// The name a downloaded file gets: the last component of its path in the collection, admitted by safe_relative_path.
std::string file_name(const File& file);

/// Where an entry's file goes: every name in it is one admitted segment (edi/safe_names.hpp), so each place is a
/// direct child of `destination`.
Placement placement(const std::string& destination, const Entry& entry, const File& file);

/// Store verified bytes at their placement and answer the path a user opens: the unpacked project folder for an
/// archive, else the file. An existing file or folder is kept unless `overwrite`; a kept data file must still match
/// the index or it is replaced, while an existing tutorial is kept as it is, since the user may have edited it.
std::string store(const Placement& where, const File& file, std::string_view bytes, bool overwrite);

/// The path `store` would answer if a placement can be used without reading anything: the unpacked project folder, or
/// the file when it exists and matches the index; empty otherwise.
std::string stored(const Placement& where, const File& file);


/// EasyDiffraction's collection, in the order it is read: GitHub, then the mirror (ADR-0068).
const std::vector<std::string>& default_collection_sources();
/// Where the documentation publishes its tutorials index (ADR-0075).
const std::string& default_tutorials_source();
/// The locations to read: `source` alone when given, else the environment variable `variable` (EDI_COLLECTION or
/// EDI_TUTORIALS) when set, else `defaults`.
std::vector<std::string> sources_for(const std::string& source, const char* variable,
                                     const std::vector<std::string>& defaults);

/// What a blocking transport answers for one URL: the bytes, or why not and whether that was an outage.
struct Reply {
    bool ok = false;
    std::string bytes;
    std::string error;
    bool outage = false;
};
using Transport = std::function<Reply(const std::string& url)>;

/// Every location of a read was unreachable.
struct Unreachable : std::runtime_error {
    using std::runtime_error::runtime_error;
};

/// A file path or `file://` URL read from disk: a missing file is an outage, the offline stand-in for a host that
/// does not answer. Transports use it for anything that is not http(s).
Reply read_local(const std::string& url);

/// Drive `read` to its end through `transport`: the bytes, with the location that served them in `served`. Throws
/// Unreachable when no location could be reached, std::invalid_argument for an answer or a failed check.
std::string read_through(FileRead read, const Transport& transport, std::string* served = nullptr);

/// A collection's `index.json` from `sources`; the location that served it moves to the front of `sources`, so the
/// files are read from it first.
std::string read_index(std::vector<std::string>& sources, const Transport& transport);

/// Copy or download the entry `id`'s first file, unchanged, into the folder `into` and answer its path; an existing file
/// there is replaced. The same placement and writer as `download`, without unpacking an archive.
std::string fetch(const std::vector<std::string>& sources, const std::string& index_text, const std::string& id,
                  const std::string& into, const Transport& transport);

/// Download the entry `name` (an id or a listing number of `kind`) and answer the path a user opens. The file of
/// `format` is taken, or the entry's first. A kept file or folder is reused unless `overwrite` (see `store`).
std::string download(const std::vector<std::string>& sources, const std::string& index_text, const std::string& name,
                     const std::string& kind, const std::string& format, const std::string& destination,
                     bool overwrite, const Transport& transport);

}  // namespace edi::online
