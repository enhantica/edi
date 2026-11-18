.pragma library
// SPDX-License-Identifier: BSD-3-Clause
// When the "Enjoying EasyDiffraction?" bar and the survey invitation bar may appear (ADR-0063; owner, 2026-11-17). The
// clock is passed in, so the rules are the same in the app and in tests: times are UTC milliseconds since the epoch.

var minSessions = 3;
var minDays = 7;
var monthsBetween = 3;
var day = 24 * 60 * 60 * 1000;
// The survey invitation: first after 5 sessions over 14 days, again 30 days and 2 sessions after Not now or the close
// cross, once the app has been idle a minute after useful work.
var surveyMinSessions = 5;
var surveyMinDays = 14;
var surveyAgainDays = 30;
var surveyAgainSessions = 2;
var surveyIdle = 60 * 1000;
// Never both bars in one session, and at least 7 days between them.
var daysBetweenBars = 7;

// The earliest time a prompt may follow one shown at `shown`: the same day of the month three months later.
function nextPromptTime(shown) {
    var next = new Date(shown);
    next.setUTCMonth(next.getUTCMonth() + monthsBetween);
    return next.getTime();
}

// Whether the other bar leaves room for one now: neither bar shown in this session (`barShown`), and the other bar
// last shown (`otherShown`, nullable) at least 7 days ago.
function apartFromOther(state, now) {
    if (state.barShown)
        return false;
    var other = state.otherShown;
    return other === null || other === undefined || !(other > 0) || now - other >= daysBetweenBars * day;
}

// `state`: `sessions` started so far, `firstSession` and the nullable `lastPrompt` times, whether a fit just
// `fitSucceeded`, whether a fit is `fitting` or a `tutorial` runs, whether the user turned it off (`disabled`), and
// the two bars' shared rule (apartFromOther: `barShown`, `otherShown`, the survey bar's last showing). True only
// after a successful fit, at least 3 sessions over at least 7 days, at most every 3 months, never during a fit or a
// tutorial.
function eligible(state, now) {
    if (!state || state.disabled || state.fitting || state.tutorial || !state.fitSucceeded)
        return false;
    if (!apartFromOther(state, now))
        return false;
    if (!(state.sessions >= minSessions) || typeof state.firstSession !== "number")
        return false;
    if (now - state.firstSession < minDays * day)
        return false;
    if (state.lastPrompt !== null && state.lastPrompt !== undefined && now < nextPromptTime(state.lastPrompt))
        return false;
    return true;
}

// `state`: `sessions`, `firstSession`; `disabled` (the preference off), `stopped` (Take the survey or Don't ask
// again chosen); `lastShown` and `sessionsAtShown`, when the invitation last showed and the session count then
// (nullable); `usefulWork` (a project loaded or a fit finished in this session) and `idle`, milliseconds since the
// user last did anything; `fitting`, `tutorial`; `likesDue`, whether the likes bar is showing or about to (it goes
// first: a real successful fit's prompt, never one a fit might earn later); and
// apartFromOther's `barShown` and `otherShown` (the likes bar's last showing).
function surveyEligible(state, now) {
    if (!state || state.disabled || state.stopped || state.fitting || state.tutorial || state.likesDue)
        return false;
    if (!state.usefulWork || !(state.idle >= surveyIdle) || !apartFromOther(state, now))
        return false;
    if (!(state.sessions >= surveyMinSessions) || typeof state.firstSession !== "number")
        return false;
    if (now - state.firstSession < surveyMinDays * day)
        return false;
    if (state.lastShown !== null && state.lastShown !== undefined && state.lastShown > 0) {
        if (now - state.lastShown < surveyAgainDays * day)
            return false;
        if (!(state.sessions - (state.sessionsAtShown || 0) >= surveyAgainSessions))
            return false;
    }
    return true;
}
