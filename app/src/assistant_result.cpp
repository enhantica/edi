// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_result.hpp"
#include <limits>
#include "edi/assistant.hpp"
#include "edi/io.hpp"
// Reuse the existing strict parser, preserving member order for duplicate checks below.
#include "../../core/src/assistant_json.hpp"
#include "../../core/src/assistant_project_io.hpp"
#include <QCryptographicHash>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QSaveFile>
#include <QStringView>
#include <QScopeGuard>
#include <charconv>
#include <QJsonObject>
#include <QJsonDocument>
#include <QStandardPaths>
#include <QUuid>
#include <algorithm>
#include <array>
#include <string_view>
#include <cmath>
#include <map>
#include <optional>
#include <set>
#include <stdexcept>
#include <utility>
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
#include <cerrno>
#include <cstring>
#include <dirent.h>
#include <limits.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#if defined(__linux__)
#include <sys/syscall.h>
#include <linux/fs.h>
#elif defined(__APPLE__)
#include <stdio.h>
#endif
#elif defined(Q_OS_WIN)
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <io.h>
#endif

namespace edi_app {
void validate_assistant_result_leaf(const QString& name) {
    using Bounds = edi::assistant::SelectedFileLimits;
    // A well-formed name has no more UTF-16 units than its UTF-8 bytes.
    // Admit that fixed outer bound before encoding, then require an exact
    // round trip: malformed surrogate text must never name a different file.
    if (name.isEmpty() || name.size() > static_cast<qsizetype>(Bounds::name_bytes) || name == "." || name == ".." ||
        name.contains('/') || name.contains('\\') || name.contains(QChar(0)) || name.endsWith('.') || name.endsWith(' '))
        throw std::runtime_error("Saved assistant result is unavailable, changed, or outside the supported self-contained project limits");
    const auto encoded = name.toUtf8(); // At most four bytes per admitted code unit.
    if (encoded.isEmpty() || encoded.size() > static_cast<qsizetype>(Bounds::name_bytes) || QString::fromUtf8(encoded) != name)
        throw std::runtime_error("Saved assistant result is unavailable, changed, or outside the supported self-contained project limits");
}

namespace {
using Bounds = edi::assistant::SelectedFileLimits;
using Limits = edi::assistant::Limits;
[[noreturn]] void refuse() { throw std::runtime_error("Saved assistant result is unavailable, changed, or outside the supported self-contained project limits"); }

QString relative_name(const std::string& bytes, bool carried = false) {
    if (bytes.empty() || bytes.size() > Bounds::name_bytes) refuse();
    const auto name = QString::fromUtf8(bytes.data(), static_cast<qsizetype>(bytes.size()));
    if (name.toUtf8() != QByteArray(bytes.data(), static_cast<qsizetype>(bytes.size())) || name.startsWith('/')) refuse();
    const auto parts = name.split('/');
    if (parts.size() > static_cast<qsizetype>(Limits::json_depth)) refuse();
    for (const auto& part : parts) validate_assistant_result_leaf(part);
    if (carried) return name;
    // Provider results retain the original fixed native project layout.
    if (name == "project.edi") return name;
    if (parts.size() != 2 || !parts[1].endsWith(".edi") || parts[1].size() <= 4 ||
        !(parts[0] == "structures" || parts[0] == "experiments" ||
          (parts[0] == "analysis" && parts[1] == "analysis.edi") ||
          (parts[0] == "reports" && parts[1] == "report.edi"))) refuse();
    return name;
}
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
struct Fd {
    int n = -1;
    Fd() = default;
    explicit Fd(int fd) : n(fd) { if (n < 0) refuse(); }
    ~Fd() { if (n >= 0) ::close(n); }
    Fd(Fd&& other) noexcept : n(std::exchange(other.n, -1)) {}
    Fd& operator=(Fd&& other) noexcept { if (n >= 0) ::close(n); n = std::exchange(other.n, -1); return *this; }
    Fd(const Fd&) = delete;
};
struct Identity {
    struct stat value{};
    explicit Identity(int fd) { if (::fstat(fd, &value)) refuse(); }
    bool object(int fd) const { struct stat now{}; return !::fstat(fd, &now) && value.st_dev == now.st_dev && value.st_ino == now.st_ino && value.st_mode == now.st_mode; }
    bool unchanged(int fd) const {
        struct stat now{};
        if (::fstat(fd, &now)) return false;
#if defined(__APPLE__)
        const bool times = value.st_mtimespec.tv_sec == now.st_mtimespec.tv_sec && value.st_mtimespec.tv_nsec == now.st_mtimespec.tv_nsec &&
            value.st_ctimespec.tv_sec == now.st_ctimespec.tv_sec && value.st_ctimespec.tv_nsec == now.st_ctimespec.tv_nsec;
#else
        const bool times = value.st_mtim.tv_sec == now.st_mtim.tv_sec && value.st_mtim.tv_nsec == now.st_mtim.tv_nsec &&
            value.st_ctim.tv_sec == now.st_ctim.tv_sec && value.st_ctim.tv_nsec == now.st_ctim.tv_nsec;
#endif
        return object(fd) && value.st_size == now.st_size && times;
    }
};
Fd physical_directory(const QString& path) {
    // Only already-captured physical paths enter here. Reject later ancestor
    // links instead of resolving unknown replacement path text.
    if (!QDir::isAbsolutePath(path)) refuse();
    Fd fd(::open("/", O_RDONLY | O_DIRECTORY | O_CLOEXEC));
    const auto view=QStringView(path);
    for(qsizetype start=0;start<view.size();) {
        while(start<view.size() && view[start]==u'/')++start;
        if(start==view.size())break;
        auto end=view.indexOf(u'/',start);if(end<0)end=view.size();
        const auto part=view.mid(start,end-start);start=end;
        if(part==u"." || part==u".." || part.contains(QChar(0)))refuse();
        fd=Fd(::openat(fd.n,part.toUtf8().constData(),O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC));
    }
    return fd;
}
Fd directory(const QString& path) {
    // Ordinary callers keep system-alias canonicalization (notably macOS
    // /var and /tmp). The same no-follow reader owns physical descent.
    if (!QDir::isAbsolutePath(path)) refuse();
    const auto physical = QFileInfo(path).canonicalFilePath();
    if (physical.isEmpty()) refuse();
    auto fd=physical_directory(physical);
    Fd original(::open(path.toUtf8().constData(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC));
    if (!Identity(fd.n).object(original.n)) refuse();
    return fd;
}
Fd below(int parent, const QString& name, bool dir = false) {
    const auto parts = name.split('/');
    Fd fd(::dup(parent));
    for (qsizetype i = 0; i < parts.size(); ++i) {
        validate_assistant_result_leaf(parts[i]);
        const bool directoryPart = i + 1 != parts.size() || dir;
        if (!directoryPart) {
            struct stat admitted{};
            if (::fstatat(fd.n, parts[i].toUtf8().constData(), &admitted, AT_SYMLINK_NOFOLLOW) || !S_ISREG(admitted.st_mode)) refuse();
        }
        fd = Fd(::openat(fd.n, parts[i].toUtf8().constData(), O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC | (directoryPart ? O_DIRECTORY : 0)));
    }
    return fd;
}
QByteArray read_file(int fd, quint64 cap) {
    const Identity original(fd);
    if (!S_ISREG(original.value.st_mode) || original.value.st_nlink != 1 || original.value.st_size < 0 || static_cast<quint64>(original.value.st_size) > cap) refuse();
    QByteArray bytes;
    bytes.reserve(static_cast<qsizetype>(original.value.st_size));
    char chunk[65536];
    for (;;) {
        const auto count = ::read(fd, chunk, sizeof chunk);
        if (count < 0) { if (errno == EINTR) continue; refuse(); }
        if (!count) break;
        if (static_cast<quint64>(count) > cap - static_cast<quint64>(bytes.size())) refuse();
        bytes.append(chunk, static_cast<qsizetype>(count));
    }
    if (bytes.size() != original.value.st_size || !original.unchanged(fd)) refuse();
    return bytes;
}
QByteArray stream_file(int input, quint64 expected, quint64 cap, int output = -1, bool reportTime = false) {
    const Identity original(input);
    if (!S_ISREG(original.value.st_mode) || original.value.st_nlink != 1 || original.value.st_size < 0 ||
        static_cast<quint64>(original.value.st_size) != expected || expected > cap) refuse();
    QCryptographicHash hash(QCryptographicHash::Sha256);
    std::array<char, Bounds::read_bytes> chunk{};
    quint64 consumed = 0;
    for (;;) {
        const auto count = ::read(input, chunk.data(), chunk.size());
        if (count < 0) { if (errno == EINTR) continue; refuse(); }
        if (!count) break;
        if (static_cast<quint64>(count) > expected - consumed) refuse();
        hash.addData(QByteArrayView(chunk.data(), count));
        if (output >= 0) {
            std::size_t written = 0;
            while (written < static_cast<std::size_t>(count)) {
                const auto n = ::write(output, chunk.data() + written, static_cast<std::size_t>(count) - written);
                if (n < 0) { if (errno == EINTR) continue; refuse(); }
                if (!n) refuse();
                written += static_cast<std::size_t>(n);
            }
        }
        consumed += static_cast<quint64>(count);
    }
    if (consumed != expected || !original.unchanged(input)) refuse();
    if (output >= 0 && reportTime) {
        // The ordinary writer preserves carried report mtimes (ADR-0089 §6).
        // Apply only through this original newly created destination descriptor.
#if defined(__APPLE__)
        const timespec times[2]{{0, UTIME_OMIT}, original.value.st_mtimespec};
#else
        const timespec times[2]{{0, UTIME_OMIT}, original.value.st_mtim};
#endif
        if (::futimens(output, times) != 0) refuse();
    }
    return hash.result().toHex();
}
struct Entry { QString path; quint64 bytes; QByteArray hash; };

// A single export's logical metadata admission, not a global allocator limit.
// Scratch claims unwind before later phases; peak retains their maximum
// simultaneous requirement. This is the caller's existing finite retained role.
struct ExportMetadata {
    quint64 limit,used=0,peak=0,normalizationScratch=0,pathScratch=0;
    explicit ExportMetadata(quint64 remaining):limit(remaining){}
    static quint64 product(quint64 n,quint64 width) {
        if(width && n>std::numeric_limits<quint64>::max()/width)
            throw std::length_error("Export metadata multiplication overflows");
        return n*width;
    }
    void add(quint64 bytes) {
        if(bytes>limit-used)throw std::length_error("Export metadata exceeds its admitted role");
        used+=bytes;peak=std::max(peak,used);
    }
    void rows(quint64 n,quint64 width){add(product(n,width));}
};
struct ExportScratch {
    ExportMetadata* budget;
    quint64 released;
    ExportScratch(ExportMetadata* owner,quint64 bytes):budget(owner),released(bytes) {if(budget)budget->add(bytes);}
    ~ExportScratch(){if(budget)budget->used-=released;}
    void retain(quint64 bytes){if(bytes>released)refuse();released-=bytes;}
    ExportScratch(const ExportScratch&)=delete;
};
char32_t metadata_scalar(QStringView text,qsizetype& at) {
    const auto first=text[at++].unicode();
    if(QChar::isHighSurrogate(first)) {
        if(at==text.size() || !text[at].isLowSurrogate())refuse();
        return QChar::surrogateToUcs4(first,text[at++].unicode());
    }
    if(QChar::isLowSurrogate(first))refuse();
    return first;
}
quint64 path_utf8_bytes(QStringView text) {
    quint64 bytes=0;
    for(qsizetype at=0;at<text.size();) {
        const auto scalar=metadata_scalar(text,at);
        const quint64 width=scalar<0x80?1:scalar<0x800?2:scalar<0x10000?3:4;
        if(width>std::numeric_limits<quint64>::max()-bytes)throw std::length_error("Export path encoding overflows");
        bytes+=width;
    }
    return bytes;
}
void admit_path_work(ExportMetadata& metadata,QStringView path,QStringView suffix={},bool separator=false) {
    // One reusable physical-descent slot: full split/header/text storage plus
    // whole-path and current-component UTF-8. Callers own retained paths apart.
    ExportMetadata work(std::numeric_limits<quint64>::max());
    work.add(sizeof(QStringList)+2*sizeof(QByteArray));
    work.rows(static_cast<quint64>(path.count(u'/'))+static_cast<quint64>(suffix.count(u'/'))+1,sizeof(QString));
    work.rows(static_cast<quint64>(path.size()),sizeof(QChar));
    work.rows(static_cast<quint64>(suffix.size()),sizeof(QChar));
    work.rows(path_utf8_bytes(path),2);work.rows(path_utf8_bytes(suffix),2);
    if(separator)work.add(sizeof(QChar)+sizeof(QString)+2);
    if(work.peak>metadata.pathScratch) {
        metadata.add(work.peak-metadata.pathScratch);
        metadata.pathScratch=work.peak;
    }
}

quint64 canonical_units(char32_t scalar,ExportMetadata& budget) {
    if(QChar::decompositionTag(scalar)!=QChar::Canonical)return QChar::requiresSurrogates(scalar)?2:1;
    // Qt6.11.2 qchar.cpp decompositionHelper stores a direct mapping length in
    // the upper byte of ushort. Preown that public-call result BEFORE lookup;
    // recursion uses the same remaining role, not an invented depth/size cap.
    ExportScratch mapping(&budget,sizeof(QString)+2*sizeof(void*)+
        ExportMetadata::product(std::numeric_limits<quint8>::max(),sizeof(QChar)));
    const auto parts=QChar::decomposition(scalar);
    if(parts.isEmpty())return QChar::requiresSurrogates(scalar)?2:1;
    quint64 result=0;
    for(qsizetype at=0;at<parts.size();) {
        const auto next=canonical_units(metadata_scalar(QStringView(parts),at),budget);
        if(next>std::numeric_limits<quint64>::max()-result)throw std::length_error("Export name decomposition overflows");
        result+=next;
    }
    return result;
}
quint64 name_decomposition(QStringView text,ExportMetadata& budget) {
    quint64 result=0;
    for(qsizetype at=0;at<text.size();) {
        const auto next=canonical_units(metadata_scalar(text,at),budget);
        if(next>std::numeric_limits<quint64>::max()-result)throw std::length_error("Export name decomposition overflows");
        result+=next;
    }
    return result;
}
quint64 admit_alias(QStringView name,ExportMetadata& budget) {
    const auto decomposed=name_decomposition(name,budget);
    // NFC cannot exceed NFD's counted UTF-16 length. Pinned Qt6.11.2's generated
    // MaxSpecialCaseLength is3; ordinary supplementary conversions use2 units.
    budget.add(sizeof(QString));budget.rows(decomposed,3*sizeof(QChar));
    const auto scratch=ExportMetadata::product(decomposed,2*sizeof(QChar));
    budget.normalizationScratch=std::max(budget.normalizationScratch,scratch);
    return scratch;
}

void enumerate(int parent, const QString& prefix, std::set<QString>& files, std::set<QString>& aliases, std::size_t& entries, std::size_t depth = 0, bool carried = false, QStringList* directories = nullptr,
               const std::set<QString>* expectedFiles = nullptr,const QStringList* expectedDirectories = nullptr) {
    if (depth > Limits::json_depth) refuse();
    Fd owned(::openat(parent, ".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC));
    DIR* raw = ::fdopendir(owned.n);
    if (!raw) refuse();
    owned.n = -1;
    std::unique_ptr<DIR, decltype(&::closedir)> stream(raw, ::closedir);
    for (;;) {
        errno = 0;
        auto* entry = ::readdir(raw);
        if (!entry) { if (errno) refuse(); break; }
        const auto nameLength=::strnlen(entry->d_name,Bounds::name_bytes+1);
        if(nameLength>Bounds::name_bytes)refuse();
        const QByteArray rawName(entry->d_name,static_cast<qsizetype>(nameLength));
        if (rawName == "." || rawName == "..") continue;
        if (++entries > Bounds::files) refuse(); // Includes directories and empty directories.
        const auto name = QString::fromUtf8(rawName);
        if (name.toUtf8() != rawName) refuse();
        validate_assistant_result_leaf(name);
        const auto path = prefix.isEmpty() ? name : prefix + '/' + name;
        if (path.toUtf8().size() > static_cast<qsizetype>(Bounds::name_bytes)) refuse();
        struct stat st{};
        if (::fstatat(parent, rawName.constData(), &st, AT_SYMLINK_NOFOLLOW)) refuse();
        if (S_ISDIR(st.st_mode)) {
            if (!carried && (!prefix.isEmpty() || !(name == "structures" || name == "experiments" || name == "analysis" || name == "reports"))) refuse();
            if(expectedDirectories && !expectedDirectories->contains(path))refuse();
        } else if(!S_ISREG(st.st_mode) || (expectedFiles && !expectedFiles->count(path)))refuse();
        if(!aliases.insert(path.normalized(QString::NormalizationForm_C).toCaseFolded()).second)refuse();
        if (S_ISDIR(st.st_mode)) {
            auto child = below(parent, name, true);
            if (directories) directories->append(path);
            enumerate(child.n, path, files, aliases, entries, depth + 1, carried, directories,expectedFiles,expectedDirectories);
        } else if (S_ISREG(st.st_mode)) { relative_name(path.toStdString(), carried); files.insert(path); }
        else refuse();
    }
}
std::set<QString> closure(int fd, bool carried = false, QStringList* directories = nullptr,
                          const std::set<QString>* expectedFiles = nullptr,const QStringList* expectedDirectories = nullptr) {
    std::set<QString> files, aliases;
    std::size_t entries = 0;
    enumerate(fd, {}, files, aliases, entries, 0, carried, directories,expectedFiles,expectedDirectories);
    if (directories) directories->sort();
    if (!files.count("project.edi")) refuse();
    return files;
}
void keys(const edi::json::Object& object, std::initializer_list<const char*> allowed) {
    if (object.size() != allowed.size()) refuse();
    for (const auto* key : allowed) if (std::count_if(object.begin(), object.end(), [key](const auto& member) { return member.first == key; }) != 1) refuse();
}
// Count only the existing closed receipt grammar's allocation roles. This
// prepass does not parse or accept JSON: the original strict parser remains the
// authority after byte/depth/token admission, before the first owning copy.
quint64 receipt_parser_roles(quint64 byteCount,quint64 tokens,quint64 members,quint64 objects,quint64 maximumDepth) {
    quint64 total=0;
    const auto add=[&](quint64 n) {
        if(n>std::numeric_limits<quint64>::max()-total)throw std::length_error("Export receipt metadata overflows");
        total+=n;
    };
    const auto rows=[&](quint64 n,quint64 width) {
        if(width && n>(std::numeric_limits<quint64>::max()-total)/width)throw std::length_error("Export receipt rows overflow");
        total+=n*width;
    };
    // Reader returns local vectors by value. Admit original plus returned AST
    // value/key temporaries. Never subtract member tokens: malformed trailing
    // punctuation must not discount a valid prefix allocated before refusal.
    for (int tree=0;tree!=2;++tree) {
        rows(tokens,sizeof(edi::json::Value));
        rows(members,sizeof(std::string));
    }
    rows(maximumDepth+1,sizeof(edi::json::Value));
    rows(objects,sizeof(std::set<std::string>));
    rows(members,sizeof(std::string)); // unique()'s real copied key set
    // Separate byte owners: input std::string, original and returned AST text,
    // duplicate-key set text, and one number/string reader scratch buffer.
    for(int owner=0;owner!=5;++owner)add(byteCount);
    return total;
}

quint64 receipt_parser_bytes(const QByteArray& bytes) {
    if (bytes.size() < 0 || static_cast<quint64>(bytes.size()) > Limits::context_bytes) refuse();
    quint64 tokens=0,members=0,objects=0,arrays=0,depth=0,maximumDepth=0;
    bool quoted=false,escaped=false,scalar=false;
    for (const char c : bytes) {
        if (quoted) {
            if (escaped) escaped=false;
            else if (c=='\\') escaped=true;
            else if (c=='"') quoted=false;
            continue;
        }
        if (c=='"') {++tokens;quoted=true;scalar=false;}
        else if (c=='{' || c=='[') {
            ++tokens;scalar=false;
            if (c=='{')++objects;else ++arrays;
            if (++depth>Limits::json_depth)refuse();
            maximumDepth=std::max(maximumDepth,depth);
        } else if (c=='}' || c==']') {if(depth)--depth;scalar=false;}
        else if (c==':') {++members;scalar=false;}
        else if (c==',' || c==' ' || c=='\t' || c=='\r' || c=='\n')scalar=false;
        else if (!scalar) {++tokens;scalar=true;}
        // One root object, one files array and at most the admitted file rows;
        // four root members and three members/seven tokens per file row.
        if (objects>1+Bounds::files || arrays>1 || members>4+3*Bounds::files || tokens>9+7*Bounds::files)refuse();
    }
    if (quoted || escaped || depth)refuse();
    return receipt_parser_roles(static_cast<quint64>(bytes.size()),tokens,members,objects,maximumDepth);
}
std::vector<Entry> manifest(const QByteArray& bytes, const QString& intent, bool carried = false,ExportMetadata* metadata = nullptr) {
    (void)receipt_parser_bytes(bytes); // Shape admission before toStdString/parser growth.
    const auto parsed = edi::assistant::detail::parse(bytes.toStdString(), Limits::context_bytes);
    const auto& root = parsed.object("result receipt"); keys(root, {"schema", "intent", "project", "files"});
    if (parsed.at("schema").string("schema") != "edi.assistant.result/1" || parsed.at("intent").string("intent") != intent.toStdString() ||
        parsed.at("project").string("project") != "project") refuse();
    const auto& items = parsed.at("files").array("files");
    if (items.empty() || items.size() > Bounds::files) refuse();
    if(metadata) {
        metadata->add(sizeof(std::vector<Entry>)+sizeof(std::set<QString>));
        metadata->rows(items.size(),sizeof(Entry));
    }
    std::vector<Entry> result;result.reserve(items.size());std::set<QString> names;quint64 total=0;
    for (const auto& item : items) {
        keys(item.object("file"), {"path", "bytes", "sha256"});
        const auto& raw=item.at("path").string("path");
        if(raw.size()>Bounds::name_bytes)refuse();
        const auto parts=1+static_cast<quint64>(std::count(raw.begin(),raw.end(),'/'));
        if(parts>Limits::json_depth)refuse();
        const auto rawBytes=static_cast<quint64>(raw.size());
        // relative_name: retained decoded name, round-trip pair, split fields,
        // and the one current component's encoded/decoded validation scratch.
        const auto nameWork=sizeof(QString)+2*sizeof(QByteArray)+sizeof(QStringList)+
            ExportMetadata::product(parts,sizeof(QString))+sizeof(QByteArray)+sizeof(QString)+
            ExportMetadata::product(rawBytes,sizeof(QChar)+2+sizeof(QChar)+1+sizeof(QChar));
        ExportScratch relative(metadata,nameWork);
        const auto name=relative_name(raw,carried);
        relative.retain(ExportMetadata::product(rawBytes,sizeof(QChar)));
        const auto normalizeBytes=metadata?admit_alias(QStringView(name),*metadata):0;
        {ExportScratch normalize(metadata,normalizeBytes);
            if(!names.insert(name.normalized(QString::NormalizationForm_C).toCaseFolded()).second)refuse();}
        const auto size = item.at("bytes").number("bytes");
        if (!std::isfinite(size) || size < 0 || std::floor(size) != size || size > Bounds::file_bytes || size > Bounds::collection_bytes - total) refuse();
        const auto& hash = item.at("sha256").string("sha256");
        if (hash.size() != 64 || !std::all_of(hash.begin(), hash.end(), [](char c) { return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'); })) refuse();
        total += static_cast<quint64>(size);
        if(metadata)metadata->add(64);
        result.push_back({name, static_cast<quint64>(size), QByteArray::fromStdString(hash)});
    }
    return result;
}
// Logical JSON/header and generated protected-receipt roles. This counts the
// existing schema; own_receipt remains the only formatter. The common core
// escaped-size walker borrows UTF-8 and may overestimate Qt's HTML spelling.
void admit_export_json(ExportMetadata& metadata,const std::vector<Entry>& entries,
                       const ImmutableAssistantResult& source) {
    quint64 encoded=sizeof("{\"schema\":\"edi.assistant.result/1\",\"intent\":\"")-1;
    const auto add=[&](quint64 amount) {
        if(amount>std::numeric_limits<quint64>::max()-encoded)
            throw std::length_error("Export receipt encoding overflows");
        encoded+=amount;
    };
    add(36); // QUuid::WithoutBraces, the existing protected receipt intent.
    add(sizeof("\",\"project\":\"project\",\"files\":[")-1);
    // Two retained file arrays (export state and protected readback) and one
    // simultaneous root/document construction role. QString storage below is
    // payload accounting, distinct from the QJson value/member headers.
    for(int role=0;role!=3;++role) {
        metadata.add(sizeof(QJsonArray));
        metadata.rows(entries.size(),sizeof(QJsonObject)+4*sizeof(QJsonValue)+3*sizeof(QString));
        metadata.rows(entries.size(),(4+5+6+64)*sizeof(QChar));
        for(const auto& entry:entries)metadata.rows(static_cast<quint64>(entry.path.size()),sizeof(QChar));
    }
    metadata.add(sizeof(QJsonDocument)+sizeof(QJsonObject)+4*sizeof(QJsonValue)+4*sizeof(QString));
    metadata.rows(6+6+7+5+21+36+7,sizeof(QChar)); // Root keys and string values.
    for(std::size_t i=0;i<entries.size();++i) {
        const auto& entry=entries[i];
        // Every admitted path already round-tripped inside the existing byte
        // bound. Preown the one UTF-8 conversion before using the common size
        // counter, then release it before the next row.
        ExportScratch utf8(&metadata,sizeof(QByteArray)+Bounds::name_bytes+
            sizeof(std::array<char,std::numeric_limits<quint64>::digits10+1>));
        const auto path=entry.path.toUtf8();
        if(path.size()>static_cast<qsizetype>(Bounds::name_bytes))refuse();
        if(i)add(1);
        add(sizeof("{\"path\":")-1);
        add(edi::json::encoded_string_size(std::string_view(path.constData(),static_cast<std::size_t>(path.size()))));
        add(sizeof(",\"bytes\":")-1);
        std::array<char,std::numeric_limits<quint64>::digits10+1> decimal{};
        const auto converted=std::to_chars(decimal.data(),decimal.data()+decimal.size(),entry.bytes);
        if(converted.ec!=std::errc{})throw std::length_error("Export byte count encoding overflows");
        add(static_cast<quint64>(converted.ptr-decimal.data()));
        add(sizeof(",\"sha256\":\"")-1);add(64);add(sizeof("\"}")-1);
    }
    add(sizeof("]}")-1);
    if(encoded>Limits::context_bytes)refuse(); // Existing own_receipt final cap.
    metadata.add(sizeof(QByteArray)+encoded);
    const auto rows=static_cast<quint64>(entries.size());
    const auto readbackParser=receipt_parser_roles(encoded,9+7*rows,4+3*rows,1+rows,3);
    const auto originalParser=receipt_parser_bytes(source.receipt);
    // The caller separately owns the original receipt-parser role. Only a
    // larger generated receipt needs additional simultaneous parser space.
    if(readbackParser>originalParser)metadata.add(readbackParser-originalParser);
}

Fd staged_file(int root, const QString& path) {
    const auto parts = path.split('/');
    Fd directoryFd(::dup(root));
    for (qsizetype i = 0; i + 1 < parts.size(); ++i) {
        const auto name = parts[i].toUtf8();
        if (::mkdirat(directoryFd.n, name.constData(), 0700) && errno != EEXIST) refuse();
        directoryFd = below(directoryFd.n, parts[i], true);
    }
    return Fd(::openat(directoryFd.n, parts.back().toUtf8().constData(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600));
}
void stage_directories(int root, const QStringList& directories) {
    for (const auto& path : directories) {
        Fd parent(::dup(root));
        for (const auto& part : path.split('/')) {
            validate_assistant_result_leaf(part);
            const auto name = part.toUtf8();
            if (::mkdirat(parent.n, name.constData(), 0700) && errno != EEXIST) refuse();
            parent = below(parent.n, part, true);
        }
    }
}
void write_staged(int root, const QString& path, std::string_view bytes) {
    auto file = staged_file(root, path);
    std::size_t written = 0;
    while (written < bytes.size()) {
        const auto count = ::write(file.n, bytes.data() + written, bytes.size() - written);
        if (count < 0) { if (errno == EINTR) continue; refuse(); }
        if (!count) refuse();
        written += static_cast<std::size_t>(count);
    }
}
QJsonArray receipt_files(const std::vector<Entry>& entries) {
    QJsonArray result;
    for (const auto& entry : entries) result.append(QJsonObject{{"path", entry.path}, {"bytes", static_cast<qint64>(entry.bytes)}, {"sha256", QString::fromLatin1(entry.hash)}});
    return result;
}
void verify(int fd, const std::vector<Entry>& entries, int copy = -1,
            bool carried = false, const QStringList* expectedDirectories = nullptr) {
    std::set<QString> expected;
    for(const auto& entry:entries)expected.insert(entry.path);
    QStringList beforeDirectories;
    const auto before = closure(fd, carried, expectedDirectories ? &beforeDirectories : nullptr,&expected,expectedDirectories);
    if (expectedDirectories && beforeDirectories != *expectedDirectories) refuse();
    if (copy >= 0 && expectedDirectories) stage_directories(copy, *expectedDirectories);
    for (const auto& entry : entries) {
        auto source = below(fd, entry.path);
        Fd output;
        if (copy >= 0) output = staged_file(copy, entry.path);
        if (stream_file(source.n, entry.bytes, Bounds::file_bytes, output.n, entry.path.startsWith("reports/")) != entry.hash) refuse();
    }
    QStringList afterDirectories;
    if (before != expected || closure(fd, carried, expectedDirectories ? &afterDirectories : nullptr,&expected,expectedDirectories) != expected ||
        (expectedDirectories && afterDirectories != *expectedDirectories)) refuse();
}
edi::Project load_owned_project(int fd, const QString& ownedPath, const std::vector<Entry>& entries, bool carried = false, const QStringList* directories = nullptr) {
    const Identity pinned(fd);
    verify(fd, entries, -1, carried, directories);
    QString access;
#if defined(__linux__)
    access = QStringLiteral("/proc/self/fd/%1").arg(fd);
#elif defined(__APPLE__)
    // Darwin fdescfs duplicates a descriptor; it does not implement child
    // lookup. Use the actual private host-owned copy's physical directory.
    // This directory is outside the admitted runtime write root, not its source.
    access = ownedPath;
    if (access.isEmpty()) refuse();
#else
    Q_UNUSED(ownedPath); refuse();
#endif
    // Bond the named copy to the pinned descriptor both before and after the
    // real loader. Directory ancestors may have trusted system aliases; every
    // untrusted copied descendant was no-follow admitted and hash verified.
    auto named = physical_directory(ownedPath);
    if (!pinned.object(named.n)) refuse();
    auto project = edi::detail::load_assistant_project(access.toStdString());
    auto again = physical_directory(ownedPath);
    if (!pinned.object(again.n)) refuse();
    verify(fd, entries, -1, carried, directories);
    return project;
}

#endif
} // namespace
struct AssistantResultDirectory {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    Fd descriptor;
    explicit AssistantResultDirectory(Fd fd) : descriptor(std::move(fd)) {}
#endif
};

namespace {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
std::shared_ptr<ImmutableAssistantResult> owned_result_snapshot_in(const QString& physicalParent) {
    auto parent=physical_directory(physicalParent);
    const Identity parentIdentity(parent.n);
    auto result=std::make_shared<ImmutableAssistantResult>();
    result->lease=std::make_shared<QTemporaryDir>(QDir(physicalParent).filePath("result-XXXXXX"));
    if(!result->lease->isValid())refuse();
    result->lease->setAutoRemove(false);
    const auto path=result->lease->path();
    // The explicit absolute template has one terminal six-character mask.
    // No canonical path or mutable external root is obtained from this result.
    const auto prefixLength=physicalParent.size()+(physicalParent.endsWith('/')?0:1);
    if(!path.startsWith(physicalParent) || path.size()!=prefixLength+static_cast<qsizetype>(sizeof("result-XXXXXX")-1) ||
       (!physicalParent.endsWith('/') && path[physicalParent.size()]!='/'))refuse();
    auto again=physical_directory(physicalParent);
    if(!parentIdentity.object(again.n))refuse();
    const auto leaf=path.mid(prefixLength);
    auto handle=below(parent.n,leaf,true);
    auto named=physical_directory(path);
    if(!Identity(handle.n).object(named.n))refuse();
    result->handle=std::make_shared<AssistantResultDirectory>(std::move(handle));
    result->directory=path;result->recovery_directory=path;
    return result;
}
std::shared_ptr<ImmutableAssistantResult> owned_result_snapshot() {
    const auto cache=QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)+"/assistant/results";
    if(!QDir().mkpath(cache))refuse();
    const auto physical=QFileInfo(cache).canonicalFilePath();
    const auto agent=QFileInfo(QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)+"/assistant/agent").canonicalFilePath();
    if(physical.isEmpty() || (!agent.isEmpty() && (physical==agent || physical.startsWith(agent+'/'))))refuse();
    return owned_result_snapshot_in(physical);
}
std::shared_ptr<ImmutableAssistantResult> owned_result_snapshot(const ImmutableAssistantResult& admitted) {
    if(!admitted.handle || !admitted.lease || !admitted.lease->isValid())refuse();
    auto original=physical_directory(admitted.directory);
    if(!Identity(admitted.handle->descriptor.n).object(original.n))refuse();
    const auto slash=admitted.directory.lastIndexOf('/');
    if(slash<0)refuse();
    // This is the existing host-owned lease's exact parent, never a provider
    // path or an arbitrary filesystem seed. The first factory owns its policy.
    return owned_result_snapshot_in(admitted.directory.left(slash?slash:1));
}
void own_receipt(ImmutableAssistantResult& result, const std::vector<Entry>& entries) {
    result.intent = QUuid::createUuid().toString(QUuid::WithoutBraces);
    result.files = receipt_files(entries);
    result.receipt = QJsonDocument(QJsonObject{{"schema", "edi.assistant.result/1"}, {"intent", result.intent},
        {"project", "project"}, {"files", result.files}}).toJson(QJsonDocument::Compact);
    if (result.receipt.size() > static_cast<qsizetype>(Limits::context_bytes)) refuse();
}
#endif
} // namespace

void check_assistant_result_mode(const edi::Project& project) {
    if (project.sequential_fit.declared() || edi::is_scan_fitting_mode(project.fitting_mode) || !project.report_files.empty())
        throw std::runtime_error("This result requires external scan/report files; automatic opening currently supports self-contained native projects only");
}
std::shared_ptr<ImmutableAssistantResult> capture_assistant_result(const QString& workspace, const QString& intent) {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    validate_assistant_result_leaf(intent);
    auto root = directory(workspace);
    const auto receiptName = ".edi-result/" + intent + "/result.json";
    auto receipt = below(root.n, receiptName);
    const Identity receiptIdentity(receipt.n);
    const auto original = read_file(receipt.n, Limits::context_bytes);
    const auto entries = manifest(original, intent);
    auto project = below(root.n, ".edi-result/" + intent + "/project", true);
    const Identity projectIdentity(project.n);
    auto result = owned_result_snapshot();
    const auto physicalWorkspace = QFileInfo(workspace).canonicalFilePath();
    if (physicalWorkspace.isEmpty() || result->directory == physicalWorkspace || result->directory.startsWith(physicalWorkspace + '/')) refuse();
    auto copy = result->handle;
    verify(project.n, entries, copy->descriptor.n);
    // Reopen source paths as well: a rename/replacement cannot substitute a different receipt/tree.
    auto receiptAgain = below(root.n, receiptName);
    auto projectAgain = below(root.n, ".edi-result/" + intent + "/project", true);
    if (!receiptIdentity.unchanged(receipt.n) || !receiptIdentity.unchanged(receiptAgain.n) || !projectIdentity.object(projectAgain.n)) refuse();
    verify(copy->descriptor.n, entries);
    verify(project.n, entries); // Later companions cannot conceal a changed earlier source file.
    if (!receiptIdentity.unchanged(receipt.n)) refuse();
    auto loaded = load_owned_project(copy->descriptor.n, result->directory, entries);
    check_assistant_result_mode(loaded);
    result->files = receipt_files(entries); result->receipt = original; result->intent = intent;
    return result;
#else
    Q_UNUSED(workspace); Q_UNUSED(intent); refuse();
#endif
}

edi::Project load_captured_assistant_result(const ImmutableAssistantResult& result) {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    if (!result.handle || !result.lease || !result.lease->isValid()) refuse();
    const auto entries = manifest(result.receipt, result.intent, result.carried_tree);
    auto loaded = load_owned_project(result.handle->descriptor.n, result.directory, entries, result.carried_tree, result.carried_tree ? &result.directories : nullptr);
    check_assistant_result_mode(loaded);
    return loaded;
#else
    Q_UNUSED(result); refuse();
#endif
}

std::shared_ptr<ImmutableAssistantResult> capture_prepared_native_documents(
    const std::vector<std::pair<std::string, std::string>>& documents) {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    if (documents.empty() || documents.size() > Bounds::files) refuse();
    std::vector<Entry> entries;
    entries.reserve(documents.size());
    std::set<QString> aliases, directories;
    quint64 bytes = 0;
    bool project = false;
    // Every input cardinality/path/byte role is checked before any output
    // directory, owning text copy or staged file. The upstream writer MUST
    // independently bound preparation; this function does not bless a scratch save.
    for (const auto& [name, text] : documents) {
        if (text.size() > Bounds::file_bytes || text.size() > Bounds::collection_bytes - bytes) refuse();
        bytes += text.size();
        const auto path = relative_name(name);
        if (!aliases.insert(path.normalized(QString::NormalizationForm_C).toCaseFolded()).second) refuse();
        const auto slash = path.indexOf('/');
        if (slash >= 0) directories.insert(path.left(slash));
        if (documents.size() + directories.size() > Bounds::files) refuse();
        project |= path == "project.edi";
        const auto view = QByteArray::fromRawData(text.data(), static_cast<qsizetype>(text.size()));
        entries.push_back({path, static_cast<quint64>(text.size()), QCryptographicHash::hash(view, QCryptographicHash::Sha256).toHex()});
    }
    if (!project) refuse();
    auto result = owned_result_snapshot();
    own_receipt(*result, entries);
    for (std::size_t i = 0; i < entries.size(); ++i) write_staged(result->handle->descriptor.n, entries[i].path, documents[i].second);
    verify(result->handle->descriptor.n, entries);
    auto loaded = load_owned_project(result->handle->descriptor.n, result->directory, entries);
    check_assistant_result_mode(loaded);
    return result;
#else
    Q_UNUSED(documents); refuse();
#endif
}

namespace {
bool separated_from_host_storage(const QString& physical) {
    const auto base = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
    if (base.isEmpty()) return false;
    const auto within = [](const QString& child, const QString& parent) {
        return child.compare(parent, Qt::CaseInsensitive) == 0 || child.startsWith(parent + '/', Qt::CaseInsensitive);
    };
    // Include actual existing child aliases, not only the app-data spelling.
    // No enumeration or provider-supplied protected-root list is involved.
    for (const auto* suffix : {"", "/assistant", "/assistant/agent", "/assistant/input-cache", "/assistant/results", "/assistant/report-views"}) {
        const QFileInfo entry(base + QString::fromLatin1(suffix));
        const auto protectedPath = entry.canonicalFilePath();
        if (protectedPath.isEmpty()) {
            if (!*suffix || entry.exists() || entry.isSymLink()) return false;
            continue;
        }
        if (within(physical, protectedPath) || within(protectedPath, physical)) return false;
    }
    return true;
}
}

bool assistant_input_path_allowed(const QString& physical) noexcept {
    try {
        if(physical.isEmpty() || !separated_from_host_storage(physical))return false;
        const auto home=QDir::homePath();
        const QStringList privateRoots{home+"/.codex",qEnvironmentVariable("CODEX_HOME"),home+"/.ssh",home+"/.aws"};
        for(const auto& name:privateRoots) {
            if(name.isEmpty())continue;
            const auto actual=QFileInfo(name).canonicalFilePath();
            const auto root=actual.isEmpty()?QDir::cleanPath(name):actual;
#if defined(Q_OS_WIN)
            constexpr auto sensitivity=Qt::CaseInsensitive;
#else
            constexpr auto sensitivity=Qt::CaseSensitive;
#endif
            if(physical.compare(root,sensitivity)==0 || physical.startsWith(root+'/',sensitivity) || root.startsWith(physical+'/',sensitivity))return false;
        }
        return true;
    } catch(...) {return false;}
}

bool assistant_input_matches(int descriptor,const QString& physical,const QString& selected) noexcept {
    try {
        if(descriptor<0 || !assistant_input_path_allowed(physical))return false;
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
        const Identity pinned(descriptor);
        const bool dir=S_ISDIR(pinned.value.st_mode);
        if(!dir && (!S_ISREG(pinned.value.st_mode) || pinned.value.st_nlink!=1))return false;
        // Reuse the original bounded writer's physical, component-wise no-follow
        // descent. A mutable canonical parent cannot redirect this open to A
        // while the classifier was checking B's spelling.
        // An input's physical leaf keeps the existing read domain, including
        // lawful Unix trailing dots/spaces; result-tree naming is stricter.
        auto classified=dir?physical_directory(physical):Fd(::openat(
            physical_directory(QFileInfo(physical).absolutePath()).n,QFileInfo(physical).fileName().toUtf8().constData(),
            O_RDONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC));
        if(!pinned.unchanged(classified.n) || QFileInfo(selected).canonicalFilePath()!=physical)return false;
        Fd named(::open(selected.toUtf8().constData(),O_RDONLY|O_NONBLOCK|O_CLOEXEC));
        return pinned.unchanged(named.n) && pinned.unchanged(descriptor) && assistant_input_path_allowed(physical);
#elif defined(Q_OS_WIN)
        const auto handle=reinterpret_cast<HANDLE>(_get_osfhandle(descriptor));
        if(handle==INVALID_HANDLE_VALUE)return false;
        BY_HANDLE_FILE_INFORMATION pinned{};
        if(!GetFileInformationByHandle(handle,&pinned) || GetFileType(handle)!=FILE_TYPE_DISK ||
            (pinned.dwFileAttributes&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT)) || pinned.nNumberOfLinks!=1)return false;
        // Windows supplies the normalized name of this actual opened handle,
        // rather than resolving the mutable caller spelling as the classifier.
        // The platform's extended native pathname domain is 32767 UTF-16 units.
        std::array<wchar_t,32768> buffer{};
        const auto count=GetFinalPathNameByHandleW(handle,buffer.data(),static_cast<DWORD>(buffer.size()),FILE_NAME_NORMALIZED|VOLUME_NAME_DOS);
        if(!count || count>=buffer.size())return false;
        auto actual=QDir::fromNativeSeparators(QString::fromWCharArray(buffer.data(),count));
        if(actual.startsWith("//?/UNC/"))actual="//"+actual.mid(8);
        else if(actual.startsWith("//?/"))actual=actual.mid(4);
        if(actual.compare(physical,Qt::CaseInsensitive)!=0 || !assistant_input_path_allowed(actual))return false;
        const auto spelling=QDir::toNativeSeparators(selected).toStdWString();
        const auto named=CreateFileW(spelling.c_str(),GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,
            nullptr,OPEN_EXISTING,FILE_FLAG_OPEN_REPARSE_POINT,nullptr);
        if(named==INVALID_HANDLE_VALUE)return false;
        const auto close=qScopeGuard([named]{CloseHandle(named);});
        BY_HANDLE_FILE_INFORMATION info{};
        return GetFileInformationByHandle(named,&info) && !(info.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT) &&
            pinned.dwVolumeSerialNumber==info.dwVolumeSerialNumber && pinned.nFileIndexHigh==info.nFileIndexHigh &&
            pinned.nFileIndexLow==info.nFileIndexLow && pinned.nFileSizeHigh==info.nFileSizeHigh && pinned.nFileSizeLow==info.nFileSizeLow &&
            pinned.ftLastWriteTime.dwHighDateTime==info.ftLastWriteTime.dwHighDateTime && pinned.ftLastWriteTime.dwLowDateTime==info.ftLastWriteTime.dwLowDateTime;
#else
        Q_UNUSED(selected);return false;
#endif
    }catch(...){return false;}
}

struct AssistantSaveSource::State {
    QString path;
    std::string record;
    std::shared_ptr<ImmutableAssistantResult> snapshot;
    quint64 retained = 0;
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    Fd source;
    Identity identity;
    std::vector<Entry> entries;
    std::vector<Identity> fileIdentities;
    State(QString location, Fd pinned)
        : path(std::move(location)), source(std::move(pinned)), identity(source.n) {}
#endif
};
AssistantSaveSource::AssistantSaveSource(const QString& ownedDirectory, quint64 retainedLimit, const std::function<bool()>& current) {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    if (ownedDirectory.isEmpty() || ownedDirectory.size() > static_cast<qsizetype>(Limits::id_bytes) ||
        ownedDirectory.contains(QChar(0)) || ownedDirectory.toUtf8().size() > static_cast<qsizetype>(Limits::id_bytes) ||
        !QDir::isAbsolutePath(ownedDirectory) || !current()) refuse();
    auto pinned = directory(ownedDirectory);
    const auto physical = QFileInfo(ownedDirectory).canonicalFilePath();
    if (physical.isEmpty() || physical == "/" || physical.toUtf8().size() > static_cast<qsizetype>(Limits::id_bytes) ||
        !separated_from_host_storage(physical)) refuse();
    // Enumeration and later currentness/receipt walks use the same closed file/path
    // limits. Preown their maximum simultaneous metadata roles before the first walk.
    static_assert(Bounds::files <= std::numeric_limits<quint64>::max() /
        (sizeof(Entry) + sizeof(Identity) + 32 * Bounds::name_bytes + 512));
    constexpr quint64 metadata = Bounds::files *
        (sizeof(Entry) + sizeof(Identity) + 32 * Bounds::name_bytes + 512);
    constexpr quint64 fixed = sizeof(State) + sizeof(ImmutableAssistantResult) + Bounds::read_bytes + 8 * Limits::id_bytes;
    static_assert(metadata <= std::numeric_limits<quint64>::max() - fixed);
    quint64 roles = fixed + metadata;
    if (roles > retainedLimit) throw std::length_error("Saved source has no admitted metadata workspace");
    auto state = std::make_unique<State>(physical, std::move(pinned));
    QStringList directories;
    const auto names = closure(state->source.n, true, &directories);
    quint64 recordBytes = 0;
    const auto admit = [&](quint64 extra) {
        if (roles > retainedLimit || extra > retainedLimit - roles) throw std::length_error("Saved source exceeds its original retained slot");
        roles += extra;
    };
    for (const auto& name : names) {
        // Per-file metadata is already owned by the finite workspace above.
        auto input = below(state->source.n, name);
        const Identity identity(input.n);
        if (!S_ISREG(identity.value.st_mode) || identity.value.st_nlink != 1 || identity.value.st_size < 0 ||
            static_cast<quint64>(identity.value.st_size) > Bounds::file_bytes) refuse();
        if (name == "project.edi") { recordBytes = static_cast<quint64>(identity.value.st_size); admit(recordBytes); }
    }
    if (roles > retainedLimit) throw std::length_error("Saved source exceeds its original retained slot");
    state->retained = roles;
    state->entries.reserve(names.size()); state->fileIdentities.reserve(names.size());
    state->snapshot = owned_result_snapshot();
    state->snapshot->carried_tree = true; state->snapshot->directories = std::move(directories);
    stage_directories(state->snapshot->handle->descriptor.n, state->snapshot->directories);
    quint64 total = 0;
    for (const auto& name : names) {
        auto input = below(state->source.n, name);
        const Identity identity(input.n);
        if (identity.value.st_size < 0 || static_cast<quint64>(identity.value.st_size) > Bounds::collection_bytes - total) refuse();
        const auto bytes = static_cast<quint64>(identity.value.st_size); total += bytes;
        auto output = staged_file(state->snapshot->handle->descriptor.n, name);
        const auto hash = stream_file(input.n, bytes, Bounds::file_bytes, output.n, name.startsWith("reports/"));
        state->entries.push_back({name, bytes, hash}); state->fileIdentities.push_back(identity);
    }
    own_receipt(*state->snapshot, state->entries);
    verify(state->source.n, state->entries, -1, true, &state->snapshot->directories);
    verify(state->snapshot->handle->descriptor.n, state->entries, -1, true, &state->snapshot->directories);
    auto record = below(state->snapshot->handle->descriptor.n, QStringLiteral("project.edi"));
    const Identity recordIdentity(record.n);
    if (recordIdentity.value.st_size < 0 || static_cast<quint64>(recordIdentity.value.st_size) != recordBytes) refuse();
    state->record.resize(static_cast<std::size_t>(recordIdentity.value.st_size));
    std::size_t read = 0;
    while (read < state->record.size()) {
        const auto n = ::read(record.n, state->record.data() + read, state->record.size() - read);
        if (n < 0) { if (errno == EINTR) continue; refuse(); }
        if (!n) refuse();
        read += static_cast<std::size_t>(n);
    }
    char extra{}; if (::read(record.n, &extra, 1) != 0 || !recordIdentity.unchanged(record.n)) refuse();
    if (!current()) refuse();
    auto named = directory(physical);
    if (!state->identity.unchanged(state->source.n) || !state->identity.unchanged(named.n)) refuse();
    for (std::size_t i = 0; i < state->entries.size(); ++i) {
        auto input = below(state->source.n, state->entries[i].path);
        if (!state->fileIdentities[i].unchanged(input.n)) refuse();
    }
    state_ = std::move(state);
#else
    Q_UNUSED(ownedDirectory); Q_UNUSED(retainedLimit); Q_UNUSED(current); refuse();
#endif
}
AssistantSaveSource::~AssistantSaveSource() = default;
const QString& AssistantSaveSource::path() const noexcept { return state_->path; }
const std::string& AssistantSaveSource::record() const noexcept { return state_->record; }
const ImmutableAssistantResult& AssistantSaveSource::snapshot() const noexcept { return *state_->snapshot; }
quint64 AssistantSaveSource::retainedBytes() const noexcept { return state_->retained; }
bool AssistantSaveSource::current() const noexcept {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    try {
        if (!separated_from_host_storage(state_->path)) return false;
        auto named = directory(state_->path);
        QStringList directories;
        const auto names = closure(state_->source.n, true, &directories);
        if (!state_->identity.unchanged(state_->source.n) || !state_->identity.unchanged(named.n) ||
            names.size() != state_->entries.size() || directories != state_->snapshot->directories) return false;
        for (std::size_t i = 0; i < state_->entries.size(); ++i) {
            auto input = below(state_->source.n, state_->entries[i].path);
            if (!state_->fileIdentities[i].unchanged(input.n)) return false;
        }
        return true;
    } catch (...) { return false; }
#else
    return false;
#endif
}

std::shared_ptr<ImmutableAssistantResult> capture_prepared_native_documents(
    const std::vector<std::pair<std::string, std::string>>& documents, const AssistantSaveSource& source) {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    const auto& seed = source.snapshot();
    if (!seed.carried_tree || !seed.handle) refuse();
    const auto original = manifest(seed.receipt, seed.intent, true);
    verify(seed.handle->descriptor.n, original, -1, true, &seed.directories);
    auto result = capture_prepared_native_documents(documents);
    auto entries = manifest(result->receipt, result->intent);
    std::set<QString> files, directories, aliases;
    quint64 total = 0;
    const auto admit = [&](const Entry& entry) {
        if (entry.bytes > Bounds::file_bytes || entry.bytes > Bounds::collection_bytes - total) refuse();
        total += entry.bytes;
        if (!aliases.insert(entry.path.normalized(QString::NormalizationForm_C).toCaseFolded()).second) refuse();
        files.insert(entry.path);
        auto parent = QFileInfo(entry.path).path();
        while (parent != ".") { directories.insert(parent); parent = QFileInfo(parent).path(); }
        if (files.size() + directories.size() > Bounds::files) refuse();
    };
    for (const auto& entry : entries) admit(entry);
    std::vector<Entry> carried;
    for (const auto& entry : original) {
        const auto parts = entry.path.split('/');
        const bool entity = parts.size() == 2 && (parts[0] == "structures" || parts[0] == "experiments") && parts[1].endsWith(".edi", Qt::CaseInsensitive);
        if (entry.path == "project.edi" || entity || entry.path == "analysis/analysis.edi" || files.count(entry.path)) continue;
        admit(entry); carried.push_back(entry);
    }
    for (const auto& directory : seed.directories) {
        if (!aliases.insert(directory.normalized(QString::NormalizationForm_C).toCaseFolded()).second) refuse();
        directories.insert(directory);
        if (files.size() + directories.size() > Bounds::files) refuse();
    }
    std::set<QString> finalAliases;
    for (const auto& file : files) if (!finalAliases.insert(file.normalized(QString::NormalizationForm_C).toCaseFolded()).second) refuse();
    for (const auto& directory : directories) if (!finalAliases.insert(directory.normalized(QString::NormalizationForm_C).toCaseFolded()).second) refuse();
    QStringList finalDirectories;
    for (const auto& directory : directories) finalDirectories.append(directory);
    finalDirectories.sort();
    stage_directories(result->handle->descriptor.n, finalDirectories);
    for (const auto& entry : carried) {
        auto input = below(seed.handle->descriptor.n, entry.path); auto output = staged_file(result->handle->descriptor.n, entry.path);
        if (stream_file(input.n, entry.bytes, Bounds::file_bytes, output.n, entry.path.startsWith("reports/")) != entry.hash) refuse();
        entries.push_back(entry);
    }
    result->carried_tree = true; result->directories = std::move(finalDirectories);
    own_receipt(*result, entries);
    verify(result->handle->descriptor.n, entries, -1, true, &result->directories);
    (void)load_captured_assistant_result(*result);
    return result;
#else
    Q_UNUSED(documents); Q_UNUSED(source); refuse();
#endif
}

struct AssistantWorkingFolder::State {
    QString path, selected;

#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    Fd descriptor;
    Identity identity;
    explicit State(QString physical)
        : path(std::move(physical)), descriptor(directory(path)), identity(descriptor.n) {
        if (!S_ISDIR(identity.value.st_mode) || ::faccessat(descriptor.n, ".", R_OK | W_OK | X_OK, 0))
            throw std::runtime_error("The chosen Save As parent is not readable and writable");
    }
#endif
};
quint64 AssistantWorkingFolder::preparationBytes(const QString& selected) {
    if(selected.isEmpty() || selected.size()>static_cast<qsizetype>(Limits::id_bytes))refuse();
    // Selected QString plus its UTF-8 validation, two simultaneous canonical
    // spellings and directory encoder scratch coexist in the existing picker
    // constructor. PATH_MAX bounds the platform canonicalization intermediate;
    // the accepted retained physical spelling still obeys id_bytes.
#if defined(Q_OS_UNIX) && defined(PATH_MAX) && !defined(__EMSCRIPTEN__)
    return sizeof(AssistantWorkingFolder)+sizeof(State)+
        static_cast<quint64>(selected.size())*sizeof(QChar)+Limits::id_bytes+
        2*static_cast<quint64>(PATH_MAX)*sizeof(QChar)+Limits::id_bytes;
#else
    refuse();
#endif
}
quint64 AssistantWorkingFolder::retainedBytes() const noexcept {
    return sizeof(AssistantWorkingFolder)+sizeof(State)+
        static_cast<quint64>(state_->path.capacity()+state_->selected.capacity())*sizeof(QChar);
}
AssistantWorkingFolder::AssistantWorkingFolder(const QString& selected) {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    // Admit path bytes before canonicalization and retain the physical spelling.
    // A selected alias is permitted, but does not turn later aliases into grants.
    if (selected.isEmpty() || selected.size() > static_cast<qsizetype>(Limits::id_bytes) ||
        selected.contains(QChar(0)) || selected.toUtf8().size() > static_cast<qsizetype>(Limits::id_bytes) ||
        !QDir::isAbsolutePath(selected))
        throw std::runtime_error("Choose an existing local Save As parent");
    const auto physical = QFileInfo(selected).canonicalFilePath();
    if (physical.isEmpty() || physical == "/" || physical.toUtf8().size() > static_cast<qsizetype>(Limits::id_bytes))
        throw std::runtime_error("Choose a bounded project Save As parent");
    if (!separated_from_host_storage(physical))
        throw std::runtime_error("Choose a Save As parent outside Edi's protected storage");
    auto prepared = std::make_unique<State>(physical);
    prepared->selected=selected;
    // The actual selected alias must still name that pinned object after all
    // fallible admission. Future runtime requests use only the physical path.
    const auto selectedNow = QFileInfo(selected).canonicalFilePath();
    auto namedNow = directory(physical);
    if (selectedNow != physical || !prepared->identity.object(namedNow.n) || !separated_from_host_storage(physical))
        throw std::runtime_error("The chosen Save As parent changed");
    state_ = std::move(prepared);
#else
    Q_UNUSED(selected);
    throw std::runtime_error("Native Save As is unavailable on this platform");
#endif
}
AssistantWorkingFolder::~AssistantWorkingFolder() = default;
const QString& AssistantWorkingFolder::path() const noexcept { return state_->path; }
bool AssistantWorkingFolder::current() const noexcept {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    try {
        auto named = directory(state_->path);
        return QFileInfo(state_->selected).canonicalFilePath()==state_->path &&
            state_->identity.object(state_->descriptor.n) && state_->identity.object(named.n) &&
            separated_from_host_storage(state_->path) && !::faccessat(state_->descriptor.n, ".", R_OK | W_OK | X_OK, 0);
    } catch (...) { return false; }
#else
    return false;
#endif
}

struct AssistantResultExport::State {
    QString parent, stage, leaf, destination, recovery;
    quint64 preparationBytes = 0;
    QJsonArray files;
    QStringList directories;
    bool committed = false, carried = false, physicalParent = false;
    std::shared_ptr<const AssistantSaveSource> owned;
    std::shared_ptr<const AssistantWorkingFolder> grant;
    std::shared_ptr<ImmutableAssistantResult> reopenCopy;
    bool reopenCopied = false;
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    std::vector<Entry> entries;
#endif
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    Fd parentFd, stageFd, grantReplacement;
    Identity parentIdentity, stageIdentity;
    std::optional<Identity> replacementIdentity;
    static Fd selectedParent(const QString& path,bool alreadyPhysical=false) {
        return alreadyPhysical?physical_directory(path):directory(path);
    }
    State(const QString& parentPath, const QString& leafName, Fd pinnedParent, const Identity* replacing = nullptr)
        : parent(parentPath), stage(".edi-export-" + QUuid::createUuid().toString(QUuid::WithoutBraces)), leaf(leafName),
          destination(QDir(parentPath).filePath(leafName)), parentFd(std::move(pinnedParent)), parentIdentity(parentFd.n),
          stageIdentity(parentFd.n) {
        validate_assistant_result_leaf(leaf);
        if (leaf.toCaseFolded() == stage.toCaseFolded()) refuse();
        // Refuse an already occupied destination before creating any staging
        // object. NOFOLLOW includes dangling symlinks; every other lookup error
        // also refuses. The final atomic no-replace publication remains required.
        const auto leafBytes = leaf.toUtf8();
        struct stat existing{};
        if (replacing) {
            if (::fstatat(parentFd.n, leafBytes.constData(), &existing, AT_SYMLINK_NOFOLLOW) ||
                !S_ISDIR(existing.st_mode) || existing.st_dev != replacing->value.st_dev ||
                existing.st_ino != replacing->value.st_ino || existing.st_mode != replacing->value.st_mode) refuse();
            recovery = replacing ? QDir(parentPath).filePath(stage) : QString();
        } else if (::fstatat(parentFd.n, leafBytes.constData(), &existing, AT_SYMLINK_NOFOLLOW) == 0 || errno != ENOENT) refuse();
        if (::mkdirat(parentFd.n, stage.toUtf8().constData(), 0700)) refuse();
        stageFd = below(parentFd.n, stage, true); stageIdentity = Identity(stageFd.n);
    }
#endif
};
quint64 AssistantResultExport::receiptPreparationBytes(const QByteArray& receipt) {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    return receipt_parser_bytes(receipt);
#else
    Q_UNUSED(receipt); refuse();
#endif
}
AssistantResultExport::AssistantResultExport(const ImmutableAssistantResult& source, const QString& parent, const QString& leaf) {
    prepare(source, parent, leaf, nullptr);
}
AssistantResultExport::AssistantResultExport(const ImmutableAssistantResult& source, std::shared_ptr<const AssistantWorkingFolder> folder, const QString& leaf,quint64 preparationLimit) {
    if (!folder) refuse();
    const auto parent = folder->path();
    prepare(source, parent, leaf, std::move(folder),{},preparationLimit);
}
AssistantResultExport::AssistantResultExport(const ImmutableAssistantResult& source, std::shared_ptr<const AssistantSaveSource> owned,
                                           std::shared_ptr<const AssistantWorkingFolder> folder,quint64 preparationLimit) {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    if (!owned || !owned->current()) refuse();
    const auto& path=owned->path();
    const auto slash=path.lastIndexOf('/');
    if(slash<0 || slash+1==path.size())refuse();
    ExportMetadata entrance(preparationLimit);
    entrance.add(2*sizeof(QString));entrance.rows(static_cast<quint64>(path.size()),sizeof(QChar));
    const auto parent=path.left(slash?slash:1);const auto leaf=path.mid(slash+1);
    prepare(source,parent,leaf,std::move(folder),std::move(owned),preparationLimit,entrance.peak);
#else
    Q_UNUSED(source);Q_UNUSED(owned);Q_UNUSED(folder);Q_UNUSED(preparationLimit);refuse();
#endif
}
void AssistantResultExport::prepare(const ImmutableAssistantResult& source, const QString& parent, const QString& leaf,
                                    std::shared_ptr<const AssistantWorkingFolder> folder, std::shared_ptr<const AssistantSaveSource> owned,quint64 preparationLimit,quint64 entranceBytes) {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    ExportMetadata metadata(preparationLimit);
    metadata.add(entranceBytes);
    auto* admitted=preparationLimit==std::numeric_limits<quint64>::max()?nullptr:&metadata;
    if(admitted) {
        metadata.add(sizeof(State)+sizeof(AssistantResultExport)+sizeof(std::unique_ptr<State>));
        metadata.rows(static_cast<quint64>(parent.size()),sizeof(QChar));
        metadata.rows(static_cast<quint64>(leaf.size()),sizeof(QChar));
        // These strings already belong to the captured capabilities; only
        // their known physical text enters descent/readback during export.
        admit_path_work(metadata,QStringView(parent));
        admit_path_work(metadata,QStringView(source.directory));
        admit_path_work(metadata,QStringView(parent),QStringView(leaf),true);
        const auto slash=source.directory.lastIndexOf('/');
        if(slash<0)refuse();
        const auto protectedParent=QStringView(source.directory).left(slash?slash:1);
        constexpr QStringView temporarySuffix=u"/result-XXXXXX";
        admit_path_work(metadata,protectedParent,temporarySuffix);
        const auto parentUnits=static_cast<quint64>(protectedParent.size());
        const auto copyUnits=parentUnits+static_cast<quint64>(temporarySuffix.size());
        // Parent substring; explicit template; Qt's clean template; Qt's final
        // decoded lease path; retained directory and retained recovery path.
        for(const auto units:std::array<quint64,6>{parentUnits,copyUnits,copyUnits,copyUnits,copyUnits,copyUnits})
            metadata.rows(units,sizeof(QChar));
        metadata.rows(6,sizeof(QString));
        // Pinned Qt6.11.2 create() owns one native temporary filename and one
        // native filesystem entry before its final decoded path is retained.
        const auto copyUtf8=path_utf8_bytes(protectedParent)+static_cast<quint64>(temporarySuffix.size());
        metadata.rows(copyUtf8,2);metadata.rows(2,sizeof(QByteArray));
        metadata.add(sizeof(QString)+2*sizeof(bool)+alignof(QString)); // QTemporaryDir private path/flags.
        metadata.add(sizeof(QString)+(sizeof("result-XXXXXX")-1)*sizeof(QChar)+5*sizeof(Fd)+2*sizeof(Identity)); // Factory leaf and descriptor bonds.
        metadata.add(Limits::error_bytes); // Existing bounded host-error presentation workspace.
    }
    if (!source.handle || (folder && !folder->current()) || (owned && !owned->current())) refuse();
    const bool alreadyPhysical=bool(folder)||bool(owned);
    // Picker/current-owned capabilities already capture physical paths and
    // recheck separation from all host storage through current(). Raw manual
    // Save As keeps its original canonical/reserved-root door.
    if(!alreadyPhysical) {
        const auto physicalParent=QFileInfo(parent).canonicalFilePath();
        const auto appData=QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
        for(const auto& reserved:{appData+"/assistant/agent",appData+"/assistant/results"}) {
            const auto physical=QFileInfo(reserved).canonicalFilePath();
            if(!physical.isEmpty() && (physicalParent==physical || physicalParent.startsWith(physical+'/')))refuse();
        }
    }
    // First export preserves the exact already-admitted saved native bytes.
    // Session refuses any intervening model edit; no unbounded serializer is invoked.
    const auto entries = manifest(source.receipt, source.intent, source.carried_tree,admitted);
    if(admitted) {
        admit_export_json(metadata,entries,source);
        // One second Entry vector is live either in nested protected loading or
        // as State::entries beside this original local vector. Its text/hash
        // payload is separate from the original receipt parser workspace.
        metadata.add(sizeof(std::vector<Entry>));
        metadata.rows(entries.size(),sizeof(Entry));
        quint64 depth=1;
        for(const auto& entry:entries) {
            metadata.rows(static_cast<quint64>(entry.path.size()),sizeof(QChar));
            metadata.add(64);
            const auto parts=static_cast<quint64>(entry.path.count('/'))+1;
            depth=std::max(depth,parts);
        }
        // Expected/before/after file sets coexist in verify. The one alias
        // workspace reuses the file-name role admitted by manifest; add the
        // actual carried-directory aliases (or four legal empty layout dirs).
        metadata.rows(3,sizeof(std::set<QString>));
        metadata.rows(entries.size(),3*sizeof(QString));
        for(const auto& entry:entries)
            metadata.rows(static_cast<quint64>(entry.path.size()),3*sizeof(QChar));
        metadata.rows(4,sizeof(QStringList)); // State/readback plus before/after closure.
        const auto directory_role=[&](QStringView path) {
            metadata.rows(4,sizeof(QString));
            metadata.rows(static_cast<quint64>(path.size()),4*sizeof(QChar));
            (void)admit_alias(path,metadata);
            depth=std::max(depth,static_cast<quint64>(path.count(u'/'))+2);
        };
        if(source.carried_tree)for(const auto& path:source.directories)directory_role(QStringView(path));
        else for(const auto path:std::array<QStringView,4>{u"structures",u"experiments",u"analysis",u"reports"})directory_role(path);
        const auto closureNormalization=metadata.normalizationScratch;
        metadata.add(closureNormalization);
        // Closure recursion holds ancestor component/path payloads. A foreign
        // raw leaf is rejected before alias normalization, but its decoding and
        // prefix concatenation may still reach 2*the admitted name cap+slash.
        metadata.rows(depth,sizeof(QByteArray)+2*sizeof(QString)+sizeof(Fd)+sizeof(struct stat)+sizeof(std::unique_ptr<DIR,decltype(&::closedir)>));
        metadata.rows(depth,3*Bounds::name_bytes+1+(3*Bounds::name_bytes+1)*sizeof(QChar));
        metadata.rows(2,sizeof(QStringList));
        metadata.rows(depth+1,sizeof(QString)); // Full split plus nested one-component lookup.
        metadata.add(2*Bounds::name_bytes+sizeof(QByteArray));
        metadata.add(Bounds::read_bytes+sizeof(QCryptographicHash)+32+64);
        // Exact known State destination strings, UUID stage/recovery names and
        // the constructor's component/encoding scratch. All parent/cache paths
        // above came from original physical capabilities, before any copy.
        metadata.rows(static_cast<quint64>(parent.size()),owned?3*sizeof(QChar):2*sizeof(QChar));
        metadata.rows(static_cast<quint64>(leaf.size()),2*sizeof(QChar));
        constexpr quint64 stageUnits=sizeof(".edi-export-")-1+36;
        metadata.rows(owned?2*stageUnits+2:stageUnits+1,sizeof(QChar));
        (void)admit_alias(QStringView(leaf),metadata); // Actual constructor case-fold comparison.
        metadata.rows(stageUnits,sizeof(QChar));
        if(metadata.normalizationScratch>closureNormalization)
            metadata.add(metadata.normalizationScratch-closureNormalization);
        metadata.add(2*sizeof(QByteArray)+path_utf8_bytes(QStringView(leaf))+stageUnits);
        const auto destinationUtf8=path_utf8_bytes(QStringView(parent))+1+path_utf8_bytes(QStringView(leaf));
        metadata.rows(2,sizeof(std::string));metadata.rows(destinationUtf8,2); // Verification Project path/metadata.path.
        metadata.add(sizeof(ImmutableAssistantResult)+sizeof(AssistantResultDirectory)+sizeof(QTemporaryDir)+
            2*sizeof(std::shared_ptr<ImmutableAssistantResult>)+2*sizeof(std::shared_ptr<AssistantResultDirectory>));
    }
    verify(source.handle->descriptor.n, entries, -1, source.carried_tree, source.carried_tree ? &source.directories : nullptr);
    (void)load_captured_assistant_result(source);
    auto pinned = folder && !owned ? Fd(::dup(folder->state_->descriptor.n)) : State::selectedParent(parent,alreadyPhysical);
    auto state = std::make_unique<State>(parent, leaf, std::move(pinned), owned ? &owned->state_->identity : nullptr);
    if (folder && (!folder->current() || (!owned && !folder->state_->identity.object(state->parentFd.n)))) refuse();
    state->physicalParent=alreadyPhysical;
    state->owned = std::move(owned); state->carried = source.carried_tree; state->directories = source.directories;
    if (state->owned && folder && folder->path() == state->destination) {
        state->grantReplacement = Fd(::dup(state->stageFd.n));
        state->replacementIdentity.emplace(state->grantReplacement.n);
    }
    // Pre-own one protected actual-published-byte validation slot before commit.
    // Never pass a runtime-writable chosen-root tree to the path-based loader.
    state->grant = std::move(folder);
    state->reopenCopy = owned_result_snapshot(source);
    state->reopenCopy->carried_tree = source.carried_tree; state->reopenCopy->directories = source.directories;
    own_receipt(*state->reopenCopy, entries);
    try {
        // Pinning both objects prevents a substituted parent path from redirecting writes.
        verify(source.handle->descriptor.n, entries, state->stageFd.n, state->carried, state->carried ? &state->directories : nullptr);
        verify(state->stageFd.n, entries, -1, state->carried, state->carried ? &state->directories : nullptr);
        // The source was really loaded from protected bytes; the written stage
        // must exactly match that admitted closure before publication.
        state->files = receipt_files(entries); state->entries = entries;
    } catch (...) {
        // Deliberately leave the bounded unpublished directory for recovery.
        // There is no portable inode-conditional recursive unlink; a pathname
        // cleanup must never delete a substituted foreign object.
        throw;
    }
    state->preparationBytes=admitted?metadata.peak:0;
    state_ = std::move(state);
#else
    Q_UNUSED(source); Q_UNUSED(parent); Q_UNUSED(leaf); Q_UNUSED(folder); Q_UNUSED(owned); Q_UNUSED(preparationLimit); Q_UNUSED(entranceBytes); refuse();
#endif
}
AssistantResultExport::~AssistantResultExport() = default; // Descriptor cleanup only; never delete by a mutable path.
void AssistantResultExport::publish(const std::function<bool()>& current) {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    auto& s = *state_;
    // Allocate syscall arguments before the final namespace/currentness bond.
    const auto stageName = s.stage.toUtf8();
    const auto leafName = s.leaf.toUtf8();
    verify(s.stageFd.n, s.entries, -1, s.carried, s.carried ? &s.directories : nullptr);
    if (!current() || (s.grant && !s.grant->current()) || (s.owned && !s.owned->current())) refuse();
    // Hashing and host-currentness can be lengthy. Only now revalidate the
    // actual selected parent and named source that rename will consume.
    auto parent = State::selectedParent(s.parent,s.physicalParent);
    if (!s.parentIdentity.object(parent.n) || (s.grant && !s.owned && !s.grant->state_->identity.object(parent.n))) refuse();
    auto stage = below(parent.n, s.stage, true);
    if (!s.stageIdentity.object(stage.n)) refuse();
    if (s.owned) {
        auto original = below(parent.n, s.leaf, true);
        if (!s.owned->state_->identity.object(original.n) || !s.owned->current()) refuse();
    }
    int outcome = -1;
#if defined(__linux__) && defined(SYS_renameat2)
    outcome = static_cast<int>(::syscall(SYS_renameat2, s.parentFd.n, stageName.constData(), s.parentFd.n, leafName.constData(), s.owned ? RENAME_EXCHANGE : RENAME_NOREPLACE));
#elif defined(__APPLE__)
    outcome = ::renameatx_np(s.parentFd.n, stageName.constData(), s.parentFd.n, leafName.constData(), s.owned ? RENAME_SWAP : RENAME_EXCL);
#endif
    if (outcome != 0) throw std::runtime_error("Project publication was refused: its exact destination changed or the required atomic operation is unavailable");
    s.committed = true; // The namespace changed, even if later identity/readback refuses.
    if (s.grant && s.replacementIdentity) {
        s.grant->state_->descriptor = std::move(s.grantReplacement);
        s.grant->state_->identity = *s.replacementIdentity;
    }
    if (s.owned) {
        auto previous = below(s.parentFd.n, s.stage, true);
        auto installed = below(s.parentFd.n, s.leaf, true);
        if (!s.owned->state_->identity.object(previous.n) || !s.stageIdentity.object(installed.n))
            throw std::runtime_error("The save changed its destination namespace but could not verify the original exchange; both trees were retained");
    }
#else
    Q_UNUSED(current); refuse();
#endif
}
edi::Project AssistantResultExport::reopen() const {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    auto& s = *state_;
    if (!s.committed) refuse();
    auto parent = State::selectedParent(s.parent,s.physicalParent); auto final = below(parent.n, s.leaf, true);
    if (!s.parentIdentity.object(parent.n) || !s.stageIdentity.object(final.n)) refuse();
    verify(s.stageFd.n, s.entries, -1, s.carried, s.carried ? &s.directories : nullptr);
    if (!s.reopenCopy || !s.reopenCopy->handle) refuse();
    if (!s.reopenCopied) {
        verify(s.stageFd.n, s.entries, s.reopenCopy->handle->descriptor.n, s.carried, s.carried ? &s.directories : nullptr);
        verify(s.reopenCopy->handle->descriptor.n, s.entries, -1, s.carried, s.carried ? &s.directories : nullptr);
        s.reopenCopied = true;
    }
    auto result = load_captured_assistant_result(*s.reopenCopy);
    verify(s.stageFd.n, s.entries, -1, s.carried, s.carried ? &s.directories : nullptr);
    check_assistant_result_mode(result);
    auto again = below(parent.n, s.leaf, true);
    if (!s.stageIdentity.object(again.n)) refuse();
    result.path = s.destination.toStdString(); result.metadata.path = result.path;
    return result;
#else
    refuse();
#endif
}
std::shared_ptr<ImmutableAssistantReport> capture_assistant_report(const QString& workspace, const QString& relative, quint64 remaining) {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    if (relative.isEmpty() || QDir::isAbsolutePath(relative) || relative.toUtf8().size() > static_cast<qsizetype>(Bounds::name_bytes)) refuse();
    const auto suffix = QFileInfo(relative).suffix().toLower();
    if (suffix != "html" && suffix != "htm" && suffix != "pdf") refuse();
    auto root = directory(workspace);
    const Identity rootIdentity(root.n);
    const auto parentName = QFileInfo(relative).path();
    const auto leaf = QFileInfo(relative).fileName(); validate_assistant_result_leaf(leaf);
    auto sourceRoot = parentName == "." ? Fd(::openat(root.n, ".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)) : below(root.n, parentName, true);
    const Identity sourceRootIdentity(sourceRoot.n);
    auto result = std::make_shared<ImmutableAssistantReport>();
    const auto cache = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation) + "/assistant/report-views";
    if (!QDir().mkpath(cache)) refuse();
    result->lease = std::make_shared<QTemporaryDir>(cache + "/report-XXXXXX");
    if (!result->lease->isValid()) refuse();
    const auto physicalCopy = QFileInfo(result->lease->path()).canonicalFilePath();
    const auto agentRoot = QFileInfo(QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation) + "/assistant/agent").canonicalFilePath();
    if (physicalCopy.isEmpty() || agentRoot.isEmpty() || physicalCopy == agentRoot || physicalCopy.startsWith(agentRoot + '/')) refuse();
    auto destination = directory(physicalCopy);
    struct Source { QString path; Identity identity; bool directory; };
    std::vector<Source> admitted; std::set<QString> aliases;
    std::size_t entries = 0;
    const auto copyTree = [&](auto&& self, int from, int to, const QString& prefix, std::size_t depth) -> void {
        if (depth > Limits::json_depth) refuse();
        Fd scan(::openat(from, ".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC));
        DIR* raw = ::fdopendir(scan.n); if (!raw) refuse(); scan.n = -1;
        std::unique_ptr<DIR, decltype(&::closedir)> stream(raw, ::closedir);
        for (;;) {
            errno = 0; auto* entry = ::readdir(raw);
            if (!entry) { if (errno) refuse(); break; }
            const QByteArray rawName(entry->d_name); if (rawName == "." || rawName == "..") continue;
            if (++entries > Bounds::files) refuse();
            const auto name = QString::fromUtf8(rawName); if (name.toUtf8() != rawName) refuse(); validate_assistant_result_leaf(name);
            const auto path = prefix.isEmpty() ? name : prefix + '/' + name;
            if (path.toUtf8().size() > static_cast<qsizetype>(Bounds::name_bytes) || !aliases.insert(path.normalized(QString::NormalizationForm_C).toCaseFolded()).second) refuse();
            struct stat st{}; if (::fstatat(from, rawName.constData(), &st, AT_SYMLINK_NOFOLLOW)) refuse();
            const bool isDirectory = S_ISDIR(st.st_mode);
            if (!isDirectory && !S_ISREG(st.st_mode)) refuse();
            auto input = below(from, name, isDirectory);
            const Identity identity(input.n);
            admitted.push_back({path, identity, isDirectory});
            if (isDirectory) {
                if (::mkdirat(to, rawName.constData(), 0700)) refuse();
                auto child = below(to, name, true); self(self, input.n, child.n, path, depth + 1);
            } else {
                const auto bytes = read_file(input.n, std::min<quint64>(Bounds::file_bytes, remaining - result->bytes));
                Fd output(::openat(to, rawName.constData(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600));
                qsizetype written = 0;
                while (written < bytes.size()) {
                    const auto n = ::write(output.n, bytes.constData() + written, static_cast<std::size_t>(bytes.size() - written));
                    if (n < 0) { if (errno == EINTR) continue; refuse(); }
                    if (!n) refuse(); written += n;
                }
                if (::fchmod(output.n, 0400)) refuse();
                result->bytes += static_cast<quint64>(bytes.size());
            }
        }
    };
    // Preserve the entry point and its local relative assets, not a renamed
    // text-only HTML file. No HTML is parsed/re-written and no URI is fetched.
    if (suffix == "pdf") {
        auto input = below(sourceRoot.n, leaf);
        const auto bytes = read_file(input.n, std::min<quint64>(Bounds::file_bytes, remaining));
        admitted.push_back({leaf, Identity(input.n), false});
        Fd output(::openat(destination.n, leaf.toUtf8().constData(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600));
        qsizetype written = 0;
        while (written < bytes.size()) { const auto n = ::write(output.n, bytes.constData() + written, static_cast<std::size_t>(bytes.size() - written)); if (n < 0) { if (errno == EINTR) continue; refuse(); } if (!n) refuse(); written += n; }
        if (::fchmod(output.n, 0400)) refuse(); result->bytes = static_cast<quint64>(bytes.size());
    } else copyTree(copyTree, sourceRoot.n, destination.n, {}, 0);
    for (const auto& source : admitted) { auto check = below(sourceRoot.n, source.path, source.directory); if (!source.identity.unchanged(check.n)) refuse(); }
    auto rootAgain = directory(workspace);
    auto sourceAgain = parentName == "." ? Fd(::openat(rootAgain.n, ".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)) : below(rootAgain.n, parentName, true);
    if (!rootIdentity.object(rootAgain.n) || !sourceRootIdentity.unchanged(sourceAgain.n)) refuse();
    auto entryPoint = below(destination.n, leaf); // The actual linked report must exist in the copy.
    result->file = physicalCopy + '/' + leaf;
    return result;
#else
    Q_UNUSED(workspace); Q_UNUSED(relative); Q_UNUSED(remaining); refuse();
#endif
}
quint64 AssistantResultExport::preparationBytes() const noexcept { return state_?state_->preparationBytes:0; }
bool AssistantResultExport::committed() const noexcept { return state_ && state_->committed; }
const QString& AssistantResultExport::destination() const noexcept { return state_->destination; }
const QJsonArray& AssistantResultExport::files() const noexcept { return state_->files; }
const QString& AssistantResultExport::recoveryDirectory() const noexcept { return state_->recovery; }
} // namespace edi_app

