// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import "../../../app/feedback/Likes.js" as Likes

// The likes bar's and the survey invitation's timing with a given clock (owner, 2026-11-17).
TestCase {
    name: "FeedbackBarRules"

    readonly property real day: 24 * 60 * 60 * 1000
    readonly property real start: Date.UTC(2026, 0, 1)

    function likes(extra) {
        return Object.assign({
            "sessions": 3,
            "firstSession": start,
            "lastPrompt": null,
            "fitSucceeded": true,
            "fitting": false,
            "tutorial": false,
            "disabled": false,
            "barShown": false,
            "otherShown": null
        }, extra);
    }
    function survey(extra) {
        return Object.assign({
            "sessions": 5,
            "firstSession": start,
            "disabled": false,
            "stopped": false,
            "lastShown": null,
            "sessionsAtShown": 0,
            "usefulWork": true,
            "idle": 60000,
            "fitting": false,
            "tutorial": false,
            "likesDue": false,
            "barShown": false,
            "otherShown": null
        }, extra);
    }

    function test_likes_timing_unchanged() {
        verify(Likes.eligible(likes(), start + 7 * day));
        verify(!Likes.eligible(likes(), start + 7 * day - 1), "7 days");
        verify(!Likes.eligible(likes({
            "sessions": 2
        }), start + 30 * day), "3 sessions");
        verify(!Likes.eligible(likes({
            "fitSucceeded": false
        }), start + 30 * day), "after a successful fit");
        verify(!Likes.eligible(likes({
            "lastPrompt": start + 10 * day
        }), Date.UTC(2026, 3, 10)), "3 months from showing");
        verify(Likes.eligible(likes({
            "lastPrompt": start + 10 * day
        }), Date.UTC(2026, 3, 11)));
    }
    function test_survey_first_after_5_sessions_over_14_days() {
        verify(Likes.surveyEligible(survey(), start + 14 * day));
        verify(!Likes.surveyEligible(survey(), start + 14 * day - 1), "14 days");
        verify(!Likes.surveyEligible(survey({
            "sessions": 4
        }), start + 30 * day), "5 sessions");
    }
    function test_survey_waits_for_a_pause_after_useful_work() {
        const now = start + 20 * day;
        verify(!Likes.surveyEligible(survey({
            "usefulWork": false
        }), now), "never at start-up");
        verify(!Likes.surveyEligible(survey({
            "idle": 59999
        }), now), "idle about a minute");
        verify(!Likes.surveyEligible(survey({
            "fitting": true
        }), now), "never during a fit");
        verify(!Likes.surveyEligible(survey({
            "tutorial": true
        }), now), "never during a tutorial");
    }
    function test_survey_not_now_asks_again_after_30_days_and_2_sessions() {
        const shown = start + 20 * day;
        const after = survey({
            "lastShown": shown,
            "sessionsAtShown": 6
        });
        verify(!Likes.surveyEligible(Object.assign({}, after, {
            "sessions": 8
        }), shown + 30 * day - 1), "30 days");
        verify(!Likes.surveyEligible(Object.assign({}, after, {
            "sessions": 7
        }), shown + 40 * day), "2 more sessions");
        verify(Likes.surveyEligible(Object.assign({}, after, {
            "sessions": 8
        }), shown + 30 * day));
    }
    function test_survey_stopped_or_off_never_shows() {
        verify(!Likes.surveyEligible(survey({
            "stopped": true
        }), start + 100 * day), "Take the survey or Don't ask again");
        verify(!Likes.surveyEligible(survey({
            "disabled": true
        }), start + 100 * day), "Preferences off");
    }
    function test_between_the_two_bars() {
        const now = start + 60 * day;
        verify(!Likes.surveyEligible(survey({
            "barShown": true
        }), now), "never both in one session");
        verify(!Likes.eligible(likes({
            "barShown": true
        }), now), "never both in one session");
        verify(!Likes.surveyEligible(survey({
            "otherShown": now - 7 * day + 1
        }), now), "7 days after the likes bar");
        verify(Likes.surveyEligible(survey({
            "otherShown": now - 7 * day
        }), now));
        verify(!Likes.eligible(likes({
            "otherShown": now - 6 * day
        }), now), "7 days after the survey bar");
        verify(Likes.eligible(likes({
            "otherShown": now - 7 * day
        }), now));
        verify(!Likes.surveyEligible(survey({
            "likesDue": true
        }), now), "the likes bar goes first");
    }
}
