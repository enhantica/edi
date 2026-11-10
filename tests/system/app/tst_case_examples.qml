// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import EdiOnlineHttpFixture 1.0
import EasyApplication.Gui.Style as Style
import "../../unit/app/UiInteraction.js" as Ui
import "../../unit/app/RenderedTable.js" as Render

Item {
    width: 1100
    height: 1000
    ExamplesGroup { id: examples; width: 1000; collapsed: false }
    TestCase {
        name: "CaseExamples"
        when: windowShown
        function test_observe_case_catalogue_and_painted_tags() {
            const input = JSON.parse(Probe.readReferenceFile("case-examples.json"));
            verify(OnlineHttpFixture.attachExamples(Session), "The observer replaces only the collection transport");
            OnlineHttpFixture.clearExamples();
            OnlineHttpFixture.exampleText(200, JSON.stringify(input.index));
            OnlineHttpFixture.useDefaultLocations(Session);
            tryVerify(() => OnlineHttpFixture.exampleKnown(Session, input.ready), 5000, "The real parser adopts the complete index before the Examples list is observed");
            compare(OnlineHttpFixture.exampleRequests().length, 1, "The catalogue consumes one actual index response");
            verify(OnlineHttpFixture.exampleRequests()[0].endsWith("/index.json"), "The observer exercises index loading, without downloading authored placeholder archives");
            Session.examples.searchText = "";
            Session.examples.filterProperty = "purpose";
            Session.examples.filterValue = "";
            verify(waitForPolish(examples), "The actual Examples group finishes layout after the index update");
            const rows = Probe.rows(Session.examples);
            console.info("CASE_EXAMPLES_MODEL " + JSON.stringify(rows));
            const table = Ui.find(examples, "examples.list");
            verify(table !== null && table.count === rows.length, "The actual table contains every unfiltered model row");
            for (let index = 0; index < rows.length; ++index) {
                table.positionViewAtIndex(index, ListView.Contain);
                verify(waitForPolish(table), "Each actual Examples delegate finishes layout after scrolling");
                let row = null;
                tryVerify(() => {
                    row = table.itemAtIndex(index);
                    return row !== null && row.objectName === "examples.open." + rows[index].exampleId;
                }, 2000, "The observer reaches each current real row by identity");
                if (input.paintExtra && index === 0) {
                    const extra = Qt.createQmlObject('import QtQuick; Rectangle { radius: 3; width: 180; height: 24; color: "#abcdef"; Text { text: "Fixture Observatory" } }', row);
                    verify(extra !== null && waitForPolish(extra), "The escape control paints an opaque provenance badge outside the tag model");
                }
                const badges = Render.descendants(row).filter(item => item.radius > 0 && item.height > 0 && item.height < row.height / 2 && item.color && item.color.a > 0 && Render.texts(item).length > 0);
                let labels = [];
                for (const badge of badges)
                    labels = labels.concat(Render.texts(badge).filter(item => item.font.family !== Style.Fonts.iconsFamily).map(item => item.text));
                console.info("CASE_EXAMPLES_PAINTED " + JSON.stringify({id: rows[index].exampleId, labels: labels}));
            }
        }
    }
}
