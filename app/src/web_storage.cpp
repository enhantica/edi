// SPDX-License-Identifier: BSD-3-Clause
#include "web_storage.hpp"

#include "edi/project_archive.hpp"

#include <QCoreApplication>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPointer>
#include <QQmlEngine>
#include <algorithm>
#include <cstdlib>
#include <cstdint>

#if defined(Q_OS_WASM)
#include <emscripten.h>
#include <emscripten/val.h>

// The page's side of the storage (edi ADR-0052 §9), installed once as globalThis.ediStorage. A job's files are staged
// from the app's memory first (stage), then one call starts the job; its answer goes back through
// Module._edi_storage_answered(job, json). The browser's own storage is written from a small worker, whose
// synchronous file handles every current browser has; the disk is written through the File System Access API.
// Records: IndexedDB "edi-projects", store "places", one per place by its key. Files: the origin private file system
// under edi/projects/<key> and edi/recovery/<key>.
EM_JS_DEPS(edi_web_storage, "$FS,$stringToNewUTF8,$UTF8ToString,$Emval,_emval_decref");

EM_JS(int, edi_storage_install, (), {
    if (globalThis.ediStorage) {
        return globalThis.ediStorage.disk ? 1 : 0;
    }
    const S = {handles : new Map(), staged : new Map(), workerJobs : new Map(), runs : new Map(), next : 1};
    globalThis.ediStorage = S;
    S.disk = typeof globalThis.showDirectoryPicker === "function" && typeof globalThis.showOpenFilePicker === "function"
             && typeof globalThis.showSaveFilePicker === "function";
    S.answer = (job, value) => {
        const text = stringToNewUTF8(JSON.stringify(value));
        Module._edi_storage_answered(job, text);
    };
    S.fail = (job, error) => {
        if (error && error.name === "AbortError") {
            S.answer(job, {cancelled : true});
        } else {
            S.answer(job, {ok : false, message : String(error && error.message ? error.message : error)});
        }
    };
    S.policy = (operation, value) => {
        const result = Module._edi_storage_policy(operation, Emval.toHandle(value));
        try { return Emval.toValue(result); } finally { __emval_decref(result); }
    };
    S.key = () => S.policy(0, undefined);

    S.db = () => S.opened || (S.opened = new Promise((resolve, reject) => {
        const request = indexedDB.open("edi-projects", 1);
        request.onupgradeneeded = () => request.result.createObjectStore("places", {keyPath : "key"});
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    }));
    S.store = (mode, act) => S.db().then(db => new Promise((resolve, reject) => {
        const transaction = db.transaction("places", mode);
        const request = act(transaction.objectStore("places"));
        transaction.oncomplete = () => resolve(request ? request.result : undefined);
        transaction.onerror = () => reject(transaction.error);
        transaction.onabort = () => reject(transaction.error);
    }));
    S.record = key => S.store("readonly", store => store.get(key));
    S.put = record => S.store("readwrite", store => store.put(record));
    S.remove = key => S.store("readwrite", store => store.delete(key));

    S.opfs = async (parts, create) => {
        let folder = await navigator.storage.getDirectory();
        for (const part of parts) {
            folder = await folder.getDirectoryHandle(part, {create : create});
        }
        return folder;
    };
    S.walk = async (folder, prefix, out) => {
        for await (const [name, handle] of folder.entries()) {
            const path = prefix ? prefix + "/" + name : name;
            if (handle.kind === "directory") {
                await S.walk(handle, path, out);
            } else {
                out.push([ path, handle ]);
            }
        }
        return out;
    };
    S.copyIn = async (folder, root) => {
        const files = await S.walk(folder, "", []);
        for (const [path, handle] of files) {
            const data = new Uint8Array(await (await handle.getFile()).arrayBuffer());
            const full = root + "/" + path;
            FS.mkdirTree(full.substring(0, full.lastIndexOf("/")));
            FS.writeFile(full, data);
        }
        return files.map(file => file[0]);
    };
    S.writeTo = async (folder, files) => {
        for (const [path, data] of files) {
            const names = path.split("/");
            let at = folder;
            for (const name of names.slice(0, -1)) {
                at = await at.getDirectoryHandle(name, {create : true});
            }
            const writable = await (await at.getFileHandle(names[names.length - 1], {create : true})).createWritable();
            await writable.write(data);
            await writable.close();
        }
    };
    // Only an entry proven missing counts as removed; any other refusal fails the write, so the place keeps its
    // known files and the project stays unsaved.
    S.missing = error => error && error.name === "NotFoundError";
    S.removePath = async (folder, path) => {
        const names = path.split("/");
        let at = folder;
        try {
            for (const name of names.slice(0, -1)) {
                at = await at.getDirectoryHandle(name);
            }
            await at.removeEntry(names[names.length - 1]);
        } catch (error) {
            if (!S.missing(error)) {
                throw error;
            }
        }
    };
    // The documents a project save writes in a folder and replaces there (as the app's desktop save does): the entity
    // documents directly in structures/ and experiments/, and the analysis document. Anything else stays.
    S.owned = async folder => {
        const owned = S.policy(13, undefined);
        for (const category of S.policy(14, undefined)) {
            let at;
            try {
                at = await folder.getDirectoryHandle(category);
            } catch (error) {
                if (S.missing(error)) continue;
                throw error;
            }
            for await (const [name, handle] of at.entries()) {
                const path = S.policy(1, {category : category, name : name, handle : handle});
                if (path !== null) owned.push(path);
            }
        }
        return owned;
    };
    S.permitted = async handle => {
        const mode = {mode : "readwrite"};
        return (await handle.queryPermission(mode)) === "granted" || (await handle.requestPermission(mode)) === "granted";
    };
    S.handle = async key => {
        let handle = S.handles.get(key);
        if (!handle) {
            const record = await S.record(key);
            handle = record && record.handle;
            if (handle) {
                S.handles.set(key, handle);
            }
        }
        if (!handle) {
            throw new Error("the place on the disk is no longer known to this browser");
        }
        return handle;
    };

    // A picked folder becomes the project's place on the disk.
    S.openFolder = async (handle, root) => {
        const key = S.key();
        S.handles.set(key, handle);
        S.policy(2, {key : key, paths : await S.copyIn(handle, S.policy(8, {root : root, name : handle.name}))});
        await S.put(S.policy(12, {key : key, kind : "folder", name : handle.name, handle : handle}));
        return S.policy(18, {key : key, kind : "folder", handle : handle, root : root});
    };
    // The browser storage writer: a dedicated worker with synchronous access handles, which Firefox and Safari offer
    // where they offer no writable streams. It writes every file of a job, then removes what the folder has besides.
    const writerMain = () => {
        const pendingPlans = new Map();
        const walk = async (folder, prefix, out) => {
            for await (const [name, handle] of folder.entries()) {
                const path = prefix ? prefix + "/" + name : name;
                out.push([ path, handle.kind ]);
                if (handle.kind === "directory") {
                    await walk(handle, path, out);
                }
            }
            return out;
        };
        onmessage = async event => {
            if (event.data.phase === "retention") {
                const done = pendingPlans.get(event.data.id);
                pendingPlans.delete(event.data.id);
                done(event.data);
                return;
            }
            const {id, parts, files} = event.data;
            try {
                let folder = await navigator.storage.getDirectory();
                for (const part of parts) {
                    folder = await folder.getDirectoryHandle(part, {create : true});
                }
                const paths = [];
                for (const [path, data] of files) {
                    paths.push(path);
                    const names = path.split("/");
                    let at = folder;
                    for (const name of names.slice(0, -1)) {
                        at = await at.getDirectoryHandle(name, {create : true});
                    }
                    const file = await at.getFileHandle(names[names.length - 1], {create : true});
                    const access = await file.createSyncAccessHandle();
                    access.truncate(0);
                    access.write(data, {at : 0});
                    access.flush();
                    access.close();
                }
                const entries = await walk(folder, "", []);
                const plan = await new Promise(resolve => {
                    pendingPlans.set(id, resolve);
                    postMessage({id : id, phase : "retention", entries : entries, paths : paths});
                });
                if (plan.error !== undefined) throw new Error(plan.error);
                for (const path of plan.paths) {
                    const names = path.split("/");
                    let at = folder;
                    for (const name of names.slice(0, -1)) {
                        at = await at.getDirectoryHandle(name);
                    }
                    await at.removeEntry(names[names.length - 1], {recursive : true});
                }
                postMessage({id : id, ok : true});
            } catch (error) {
                postMessage({id : id, ok : false, message : String(error && error.message ? error.message : error)});
            }
        };
    };
    S.writer = () => {
        if (!S.worker) {
            const source = "(" + writerMain.toString() + ")();";
            S.worker = new Worker(URL.createObjectURL(new Blob([source], {type : "text/javascript"})));
            S.worker.onmessage = event => {
                if (event.data.phase === "retention") {
                    try {
                        S.worker.postMessage({id : event.data.id, phase : "retention", paths : S.policy(4, event.data)});
                    } catch (error) {
                        S.worker.postMessage({id : event.data.id, phase : "retention", error : String(error && error.message ? error.message : error)});
                    }
                    return;
                }
                const done = S.workerJobs.get(event.data.id);
                S.workerJobs.delete(event.data.id);
                if (done) {
                    done(event.data);
                }
            };
        }
        return S.worker;
    };
    S.writeBrowser = (parts, files) => new Promise((resolve, reject) => {
        const id = S.next++;
        S.workerJobs.set(id, result => result.ok ? resolve() : reject(new Error(result.message)));
        S.writer().postMessage({id : id, parts : parts, files : files});
    });

    // Choosers of the page itself, where the browser has no File System Access: a folder or an archive is uploaded.
    S.upload = (kind, root) => new Promise((resolve, reject) => {
        document.getElementById("edi-open-project")?.remove();
        const input = document.createElement("input");
        input.type = "file";
        input.id = "edi-open-project";
        input.style.display = "none";
        if (kind === "folder") {
            input.webkitdirectory = true;
            input.multiple = true;
        } else {
            input.accept = ".zip,application/zip";
        }
        input.addEventListener("cancel", () => {
            input.remove();
            reject(new DOMException("cancelled", "AbortError"));
        });
        input.addEventListener("change", async () => {
            const files = Array.from(input.files);
            input.remove();
            try {
                if (files.length === 0) {
                    throw new DOMException("cancelled", "AbortError");
                }
                for (const file of files) {
                    const path = root + "/" + (file.webkitRelativePath || file.name);
                    FS.mkdirTree(path.substring(0, path.lastIndexOf("/")));
                    FS.writeFile(path, new Uint8Array(await file.arrayBuffer()));
                }
                const first = files[0].webkitRelativePath || files[0].name;
                const name = first.split("/")[0];
                resolve({ok : true, kind : "browser", name : name, path : root + "/" + name});
            } catch (error) {
                reject(error);
            }
        });
        document.body.appendChild(input);
        input.click();
    });
    return S.disk ? 1 : 0;
});

// Whether the browser lets the page keep files: a private window may refuse its storage or give it no room (Safari
// answers with UnknownError). One small file is written through the same worker and removed again.
EM_JS(void, edi_storage_probe, (int job), {
    const S = globalThis.ediStorage;
    (async () => {
        await S.writeBrowser([ "edi", "probe" ], [ [ "probe", new Uint8Array([1]) ] ]);
        await (await S.opfs(["edi"], false)).removeEntry("probe", {recursive : true});
        return {ok : true};
    })().then(value => S.answer(job, value), error => S.answer(job, {ok : false, message : String(error)}));
});

EM_JS(void, edi_storage_stage, (int job, const char* path, const char* data, int size), {
    const S = globalThis.ediStorage;
    if (!S.staged.has(job)) {
        S.staged.set(job, []);
    }
    S.staged.get(job).push([ UTF8ToString(path), HEAPU8.slice(data, data + size) ]);
});

EM_JS(void, edi_storage_pick_open, (int job, const char* kind_utf8, const char* root_utf8), {
    const S = globalThis.ediStorage;
    const kind = UTF8ToString(kind_utf8);
    const root = UTF8ToString(root_utf8);
    (async () => {
        if (!S.disk) {
            return await S.upload(kind, root);
        }
        if (kind === "folder") {
            return await S.openFolder(await showDirectoryPicker({id : "edi-project", mode : "readwrite"}), root);
        }
        const [handle] = await showOpenFilePicker(
            {id : "edi-project", types : [ {description : "edi project archive", accept : {"application/zip" : [".zip"]}} ]});
        const file = await handle.getFile();
        const path = root + "/" + file.name;
        FS.mkdirTree(root);
        FS.writeFile(path, new Uint8Array(await file.arrayBuffer()));
        // An archive the user does not let the page write is worked on in the browser.
        if (!(await S.permitted(handle))) {
            return {ok : true, kind : "browser", name : file.name, path : path};
        }
        const key = S.key();
        S.handles.set(key, handle);
        await S.put(S.policy(12, {key : key, kind : "zip", name : file.name, handle : handle}));
        return {ok : true, key : key, kind : "zip", name : file.name, path : path};
    })().then(value => S.answer(job, value), error => S.fail(job, error));
});

EM_JS(void, edi_storage_pick_save, (int job, const char* kind_utf8, const char* suggested_utf8, const char* start_utf8), {
    const S = globalThis.ediStorage;
    const kind = UTF8ToString(kind_utf8);
    const suggested = UTF8ToString(suggested_utf8);
    const start = S.handles.get(UTF8ToString(start_utf8));
    // Where the project is on the disk, else the user's documents; a .zip is offered under its name.
    const options = {id : "edi-project", startIn : start || "documents"};
    (async () => {
        let handle;
        if (kind === "folder") {
            options.mode = "readwrite";
            handle = await showDirectoryPicker(options);
        } else {
            options.suggestedName = suggested;
            options.types = [ {description : "Project archive", accept : {"application/zip" : [".zip"]}} ];
            handle = await showSaveFilePicker(options);
        }
        const key = S.key();
        S.handles.set(key, handle);
        if (kind === "folder") {
            // A folder holding another project: its documents the save does not write again are removed with it.
            S.policy(2, {key : key, paths : await S.owned(handle)});
        }
        return {ok : true, key : key, kind : kind, name : handle.name};
    })().then(value => S.answer(job, value), error => S.fail(job, error));
});

EM_JS(void, edi_storage_write, (int job, const char* key_utf8, const char* kind_utf8, const char* name_utf8, int recovery), {
    const S = globalThis.ediStorage;
    const key = UTF8ToString(key_utf8);
    const kind = UTF8ToString(kind_utf8);
    const name = UTF8ToString(name_utf8);
    const files = S.staged.get(job) || [];
    S.staged.delete(job);
    S.runs.set(job, async () => {
        let handle = null;
        const destination = S.policy(15, {kind : kind, recovery : recovery});
        if (destination === "browser") {
            await S.writeBrowser(S.policy(7, {key : key, recovery : recovery}), files);
        } else if (destination === "folder") {
            handle = await S.handle(key);
            if (!(await S.permitted(handle))) {
                throw new Error("the browser was not allowed to write to the folder " + handle.name);
            }
            await S.writeTo(handle, files);
            const paths = files.map(file => file[0]);
            for (const path of S.policy(3, {key : key, paths : paths})) {
                await S.removePath(handle, path);
            }
            S.policy(2, {key : key, paths : paths});
        } else {
            handle = await S.handle(key);
            if (!(await S.permitted(handle))) {
                throw new Error("the browser was not allowed to write to " + handle.name);
            }
            const writable = await handle.createWritable();
            await writable.write(files.length > 0 ? files[0][1] : new Uint8Array());
            await writable.close();
        }
        const record = await S.record(key);
        await S.put(S.policy(5, {record : record, key : key, kind : kind, name : name, handle : handle, recovery : recovery}));
        return {ok : true};
    });
});


EM_JS(void, edi_storage_load, (int job, const char* key_utf8, int recovery, const char* root_utf8), {
    const S = globalThis.ediStorage;
    const key = UTF8ToString(key_utf8);
    const root = UTF8ToString(root_utf8);
    (async () => {
        const record = await S.record(key);
        if (S.policy(6, {record : record, recovery : recovery})) {
            const folder = await S.opfs(S.policy(7, {key : key, recovery : recovery}), false);
            await S.copyIn(folder, S.policy(8, {root : root, name : record.name}));
            return S.policy(17, {key : key, record : record, root : root});
        }
        const handle = await S.handle(key);
        if (!(await S.permitted(handle))) {
            throw new Error("the browser was not allowed to open " + handle.name);
        }
        if (S.policy(16, {record : record})) {
            S.policy(2, {key : key, paths : await S.copyIn(handle, S.policy(8, {root : root, name : handle.name}))});
            return S.policy(18, {key : key, kind : "folder", handle : handle, root : root});
        }
        const file = await handle.getFile();
        FS.mkdirTree(root);
        FS.writeFile(S.policy(8, {root : root, name : file.name}), new Uint8Array(await file.arrayBuffer()));
        return S.policy(18, {key : key, kind : "zip", handle : file, root : root});
    })().then(value => S.answer(job, value), error => S.fail(job, error));
});


EM_JS(void, edi_storage_list, (int job), {
    const S = globalThis.ediStorage;
    S.store("readonly", store => store.getAll())
        .then(records => S.answer(job, {ok : true, places : records.map(record => S.policy(11, {record : record}))}), error => S.fail(job, error));
});


EM_JS(void, edi_storage_drop, (int job, const char* key_utf8, int whole), {
    const S = globalThis.ediStorage;
    const key = UTF8ToString(key_utf8);
    S.runs.set(job, async () => {
        const record = await S.record(key);
        const removed = [];
        for (const part of S.policy(10, {whole : whole})) {
            try {
                await (await S.opfs([ "edi", part ], false)).removeEntry(key, {recursive : true});
            } catch (error) {
                if (!S.missing(error)) {
                    // Keep the original removal refusal; a proven earlier removal can still update its metadata.
                    try {
                        if (S.policy(20, {record : record, removed : removed})) await S.put(record);
                    } finally {
                        throw error;
                    }
                }
            }
            removed.push(part);
        }
        const disposition = S.policy(9, {record : record, whole : whole});
        if (disposition === "remove") {
            await S.remove(key);
        } else if (disposition === "put") {
            await S.put(record);
        }
        S.handles.delete(key);
        return {ok : true};
    });
});


// One browser-realm primitive operation; native WebStorage selects every operand and policy step.
EM_JS(emscripten::EM_VAL, edi_storage_add, (emscripten::EM_VAL left, emscripten::EM_VAL right), {
    return Emval.toHandle(Emval.toValue(left) + Emval.toValue(right));
});

// Browser promise turns are scheduling/I/O adapters; WebStorage alone selects the next job for each place.
EM_JS(void, edi_storage_resume, (int job), {
    const S = globalThis.ediStorage;
    const run = S.runs.get(job);
    S.runs.delete(job);
    const next = Promise.resolve().then(run);
    // Queue liveness is independent of answer delivery, matching the original caught tail's microtask order.
    next.then(() => Module._edi_storage_serial_finished(job), () => Module._edi_storage_serial_finished(job));
    next.then(value => S.answer(job, value), error => S.fail(job, error));
});

extern "C" EMSCRIPTEN_KEEPALIVE emscripten::EM_VAL edi_storage_policy(int operation, emscripten::EM_VAL input) {
    const auto value = emscripten::val::take_ownership(input);
    return edi_app::WebStorage::policy(operation, value).release_ownership();
}
extern "C" EMSCRIPTEN_KEEPALIVE void edi_storage_serial_finished(int job) { edi_app::WebStorage::serialFinished(job); }

extern "C" EMSCRIPTEN_KEEPALIVE void edi_storage_answered(int job, char* json) {
    const QString text = QString::fromUtf8(json);
    std::free(json);
    edi_app::WebStorage::answered(job, text);
}
#endif

namespace edi_app {

namespace {
QPointer<WebStorage>& the_instance() {
    static QPointer<WebStorage> instance;
    return instance;
}

QJsonObject object_of(const QString& json) { return QJsonDocument::fromJson(json.toUtf8()).object(); }

WebStorageAnswer answer_of(const QString& json) {
    const QJsonObject object = object_of(json);
    WebStorageAnswer answer;
    answer.ok = object.value(QStringLiteral("ok")).toBool();
    answer.cancelled = object.value(QStringLiteral("cancelled")).toBool();
    answer.message = object.value(QStringLiteral("message")).toString();
    answer.key = object.value(QStringLiteral("key")).toString();
    answer.kind = object.value(QStringLiteral("kind")).toString();
    answer.name = object.value(QStringLiteral("name")).toString();
    answer.path = object.value(QStringLiteral("path")).toString();
    return answer;
}

// A refusal as the script would have sent it, for a job that fails before reaching the script.
[[maybe_unused]] QString refusal(const QString& message) {
    const QJsonObject object{{QStringLiteral("ok"), false}, {QStringLiteral("message"), message}};
    return QString::fromUtf8(QJsonDocument(object).toJson(QJsonDocument::Compact));
}

[[maybe_unused]] WebStorageAnswer refused(const QString& message) {
    WebStorageAnswer answer;
    answer.message = message;
    return answer;
}
}  // namespace

// ---- WebPlaceListModel --------------------------------------------------------------------------

int WebPlaceListModel::rowCount(const QModelIndex& parent) const {
    return parent.isValid() ? 0 : static_cast<int>(places_.size());
}

QVariant WebPlaceListModel::data(const QModelIndex& index, int role) const {
    const Place* place = index.isValid() ? at(index.row()) : nullptr;
    if (place == nullptr) {
        return {};
    }
    switch (role) {
        case KeyRole: return place->key;
        case KindRole: return place->kind;
        case NameRole: return place->name;
        case SavedRole: return place->saved;
        case RecoveryRole: return place->recovery;
        default: return {};
    }
}

QHash<int, QByteArray> WebPlaceListModel::roleNames() const {
    return {{KeyRole, "key"}, {KindRole, "kind"}, {NameRole, "name"}, {SavedRole, "saved"}, {RecoveryRole, "recovery"}};
}

const WebPlaceListModel::Place* WebPlaceListModel::at(int row) const {
    return row >= 0 && row < places_.size() ? &places_[row] : nullptr;
}

QString WebPlaceListModel::key(int row) const { return at(row) != nullptr ? at(row)->key : QString(); }
QString WebPlaceListModel::kind(int row) const { return at(row) != nullptr ? at(row)->kind : QString(); }
QString WebPlaceListModel::name(int row) const { return at(row) != nullptr ? at(row)->name : QString(); }
bool WebPlaceListModel::saved(int row) const { return at(row) != nullptr && at(row)->saved; }
bool WebPlaceListModel::recovery(int row) const { return at(row) != nullptr && at(row)->recovery; }

void WebPlaceListModel::setPlaces(QList<Place> places) {
    const bool counted = places.size() != places_.size();
    beginResetModel();
    places_ = std::move(places);
    endResetModel();
    if (counted) {
        emit countChanged();
    }
}

// ---- WebStorage ---------------------------------------------------------------------------------

#if defined(Q_OS_WASM)
namespace {
using emscripten::val;
QString storage_text(const val& value) { return QString::fromStdU16String(value.as<std::u16string>()); }
val storage_add(const val& left, const val& right) { return val::take_ownership(edi_storage_add(left.as_handle(), right.as_handle())); }
val storage_string(const QString& value) { return val(value.toStdU16String()); }
QStringList storage_paths(const val& values) {
    QStringList paths;
    for (const val& value : values) { const auto path = storage_text(value); if (!paths.contains(path)) paths.append(path); }
    return paths;
}
val storage_array(const QStringList& paths) {
    val out = val::array(); unsigned index = 0; for (const QString& path : paths) out.set(index++, storage_string(path)); return out;
}
val storage_path(const val& root, const val& name) { const auto prefix = storage_add(root, val("/")); return storage_add(prefix, name); }
val storage_result(const val& args, bool handle) {
    val out = val::object(); out.set("ok", true); out.set("key", args["key"]);
    out.set("kind", handle ? args["kind"] : args["record"]["kind"]);
    out.set("name", handle ? args["handle"]["name"] : args["record"]["name"]);
    out.set("path", storage_path(args["root"], handle ? args["handle"]["name"] : args["record"]["name"])); return out;
}
} // namespace

emscripten::val WebStorage::policy(int operation, const emscripten::val& args) {
    using emscripten::val;
    if (operation == 0) {
        const auto stamp = val::global("Date").call<val>("now").call<val>("toString", 36);
        const auto prefix = storage_add(stamp, val("-"));
        const auto suffix = val::global("Math").call<val>("random").call<val>("toString", 36).call<val>("slice", 2, 10);
        return storage_add(prefix, suffix);
    }
    if (operation == 1) {
        if (!args["handle"]["kind"].strictlyEquals(val("file")) || !args["name"].call<val>("toLowerCase").call<bool>("endsWith", val(".edi"))) return val::null();
        return storage_path(args["category"], args["name"]);
    }
    if (operation == 2) { instance()->loaded_files_.insert(storage_text(args["key"]), storage_paths(args["paths"])); return val::undefined(); }
    if (operation == 3) {
        const auto written = storage_paths(args["paths"]); QStringList obsolete;
        for (const QString& path : instance()->loaded_files_.value(storage_text(args["key"]))) if (!written.contains(path)) obsolete.append(path);
        return storage_array(obsolete);
    }
    if (operation == 4) {
        const auto kept = storage_paths(args["paths"]); const val entries = args["entries"]; val removed = val::array(); unsigned next = 0;
        std::uint32_t remaining = entries["length"].as<std::uint32_t>();
        while (remaining > 0) {
            const val entry = entries[--remaining]; const QString path = storage_text(entry[0]); bool used = false;
            if (entry[1].strictlyEquals(val("directory"))) { const auto prefix = path + QStringLiteral("/"); used = std::any_of(kept.begin(), kept.end(), [&](const QString& file) { return file.startsWith(prefix); }); }
            else used = kept.contains(path);
            if (!used) removed.set(next++, entry[0]);
        } return removed;
    }
    if (operation == 5) {
        val record = args["record"];
        if (!record) { record = val::object(); record.set("key", args["key"]); record.set("kind", args["kind"]); record.set("name", args["name"]); record.set("saved", false); }
        record.set("kind", args["kind"]); record.set("name", args["name"]);
        if (!(!args["handle"])) record.set("handle", args["handle"]);
        if (!(!args["recovery"])) { record.set("recovery", true); record.set("recoveryTime", val::global("Date").call<val>("now")); }
        else { record.set("saved", true); record.set("time", val::global("Date").call<val>("now")); }
        return record;
    }
    if (operation == 6) {
        const val record = args["record"];
        if (!record) val::global("Error").new_(val("this browser no longer keeps that project")).throw_();
        return val(!(!args["recovery"]) || record["kind"].strictlyEquals(val("browser")));
    }
    if (operation == 7) { val out = val::array(); out.set(0, "edi"); out.set(1, !(!args["recovery"]) ? "recovery" : "projects"); out.set(2, args["key"]); return out; }
    if (operation == 8) return storage_path(args["root"], args["name"]);
    if (operation == 9) {
        val record = args["record"]; if (!record) return val("none");
        if (!(!args["whole"]) || !record["saved"]) return val("remove");
        record.set("recovery", false); return val("put");
    }
    if (operation == 10) { val out = val::array(); out.set(0, "recovery"); if (!(!args["whole"])) out.set(1, "projects"); return out; }
    if (operation == 11) {
        const val record = args["record"]; val place = val::object();
        place.set("key", record["key"]); place.set("kind", record["kind"]); place.set("name", record["name"]); place.set("saved", !(!record["saved"]));
        const val time = record["time"]; place.set("time", !time ? val(0) : time); place.set("recovery", !(!record["recovery"]));
        const val recovery = record["recoveryTime"]; place.set("recoveryTime", !recovery ? val(0) : recovery); return place;
    }
    if (operation == 12) {
        val record = val::object(); record.set("key", args["key"]); record.set("kind", args["kind"]); record.set("name", args["name"]); record.set("handle", args["handle"]); record.set("saved", true); record.set("time", val::global("Date").call<val>("now")); return record;
    }
    if (operation == 13) return storage_array({QStringLiteral("analysis/analysis.edi")});
    if (operation == 14) return storage_array({QStringLiteral("structures"), QStringLiteral("experiments")});
    if (operation == 15) {
        if (!(!args["recovery"]) || args["kind"].strictlyEquals(val("browser"))) return val("browser");
        return val(args["kind"].strictlyEquals(val("folder")) ? "folder" : "zip");
    }
    if (operation == 16) return val(args["record"]["kind"].strictlyEquals(val("folder")));
    if (operation == 17) return storage_result(args, false);
    if (operation == 18) return storage_result(args, true);
    if (operation == 20) {
        val record = args["record"];
        if (!record || !record["recovery"]) return val(false);
        for (const val& part : args["removed"]) if (part.strictlyEquals(val("recovery"))) { record.set("recovery", false); return val(true); }
        return val(false);
    }
    return val::undefined();
}

void WebStorage::queueSerial(int job, const QString& key) {
    const auto encoded = key.toUtf8(); const auto transportKey = QString::fromUtf8(encoded.constData());
    auto& queue = serial_jobs_[transportKey]; const bool first = queue.isEmpty(); queue.append(job); if (first) edi_storage_resume(job);
}
void WebStorage::serialFinished(int job) {
    const QPointer<WebStorage> storage = the_instance(); if (storage.isNull()) return;
    for (auto it = storage->serial_jobs_.begin(); it != storage->serial_jobs_.end(); ++it) {
        if (it->isEmpty() || it->front() != job) continue;
        it->removeFirst(); if (it->isEmpty()) storage->serial_jobs_.erase(it); else edi_storage_resume(it->front()); return;
    }
}
#endif

WebStorage::WebStorage(QObject* parent) : QObject(parent), places_(new WebPlaceListModel(this)) {
#if defined(Q_OS_WASM)
    edi_storage_install();
    edi_storage_probe(begin([this](const WebStorageAnswer& answer) {
        if (answer.ok) {
            usable_ = true;
            emit usableChanged();
        }
    }));
#endif
    refresh();
}

void WebStorage::markUnusable() {
    if (usable_) {
        usable_ = false;
        emit usableChanged();
    }
}

WebStorage* WebStorage::instance() {
    if (the_instance().isNull()) {
        the_instance() = new WebStorage(QCoreApplication::instance());
    }
    return the_instance().data();
}

WebStorage* WebStorage::create(QQmlEngine*, QJSEngine*) {
    WebStorage* storage = instance();
    QQmlEngine::setObjectOwnership(storage, QQmlEngine::CppOwnership);
    return storage;
}

bool WebStorage::diskAccess() {
#if defined(Q_OS_WASM)
    return edi_storage_install() != 0;
#else
    return false;
#endif
}

int WebStorage::begin(Reply reply) {
    jobs_.insert(++last_, std::move(reply));
    return last_;
}

int WebStorage::begin(Answer answer) {
    return begin(Reply([answer = std::move(answer)](const QString& json) { answer(answer_of(json)); }));
}

void WebStorage::finish(int job, const QString& json) {
    const Reply done = jobs_.take(job);
    if (done) {
        done(json);
    }
}

void WebStorage::answered(int job, const QString& json) {
    const QPointer<WebStorage> storage = the_instance();
    if (storage.isNull()) {
        return;
    }
    // Answered on the app's own turn, never inside the browser's promise.
    QMetaObject::invokeMethod(
        storage.data(), [storage, job, json] {
            if (!storage.isNull()) {
                storage->finish(job, json);
            }
        },
        Qt::QueuedConnection);
}

void WebStorage::refresh() {
#if defined(Q_OS_WASM)
    const int job = begin(Reply([this](const QString& json) {
        const QJsonObject answer = object_of(json);
        if (!answer.value(QStringLiteral("ok")).toBool()) {
            return;
        }
        QList<QJsonObject> records;
        for (const QJsonValue& record : answer.value(QStringLiteral("places")).toArray()) {
            records.append(record.toObject());
        }
        const auto latest = [](const QJsonObject& place) {
            return std::max(place.value(QStringLiteral("time")).toDouble(), place.value(QStringLiteral("recoveryTime")).toDouble());
        };
        std::sort(records.begin(), records.end(), [&latest](const QJsonObject& a, const QJsonObject& b) { return latest(a) > latest(b); });
        QList<WebPlaceListModel::Place> places;
        for (const QJsonObject& place : records) {
            places.append({place.value(QStringLiteral("key")).toString(), place.value(QStringLiteral("kind")).toString(),
                           place.value(QStringLiteral("name")).toString(), place.value(QStringLiteral("saved")).toBool(),
                           place.value(QStringLiteral("recovery")).toBool()});
        }
        places_->setPlaces(std::move(places));
        emit placesChanged();
    }));
    edi_storage_list(job);
#endif
}

void WebStorage::pickOpen(const QString& kind, const QString& root, Answer answer) {
#if defined(Q_OS_WASM)
    edi_storage_pick_open(begin(std::move(answer)), kind.toUtf8().constData(), root.toUtf8().constData());
#else
    Q_UNUSED(kind);
    Q_UNUSED(root);
    answer(refused(QStringLiteral("opening through the browser is the browser build's")));
#endif
}

void WebStorage::pickSave(const QString& kind, const QString& suggested, const QString& startKey, Answer answer) {
#if defined(Q_OS_WASM)
    edi_storage_pick_save(begin(std::move(answer)), kind.toUtf8().constData(), suggested.toUtf8().constData(),
                          startKey.toUtf8().constData());
#else
    Q_UNUSED(kind);
    Q_UNUSED(suggested);
    Q_UNUSED(startKey);
    answer(refused(QStringLiteral("saving through the browser is the browser build's")));
#endif
}

void WebStorage::write(const QString& key, const QString& kind, const QString& name, const QString& folder,
                       bool recovery, Answer answer) {
#if defined(Q_OS_WASM)
    const int job = begin(Reply([this, answer = std::move(answer)](const QString& json) {
        refresh();
        answer(answer_of(json));
    }));
    if (kind == QStringLiteral("zip") && !recovery) {
        try {
            const std::string bytes = edi::project_archive_bytes(folder.toStdString());
            edi_storage_stage(job, "", bytes.data(), static_cast<int>(bytes.size()));
        } catch (const std::exception& error) {
            finish(job, refusal(QString::fromUtf8(error.what())));
            return;
        }
    } else {
        const QDir root(folder);
        QDirIterator files(folder, QDir::Files, QDirIterator::Subdirectories);
        while (files.hasNext()) {
            const QString path = files.next();
            QFile file(path);
            if (!file.open(QIODevice::ReadOnly)) {
                finish(job, refusal(QStringLiteral("cannot read %1").arg(root.relativeFilePath(path))));
                return;
            }
            const QByteArray data = file.readAll();
            edi_storage_stage(job, root.relativeFilePath(path).toUtf8().constData(), data.constData(),
                              static_cast<int>(data.size()));
        }
    }
    edi_storage_write(job, key.toUtf8().constData(), kind.toUtf8().constData(), name.toUtf8().constData(),
                      recovery ? 1 : 0);
    queueSerial(job, key);
#else
    Q_UNUSED(key);
    Q_UNUSED(kind);
    Q_UNUSED(name);
    Q_UNUSED(folder);
    Q_UNUSED(recovery);
    answer(refused(QStringLiteral("the browser's storage is the browser build's")));
#endif
}

void WebStorage::load(const QString& key, bool recovery, const QString& root, Answer answer) {
#if defined(Q_OS_WASM)
    edi_storage_load(begin(std::move(answer)), key.toUtf8().constData(), recovery ? 1 : 0, root.toUtf8().constData());
#else
    Q_UNUSED(key);
    Q_UNUSED(recovery);
    Q_UNUSED(root);
    answer(refused(QStringLiteral("the browser's storage is the browser build's")));
#endif
}

void WebStorage::dropRecovery(const QString& key) {
#if defined(Q_OS_WASM)
    const int job = begin(Reply([this](const QString&) { refresh(); }));
    edi_storage_drop(job, key.toUtf8().constData(), 0);
    queueSerial(job, key);
#else
    Q_UNUSED(key);
#endif
}

void WebStorage::forget(const QString& key) {
#if defined(Q_OS_WASM)
    const int job = begin(Reply([this](const QString&) { refresh(); }));
    edi_storage_drop(job, key.toUtf8().constData(), 1);
    queueSerial(job, key);
#else
    Q_UNUSED(key);
#endif
}

}  // namespace edi_app
