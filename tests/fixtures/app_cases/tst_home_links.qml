// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest

import edi.app

// Home's two columns of four links in the owner's order, the survey's tooltip, the likes bar on demand from Home, and
// no survey link left in the feedback form.
Item {
    id: root

    width: 1200
    height: 900

    HomePage {
        id: home

        anchors.fill: parent
    }
    LikesBar {
        id: bar

        width: root.width
        anchors.bottom: parent.bottom
    }
    FeedbackDialog {
        id: form

        parent: root
        roomWidth: root.width
    }

    TestCase {
        name: "HomeLinks"
        when: windowShown

        function names(column) {
            return Array.from(findChild(home, column).children).filter(item => item.objectName !== "").map(item => item.objectName);
        }

        function test_two_columns_of_four_in_order() {
            compare(names("home.learn"), ["home.tutorials", "home.documentation", "home.changes", "home.cite"]);
            compare(names("home.contact"), ["home.feedback", "home.likes", "home.survey", "home.about"]);
            compare(findChild(home, "home.likes").fontIcon, "heart");
            compare(findChild(home, "home.survey").fontIcon, "external-link-alt");
            compare(findChild(home, "home.survey").ToolTip.text, "About 10–15 minutes");
        }
        function test_enjoying_shows_the_bar_whatever_its_timing() {
            verify(!bar.visible);
            mouseClick(findChild(home, "home.likes"));
            tryVerify(() => bar.visible);
            compare(bar.stage, "ask");
        }
        function test_the_form_has_no_survey_link() {
            form.open();
            tryVerify(() => form.opened);
            compare(findChild(form, "feedback.survey"), null);
            form.close();
        }
    }
}
