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
#include <QPointer>
#include <QQmlEngine>
#include <algorithm>
#include <cstdlib>

#if defined(Q_OS_WASM)
#include <emscripten.h>

// The page's side of the storage (edi ADR-0052 §9), installed once as globalThis.ediStorage. A job's files are staged
// from the app's memory first (stage), then one call starts the job; its answer goes back through
// Module._edi_storage_answered(job, json). The browser's own storage is written from a small worker, whose
// synchronous file handles every current browser has; the disk is written through the File System Access API.
// Records: IndexedDB "edi-projects", store "places", one per place by its key. Files: the origin private file system
// under edi/projects/<key> and edi/recovery/<key>.
EM_JS_DEPS(edi_web_storage, "$FS,$stringToNewUTF8,$UTF8ToString");

EM_JS(int, edi_storage_install, (), {
    if (globalThis.ediStorage) {
        return globalThis.ediStorage.disk ? 1 : 0;
    }
    const S = {handles : new Map(), loaded : new Map(), staged : new Map(), workerJobs : new Map(), next : 1};
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
    S.key = () => Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);

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
    S.removePath = async (folder, path) => {
        const names = path.split("/");
        let at = folder;
        try {
            for (const name of names.slice(0, -1)) {
                at = await at.getDirectoryHandle(name);
            }
            await at.removeEntry(names[names.length - 1]);
        } catch (error) {
            // Already gone.
        }
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
        S.loaded.set(key, new Set(await S.copyIn(handle, root + "/" + handle.name)));
        await S.put({key : key, kind : "folder", name : handle.name, handle : handle, saved : true, time : Date.now()});
        return {ok : true, key : key, kind : "folder", name : handle.name, path : root + "/" + handle.name};
    };
    // The folder of the project.edi picked last: the folder picker starts there, and the folder must hold that file.
    S.openRecordFolder = async root => {
        const record = S.pendingRecord;
        const folder = await showDirectoryPicker({id : "edi-project", mode : "readwrite", startIn : record});
        let same = false;
        try {
            same = await (await folder.getFileHandle(record.name)).isSameEntry(record);
        } catch (error) {
            same = false;
        }
        if (!same) {
            throw new Error("the chosen folder does not hold the " + record.name + " that was opened");
        }
        S.pendingRecord = null;
        return await S.openFolder(folder, root);
    };

    // The browser storage writer: a dedicated worker with synchronous access handles, which Firefox and Safari offer
    // where they offer no writable streams. It writes every file of a job, then removes what the folder has besides.
    const writerMain = () => {
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
            const {id, parts, files} = event.data;
            try {
                let folder = await navigator.storage.getDirectory();
                for (const part of parts) {
                    folder = await folder.getDirectoryHandle(part, {create : true});
                }
                const kept = new Set();
                for (const [path, data] of files) {
                    kept.add(path);
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
                for (const [path, kind] of entries.reverse()) {
                    const used = kind === "directory" ? [...kept].some(file => file.startsWith(path + "/")) : kept.has(path);
                    if (!used) {
                        const names = path.split("/");
                        let at = folder;
                        for (const name of names.slice(0, -1)) {
                            at = await at.getDirectoryHandle(name);
                        }
                        await at.removeEntry(names[names.length - 1], {recursive : true});
                    }
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
        // A project file: its project.edi or its .zip, as the desktop Open takes them.
        const [handle] = await showOpenFilePicker({
            id : "edi-project",
            types : [ {description : "edi project (project.edi or .zip)", accept : {"application/zip" : [".zip"], "application/octet-stream" : [".edi"]}} ]
        });
        const file = await handle.getFile();
        if (!file.name.toLowerCase().endsWith(".zip")) {
            // A project.edi opens its folder, which the page may use only once the user picks it too.
            S.pendingRecord = handle;
            try {
                return await S.openRecordFolder(root);
            } catch (error) {
                if (error && (error.name === "SecurityError" || error.name === "NotAllowedError")) {
                    return {ok : false, needsFolder : true, name : file.name};
                }
                throw error;
            }
        }
        const path = root + "/" + file.name;
        FS.mkdirTree(root);
        FS.writeFile(path, new Uint8Array(await file.arrayBuffer()));
        // An archive the user does not let the page write is worked on in the browser.
        if (!(await S.permitted(handle))) {
            return {ok : true, kind : "browser", name : file.name, path : path};
        }
        const key = S.key();
        S.handles.set(key, handle);
        await S.put({key : key, kind : "zip", name : file.name, handle : handle, saved : true, time : Date.now()});
        return {ok : true, key : key, kind : "zip", name : file.name, path : path};
    })().then(value => S.answer(job, value), error => S.fail(job, error));
});

EM_JS(void, edi_storage_pick_record_folder, (int job, const char* root_utf8), {
    const S = globalThis.ediStorage;
    const root = UTF8ToString(root_utf8);
    S.openRecordFolder(root).then(value => S.answer(job, value), error => S.fail(job, error));
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
            S.loaded.set(key, new Set());
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
    (async () => {
        let handle = null;
        if (recovery || kind === "browser") {
            await S.writeBrowser([ "edi", recovery ? "recovery" : "projects", key ], files);
        } else if (kind === "folder") {
            handle = await S.handle(key);
            if (!(await S.permitted(handle))) {
                throw new Error("the browser was not allowed to write to the folder " + handle.name);
            }
            await S.writeTo(handle, files);
            const written = new Set(files.map(file => file[0]));
            for (const path of S.loaded.get(key) || []) {
                if (!written.has(path)) {
                    await S.removePath(handle, path);
                }
            }
            S.loaded.set(key, written);
        } else {
            handle = await S.handle(key);
            if (!(await S.permitted(handle))) {
                throw new Error("the browser was not allowed to write to " + handle.name);
            }
            const writable = await handle.createWritable();
            await writable.write(files.length > 0 ? files[0][1] : new Uint8Array());
            await writable.close();
        }
        const record = (await S.record(key)) || {key : key, kind : kind, name : name, saved : false};
        record.kind = kind;
        record.name = name;
        if (handle) {
            record.handle = handle;
        }
        if (recovery) {
            record.recovery = true;
            record.recoveryTime = Date.now();
        } else {
            record.saved = true;
            record.time = Date.now();
        }
        await S.put(record);
        return {ok : true};
    })().then(value => S.answer(job, value), error => S.fail(job, error));
});

EM_JS(void, edi_storage_load, (int job, const char* key_utf8, int recovery, const char* root_utf8), {
    const S = globalThis.ediStorage;
    const key = UTF8ToString(key_utf8);
    const root = UTF8ToString(root_utf8);
    (async () => {
        const record = await S.record(key);
        if (!record) {
            throw new Error("this browser no longer keeps that project");
        }
        if (recovery || record.kind === "browser") {
            const folder = await S.opfs([ "edi", recovery ? "recovery" : "projects", key ], false);
            await S.copyIn(folder, root + "/" + record.name);
            return {ok : true, key : key, kind : record.kind, name : record.name, path : root + "/" + record.name};
        }
        const handle = await S.handle(key);
        if (!(await S.permitted(handle))) {
            throw new Error("the browser was not allowed to open " + handle.name);
        }
        if (record.kind === "folder") {
            S.loaded.set(key, new Set(await S.copyIn(handle, root + "/" + handle.name)));
            return {ok : true, key : key, kind : "folder", name : handle.name, path : root + "/" + handle.name};
        }
        const file = await handle.getFile();
        FS.mkdirTree(root);
        FS.writeFile(root + "/" + file.name, new Uint8Array(await file.arrayBuffer()));
        return {ok : true, key : key, kind : "zip", name : file.name, path : root + "/" + file.name};
    })().then(value => S.answer(job, value), error => S.fail(job, error));
});

EM_JS(void, edi_storage_list, (int job), {
    const S = globalThis.ediStorage;
    S.store("readonly", store => store.getAll())
        .then(records => {
            const places = records.map(record => ({
                key : record.key,
                kind : record.kind,
                name : record.name,
                saved : !!record.saved,
                time : record.time || 0,
                recovery : !!record.recovery,
                recoveryTime : record.recoveryTime || 0
            }));
            S.answer(job, {ok : true, places : places});
        }, error => S.fail(job, error));
});

EM_JS(void, edi_storage_drop, (int job, const char* key_utf8, int whole), {
    const S = globalThis.ediStorage;
    const key = UTF8ToString(key_utf8);
    (async () => {
        const record = await S.record(key);
        const parts = whole ? [ "recovery", "projects" ] : ["recovery"];
        for (const part of parts) {
            try {
                await (await S.opfs([ "edi", part ], false)).removeEntry(key, {recursive : true});
            } catch (error) {
                // Nothing kept there.
            }
        }
        if (record) {
            if (whole || !record.saved) {
                await S.remove(key);
            } else {
                record.recovery = false;
                await S.put(record);
            }
        }
        S.handles.delete(key);
        return {ok : true};
    })().then(value => S.answer(job, value), error => S.fail(job, error));
});

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

QJsonObject refusal(const QString& message) { return QJsonObject{{QStringLiteral("ok"), false}, {QStringLiteral("message"), message}}; }
}  // namespace

WebStorage::WebStorage(QObject* parent) : QObject(parent) {
#if defined(Q_OS_WASM)
    edi_storage_install();
    edi_storage_probe(begin([this](const QJsonObject& answer) {
        if (answer.value(QStringLiteral("ok")).toBool()) {
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

QVariantMap WebStorage::place(const QString& key) const {
    for (const QVariant& place : places_) {
        const QVariantMap map = place.toMap();
        if (map.value(QStringLiteral("key")).toString() == key) {
            return map;
        }
    }
    return {};
}

int WebStorage::begin(Answer answer) {
    jobs_.insert(++last_, std::move(answer));
    return last_;
}

void WebStorage::finish(int job, const QJsonObject& answer) {
    const Answer done = jobs_.take(job);
    if (done) {
        done(answer);
    }
}

void WebStorage::answered(int job, const QString& json) {
    const QPointer<WebStorage> storage = the_instance();
    if (storage.isNull()) {
        return;
    }
    const QJsonObject answer = QJsonDocument::fromJson(json.toUtf8()).object();
    // Answered on the app's own turn, never inside the browser's promise.
    QMetaObject::invokeMethod(
        storage.data(), [storage, job, answer] {
            if (!storage.isNull()) {
                storage->finish(job, answer);
            }
        },
        Qt::QueuedConnection);
}

void WebStorage::refresh() {
#if defined(Q_OS_WASM)
    const int job = begin([this](const QJsonObject& answer) {
        if (!answer.value(QStringLiteral("ok")).toBool()) {
            return;
        }
        QVariantList places = answer.value(QStringLiteral("places")).toArray().toVariantList();
        const auto latest = [](const QVariant& place) {
            const QVariantMap map = place.toMap();
            return std::max(map.value(QStringLiteral("time")).toDouble(), map.value(QStringLiteral("recoveryTime")).toDouble());
        };
        std::sort(places.begin(), places.end(), [&latest](const QVariant& a, const QVariant& b) { return latest(a) > latest(b); });
        places_ = places;
        emit placesChanged();
    });
    edi_storage_list(job);
#endif
}

void WebStorage::pickOpen(const QString& kind, const QString& root, Answer answer) {
#if defined(Q_OS_WASM)
    edi_storage_pick_open(begin(std::move(answer)), kind.toUtf8().constData(), root.toUtf8().constData());
#else
    Q_UNUSED(kind);
    Q_UNUSED(root);
    answer(refusal(QStringLiteral("opening through the browser is the browser build's")));
#endif
}

void WebStorage::pickRecordFolder(const QString& root, Answer answer) {
#if defined(Q_OS_WASM)
    edi_storage_pick_record_folder(begin(std::move(answer)), root.toUtf8().constData());
#else
    Q_UNUSED(root);
    answer(refusal(QStringLiteral("opening through the browser is the browser build's")));
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
    answer(refusal(QStringLiteral("saving through the browser is the browser build's")));
#endif
}

void WebStorage::write(const QString& key, const QString& kind, const QString& name, const QString& folder,
                       bool recovery, Answer answer) {
#if defined(Q_OS_WASM)
    const int job = begin([this, answer = std::move(answer)](const QJsonObject& result) {
        refresh();
        answer(result);
    });
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
#else
    Q_UNUSED(key);
    Q_UNUSED(kind);
    Q_UNUSED(name);
    Q_UNUSED(folder);
    Q_UNUSED(recovery);
    answer(refusal(QStringLiteral("the browser's storage is the browser build's")));
#endif
}

void WebStorage::load(const QString& key, bool recovery, const QString& root, Answer answer) {
#if defined(Q_OS_WASM)
    edi_storage_load(begin(std::move(answer)), key.toUtf8().constData(), recovery ? 1 : 0, root.toUtf8().constData());
#else
    Q_UNUSED(key);
    Q_UNUSED(recovery);
    Q_UNUSED(root);
    answer(refusal(QStringLiteral("the browser's storage is the browser build's")));
#endif
}

void WebStorage::dropRecovery(const QString& key) {
#if defined(Q_OS_WASM)
    edi_storage_drop(begin([this](const QJsonObject&) { refresh(); }), key.toUtf8().constData(), 0);
#else
    Q_UNUSED(key);
#endif
}

void WebStorage::forget(const QString& key) {
#if defined(Q_OS_WASM)
    edi_storage_drop(begin([this](const QJsonObject&) { refresh(); }), key.toUtf8().constData(), 1);
#else
    Q_UNUSED(key);
#endif
}

}  // namespace edi_app
