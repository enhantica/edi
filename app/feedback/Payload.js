.pragma library
// SPDX-License-Identifier: BSD-3-Clause
// What Help and feedback sends, and how (ADR-0063). The form shows exactly what buildPayload returns, and
// submit sends that object unchanged.

var kinds = ["feedback", "question", "problem", "idea"];
// The feedback service keeps at most this much of a log; the app sends the header and the end of a longer one.
var maxLogCharacters = 40000;
var maxTextCharacters = 20000;

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

// The header lines of a run log and as much of its end as fits.
function shortenLog(log) {
    if (log.length <= maxLogCharacters)
        return log;
    var lines = log.split("\n");
    var header = [];
    while (header.length < lines.length && lines[header.length].charAt(0) === "#")
        header.push(lines[header.length]);
    var head = header.join("\n") + "\n…\n";
    var tail = log.slice(log.length - Math.max(0, maxLogCharacters - head.length));
    var firstBreak = tail.indexOf("\n");
    return head + (firstBreak >= 0 ? tail.slice(firstBreak + 1) : tail);
}

// The message for the feedback service: `kind` and `text`; `subject`, trimmed, left out when empty; `contact`, the
// name, e-mail and affiliation the user filled in, trimmed, the empty ones left out and the whole left out when none is
// filled; and with `include` the app's details (`app`, an object) and the run log (`log`, text). The subject, the text,
// the details and the log have the home folder and user name replaced; the kind is one of the fixed values and is
// never rewritten, and the contact is sent as written.
function buildPayload(kind, text, include, app, log, home, user, contact, subject) {
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
        if (typeof log === "string" && log !== "")
            payload.log = shortenLog(redact(log, home, user));
    }
    return payload;
}

// The message as the feedback service receives it; `readable` indents it for the form's preview.
function wireText(payload, readable) {
    return readable ? JSON.stringify(payload, null, 2) : JSON.stringify(payload);
}

// Posts `payload` to `endpoint` through `transport(url, payload, completed)`; `completed` receives the HTTP status.
// Without an endpoint nothing is sent and false is returned.
function submit(endpoint, payload, transport, completed) {
    if (!endpoint)
        return false;
    transport(endpoint, payload, completed);
    return true;
}

// The real transport: JSON over HTTPS. A request that never reaches the feedback service completes with status 0.
function httpTransport(url, payload, completed) {
    var request = new XMLHttpRequest();
    request.onreadystatechange = function () {
        if (request.readyState === XMLHttpRequest.DONE)
            completed(request.status);
    };
    request.open("POST", url);
    request.setRequestHeader("Content-Type", "application/json");
    request.send(wireText(payload, false));
}
