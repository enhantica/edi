.pragma library
// SPDX-License-Identifier: BSD-3-Clause
// What Help and feedback sends, and how (ADR-0063). The form shows exactly what buildPayload returns, and
// submit sends that object unchanged.

var kinds = ["feedback", "question", "problem", "idea"];
// The feedback service keeps at most this much of a log; the app sends the header and the end of a longer one.
var maxLogCharacters = 40000;
var maxTextCharacters = 20000;
// Attached files (ADR-0063): at most this many, of any type, each and all together at most this size in bytes. The
// service shows screenshots and videos in the issue and puts every other file into one zip linked from it.
var maxFiles = 5;
var maxFileBytes = 5 * 1024 * 1024;
var maxTotalBytes = 10 * 1024 * 1024;
var mediaTypes = ["image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml", "video/mp4", "video/quicktime",
                  "video/webm"];
var textSuffixes = ["cif", "mcif", "edi", "txt", "log", "dat", "xye", "xy", "xys", "csv", "tsv", "json", "gss", "gsa",
                    "fxye", "prm", "instprm", "pcr", "hkl", "int", "out", "yml", "yaml", "md"];

function escapeRegExp(text) {
    return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// One character of a private value in every way text may carry it: as written (in any case), as a JSON \\u escape,
// percent-encoded once or twice (a URL, a form, a link that encodes a URL again), a space also as a form's +, and a
// path's separator as either slash, a doubled backslash or JSON's escaped slash. Matching character by character finds
// a value however its characters are mixed, as in a JSON writer that escapes only the non-ASCII ones.
function characterForms(character, isPath) {
    var forms;
    if (isPath && (character === "/" || character === "\\")) {
        forms = ["/", "\\", "\\\\", "\\/", "%2F", "%5C", "%252F", "%255C", "\\u002F", "\\u005C"];
    } else {
        // The escapes of either case: the pattern's own case folding does not reach inside them.
        forms = [];
        [character, character.toLowerCase(), character.toUpperCase()].forEach(function (variant) {
            var encoded = encodeURIComponent(variant);
            if (encoded === variant)
                encoded = "%" + ("0" + variant.charCodeAt(0).toString(16)).slice(-2);
            forms.push(variant, unicodeEscaped(variant), encoded, encoded.replace(/%/g, "%25"));
        });
        if (character === " ")
            forms.push("+");
        forms = forms.filter(function (form, index) {
            return forms.indexOf(form) === index;
        });
    }
    // Each form also inside one or two more layers, as text copied between JSON and URLs carries it: a JSON layer
    // doubles a backslash or writes a percent sign as \u0025, a URL layer percent-encodes a backslash or a percent sign
    // (\u00e9 becomes \\u00e9, %5Cu00e9 or %255Cu00e9; %C3 becomes \u0025C3).
    forms = layered(forms, 2);
    // The longest first, so a shorter form never matches part of a longer one.
    forms.sort(function (a, b) {
        return b.length - a.length;
    });
    return "(?:" + forms.map(escapeRegExp).join("|") + ")";
}

function layered(forms, depth) {
    var all = forms.slice();
    var current = forms;
    for (var level = 0; level < depth; ++level) {
        var next = [];
        current.forEach(function (form) {
            next.push(form.replace(/\\/g, "\\\\"), form.replace(/%/g, "\\u0025"), form.replace(/%/g, "%25").replace(/\\/g, "%5C"));
        });
        next.forEach(function (form) {
            if (all.indexOf(form) < 0)
                all.push(form);
        });
        current = next;
    }
    return all;
}
function valuePattern(value, isPath) {
    return new RegExp(Array.from(value).map(function (character) {
        return characterForms(character, isPath);
    }).join(""), "gi");
}

function unicodeEscaped(text) {
    var escaped = "";
    for (var i = 0; i < text.length; ++i)
        escaped += "\\u" + ("000" + text.charCodeAt(i).toString(16)).slice(-4);
    return escaped;
}

// The character an escape at the end (or start) of `text` stands for, else its last (or first) character.
function lastCharacter(text) {
    var escape = /(?:%|\\u0025)(?:25)*([0-9A-Fa-f]{2})$/i.exec(text) || /(?:\\|%(?:25)*5C)+u([0-9A-Fa-f]{4})$/i.exec(text);
    return escape ? String.fromCharCode(parseInt(escape[1], 16)) : text.slice(-1);
}

function firstCharacter(text) {
    var escape = /^(?:%|\\u0025)(?:25)*([0-9A-Fa-f]{2})/i.exec(text) || /^(?:\\|%(?:25)*5C)+u([0-9A-Fa-f]{4})/i.exec(text);
    return escape ? String.fromCharCode(parseInt(escape[1], 16)) : text.charAt(0);
}

// The home folder and the user name, wherever they appear and however they are written, become "~". Both are matched
// in any case; the user name only as a whole word, so ordinary words that contain it are kept. A neighbouring escape
// counts as the character it stands for: the F of %2F is a slash, not a letter.
function redact(value, home, user) {
    if (typeof value !== "string" || value === "")
        return value;
    var result = value;
    var trimmed = home ? home.replace(/[\/\\]+$/, "") : "";
    if (trimmed !== "") {
        // A home folder starting at the root keeps a file URL's own root slash: file:///home/name becomes file:///~.
        result = result.replace(valuePattern(trimmed, true), function (match, offset, whole) {
            var fileUrl = match.charAt(0) === "/" && whole.slice(Math.max(0, offset - 7), offset).toLowerCase() === "file://";
            return fileUrl ? "/~" : "~";
        });
    }
    if (user) {
        var letter = /[A-Za-z0-9]/;
        result = result.replace(valuePattern(user, false), function (match, offset, whole) {
            var inWord = letter.test(lastCharacter(whole.slice(0, offset)))
                    || letter.test(firstCharacter(whole.slice(offset + match.length)));
            return inWord ? match : "~";
        });
    }
    return result;
}

function redactAll(value, home, user) {
    if (typeof value === "string")
        return redact(value, home, user);
    if (Array.isArray(value))
        return value.map(function (item) { return redactAll(item, home, user); });
    if (value !== null && typeof value === "object") {
        var copy = {};
        for (var key in value)
            copy[key] = redactAll(value[key], home, user);
        return copy;
    }
    return value;
}

// The most of a log the attached full copy carries (log.txt in the service's zip), as for any one attached file.
var maxFullLogCharacters = 5 * 1024 * 1024;

// The header lines of a run log and as much of its end as fits in `limit` characters (the body's preview by default).
function shortenLog(log, limit) {
    var most = limit === undefined ? maxLogCharacters : limit;
    if (log.length <= most)
        return log;
    var lines = log.split("\n");
    var header = [];
    while (header.length < lines.length && lines[header.length].charAt(0) === "#")
        header.push(lines[header.length]);
    var head = header.join("\n") + "\n…\n";
    var tail = log.slice(log.length - Math.max(0, most - head.length));
    var firstBreak = tail.indexOf("\n");
    return head + (firstBreak >= 0 ? tail.slice(firstBreak + 1) : tail);
}

var base64Alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

// Base64 to bytes and back, in plain JavaScript: the form's engine has no atob or btoa outside Qt.
function base64Bytes(text) {
    var clean = String(text).replace(/[\s=]+/g, "");
    if (/[^A-Za-z0-9+\/]/.test(clean) || clean.length % 4 === 1)
        throw new Error("an attached file is not valid base64");
    var bytes = [];
    for (var i = 0; i < clean.length; i += 4) {
        var group = 0, count = 0;
        for (var j = 0; j < 4; ++j) {
            group <<= 6;
            if (i + j < clean.length) {
                group |= base64Alphabet.indexOf(clean.charAt(i + j));
                ++count;
            }
        }
        bytes.push((group >> 16) & 255);
        if (count > 2)
            bytes.push((group >> 8) & 255);
        if (count > 3)
            bytes.push(group & 255);
    }
    return bytes;
}

function bytesBase64(bytes) {
    var text = "";
    for (var i = 0; i < bytes.length; i += 3) {
        var group = (bytes[i] << 16) | ((bytes[i + 1] || 0) << 8) | (bytes[i + 2] || 0);
        text += base64Alphabet.charAt((group >> 18) & 63) + base64Alphabet.charAt((group >> 12) & 63);
        text += i + 1 < bytes.length ? base64Alphabet.charAt((group >> 6) & 63) : "=";
        text += i + 2 < bytes.length ? base64Alphabet.charAt(group & 63) : "=";
    }
    return text;
}

// UTF-8 bytes to text and back; an invalid sequence becomes U+FFFD, as a text editor shows it.
function utf8Text(bytes) {
    var text = "";
    for (var i = 0; i < bytes.length;) {
        var lead = bytes[i], code = -1, extra = 0;
        if (lead < 0x80) { code = lead; }
        else if (lead >= 0xc2 && lead < 0xe0) { code = lead & 0x1f; extra = 1; }
        else if (lead >= 0xe0 && lead < 0xf0) { code = lead & 0x0f; extra = 2; }
        else if (lead >= 0xf0 && lead < 0xf5) { code = lead & 0x07; extra = 3; }
        var j = 1;
        for (; code >= 0 && j <= extra; ++j) {
            var next = bytes[i + j];
            if (next === undefined || (next & 0xc0) !== 0x80) { code = -1; break; }
            code = (code << 6) | (next & 0x3f);
        }
        // Overlong forms, surrogates and values past U+10FFFF are not Unicode scalar values.
        var least = [0, 0x80, 0x800, 0x10000][extra];
        if (code < least || code > 0x10ffff || (code >= 0xd800 && code <= 0xdfff))
            code = -1;
        if (code < 0) { text += "\ufffd"; i += 1; continue; }
        text += String.fromCodePoint(code);
        i += extra + 1;
    }
    return text;
}

function textUtf8(text) {
    var bytes = [];
    for (var index = 0; index < text.length; ++index) {
        var code = text.codePointAt(index);
        if (code > 0xffff)
            ++index;
        if (code < 0x80) bytes.push(code);
        else if (code < 0x800) bytes.push(0xc0 | (code >> 6), 0x80 | (code & 63));
        else if (code < 0x10000) bytes.push(0xe0 | (code >> 12), 0x80 | ((code >> 6) & 63), 0x80 | (code & 63));
        else bytes.push(0xf0 | (code >> 18), 0x80 | ((code >> 12) & 63), 0x80 | ((code >> 6) & 63), 0x80 | (code & 63));
    }
    return bytes;
}

function fileSuffix(name) {
    var dot = name.lastIndexOf(".");
    return dot < 0 ? "" : name.slice(dot + 1).toLowerCase();
}

// Whether a file goes into the issue as text (scrubbed like the log) rather than as a screenshot or video.
function isTextFile(file) {
    return /^text\//.test(file.type || "") || textSuffixes.indexOf(fileSuffix(file.name)) >= 0;
}

// Why these files cannot be attached, naming the limit, or "" when they can. `bytes` is each file's decoded size.
function attachmentProblem(files, bytes) {
    if (files.length > maxFiles)
        return "at most " + maxFiles + " files can be attached";
    var total = 0;
    for (var i = 0; i < files.length; ++i) {
        if (bytes[i] > maxFileBytes)
            return files[i].name + " is larger than the 5 MB limit for one file";
        total += bytes[i];
    }
    if (total > maxTotalBytes)
        return "the attached files are larger than the 10 MB limit in total";
    return "";
}

// Why `files` (as the form holds them, each with its `size`) cannot be sent, naming the limit, or "".
function filesProblem(files) {
    if (!Array.isArray(files) || files.length === 0)
        return "";
    return attachmentProblem(files, files.map(function (file) { return Number(file.size) || 0; }));
}

// The files as the feedback service receives them: each `name` (as given), `type`, decoded `size` and base64 `data`,
// a text file's content with the home folder and user name replaced as in the log. A file past a limit refuses all.
function attachmentsFor(files, home, user) {
    if (!Array.isArray(files))
        throw new Error("attached files must be a list");
    var decoded = files.map(function (file) {
        if (file === null || typeof file !== "object" || typeof file.name !== "string" || file.name === "")
            throw new Error("an attached file has no name");
        return base64Bytes(file.data || "");
    });
    // The size the form read from the disk counts as well as the data's own, so neither can hide a large file.
    var sizes = decoded.map(function (bytes, index) {
        var declared = Number(files[index].size);
        return isFinite(declared) && declared > bytes.length ? declared : bytes.length;
    });
    var problem = attachmentProblem(files, sizes);
    if (problem !== "")
        throw new Error(problem);
    return files.map(function (file, index) {
        var bytes = decoded[index];
        if (isTextFile(file))
            bytes = textUtf8(redact(utf8Text(bytes), home, user));
        return {
            "name": file.name,
            "type": file.type || (isTextFile(file) ? "text/plain" : "application/octet-stream"),
            "size": bytes.length,
            "data": bytesBase64(bytes)
        };
    });
}

// The message for the feedback service: `kind` and `text`; `subject`, trimmed, left out when empty; `contact`, the
// name, e-mail and affiliation the user filled in, trimmed, the empty ones left out and the whole left out when none is
// filled; and with `include` the app's details (`app`, an object) and the run log (`log`, text). The subject, the text,
// the details and the log have the home folder and user name replaced; the kind is one of the fixed values and is
// never rewritten, and the contact is sent as written. `files`, when given, become `attachments` (attachmentsFor).
function buildPayload(kind, text, include, app, log, home, user, contact, subject, files) {
    if (kinds.indexOf(kind) < 0)
        throw new Error("unknown feedback kind: " + kind);
    var written = String(text === undefined || text === null ? "" : text);
    var payload = {
        "kind": kind,
        "text": redact(written, home, user).slice(0, maxTextCharacters)
    };
    var title = typeof subject === "string" ? subject.trim() : "";
    if (title !== "")
        payload.subject = redact(title, home, user);
    var given = {};
    ["name", "email", "affiliation"].forEach(function (key) {
        var value = contact && typeof contact[key] === "string" ? contact[key].trim() : "";
        if (value !== "")
            given[key] = value;
    });
    if (Object.keys(given).length > 0)
        payload.contact = given;
    if (include) {
        if (app !== undefined && app !== null)
            payload.app = redactAll(app, home, user);
        if (typeof log === "string" && log !== "") {
            var scrubbed = redact(log, home, user);
            payload.log = shortenLog(scrubbed);
            // The whole log, for the service to attach as a file, when the body's preview is cut.
            if (payload.log !== scrubbed)
                payload.fullLog = shortenLog(scrubbed, maxFullLogCharacters);
        }
    }
    if (files !== undefined && files !== null && files.length > 0)
        payload.attachments = attachmentsFor(files, home, user);
    return payload;
}

// The likes prompt's answer (LikesBar.qml): `kind` "likes", the `answer` ("yes", "no" or "unsure"), when given what
// works well as `text`, and the app's details as Help and feedback sends them (`app`: version, commit, system); the
// home folder and user name replaced. Never the log or contact details. The service labels it `likes`.
function likesPayload(answer, text, home, user, app) {
    if (["yes", "no", "unsure"].indexOf(answer) < 0)
        throw new Error("unknown likes answer: " + answer);
    var payload = {"kind": "likes", "answer": answer};
    if (app !== undefined && app !== null)
        payload.app = redactAll(app, home, user);
    var written = typeof text === "string" ? text.trim() : "";
    if (written !== "")
        payload.text = redact(written, home, user).slice(0, maxTextCharacters);
    return payload;
}

// The files a 201 answer does not confirm: all of `names` when the answer lists no `attached` (a service that drops
// files), else those it leaves out.
function unconfirmedFiles(names, answerText) {
    if (!names || names.length === 0)
        return [];
    var attached = null;
    try {
        attached = JSON.parse(answerText || "{}").attached;
    } catch (error) {
        attached = null;
    }
    if (!Array.isArray(attached))
        return names.slice();
    return names.filter(function (name) { return attached.indexOf(name) < 0; });
}

// Whether a 201 answer says the whole log sent beside the preview did not arrive (`logAttached` false).
function logUnconfirmed(answerText) {
    try {
        return JSON.parse(answerText || "{}").logAttached === false;
    } catch (error) {
        return false;
    }
}

// The message as plain text, for Copy report after a failed send: the type, subject, message, contact, the app's
// details and the log, as "Show what will be sent" shows them, with attached files listed by name.
function reportText(payload) {
    var lines = ["Type: " + payload.kind];
    if (payload.subject)
        lines.push("Subject: " + payload.subject);
    lines.push("", payload.text || "");
    if (payload.contact) {
        lines.push("", "Contact:");
        ["name", "email", "affiliation"].forEach(function (key) {
            if (payload.contact[key])
                lines.push("- " + key + ": " + payload.contact[key]);
        });
    }
    if (payload.app) {
        lines.push("", "App:");
        for (var key in payload.app)
            lines.push("- " + key + ": " + payload.app[key]);
    }
    if (payload.attachments && payload.attachments.length > 0) {
        lines.push("", "Attached files:");
        payload.attachments.forEach(function (file) {
            lines.push("- " + file.name);
        });
    }
    if (payload.log)
        lines.push("", "Log:", payload.log);
    return lines.join("\n") + "\n";
}

// The message as the feedback service receives it; `readable` indents it for the form's preview, where the full log
// copy is named by its length rather than shown a second time.
function wireText(payload, readable) {
    if (!readable)
        return JSON.stringify(payload);
    var shown = payload;
    if (typeof payload.fullLog === "string") {
        shown = Object.assign({}, payload);
        shown.fullLog = "(the whole log, " + payload.fullLog.length + " characters, attached as log.txt)";
    }
    return JSON.stringify(shown, null, 2);
}

// Posts `payload` to `endpoint` through `transport(url, payload, completed)`; `completed` receives the HTTP status (0
// when no answer came) and, when known, what happened (the service's error or the network's reason). Without an
// endpoint nothing is sent and false is returned.
function submit(endpoint, payload, transport, completed) {
    if (!endpoint)
        return false;
    transport(endpoint, payload, completed);
    return true;
}

// The service's own reason in an answer `{"error": ...}`, or "".
function answerError(text) {
    try {
        var answer = JSON.parse(text);
        var said = answer && (answer.error || answer.warning);
        return typeof said === "string" ? said : "";
    } catch (error) {
        return "";
    }
}

// The browser's transport: JSON over HTTPS (the desktop posts through ApplicationInfo.postFeedback, which also knows
// the network's reason). A request that never reaches the feedback service completes with status 0.
function httpTransport(url, payload, completed) {
    var request = new XMLHttpRequest();
    request.onreadystatechange = function () {
        if (request.readyState === XMLHttpRequest.DONE)
            completed(request.status, answerError(request.responseText), request.responseText);
    };
    request.open("POST", url);
    request.setRequestHeader("Content-Type", "application/json");
    request.send(wireText(payload, false));
}
