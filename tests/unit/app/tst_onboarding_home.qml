// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import OnboardingAcceptance 1.0
import "RenderedTable.js" as Render
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "OnboardingHome"
    when: windowShown
    property var app
    Component {
        id: application
        Main {}
    }

    function init() {
        app = application.createObject(null);
        verify(app !== null, "Home acceptance opens the production application window");
        AppState.open(AppState.Page.Home);
        verify(waitForRendering(app.contentItem), "Home acceptance observes a rendered production window");
        OnboardingProbe.interceptUrls();
    }
    function cleanup() {
        const urls = OnboardingProbe.urls();
        OnboardingProbe.releaseUrls();
        verify(urls.every(url => /^https?:\/\/[^/]+/.test(url)), "Every onboarding link reaching the system URL handler is an absolute HTTP(S) address");
        if (app)
            app.destroy();
        app = null;
    }
    function button(text) {
        const matches = Probe.objectsWithProperty(app, "text").filter(item => item.visible && item.text === text && typeof item.clicked === "function");
        compare(matches.length, 1, "Home exposes exactly one visible action labelled " + text);
        return matches[0];
    }
    function click(control) {
        verify(control.enabled && control.width > 0 && control.height > 0, "The Home action is enabled and has an input rectangle");
        mouseClick(control, control.width / 2, control.height / 2);
    }
    function test_six_links_have_icons_and_two_columns() {
        const labels = ["Tutorials", "What's new", "Documentation", "Help and feedback", "How to cite", "About " + ApplicationInfo.name];
        const controls = labels.map(label => button(label));
        verify(/^(external-link(?:-alt)?|arrow-up-right-from-square|square-arrow-up-right|up-right-from-square)$/.test(controls[2].fontIcon), "Documentation carries the app's external-resource icon, not a book or internal-action icon");
        const points = controls.map(control => control.mapToItem(app.contentItem, 0, 0));
        for (const control of controls) {
            verify(typeof control.fontIcon === "string" && control.fontIcon.length > 0, "Each Home link has its own leading icon");
            verify(!OnboardingProbe.inheritsType(control, "SideBarButton") && (control.flat === undefined || control.flat), "Home actions retain the prior light link treatment instead of sidebar button chrome");
            const labels = Render.texts(control).filter(item => item.text === control.text);
            verify(labels.length > 0, "Every Home link paints its actual label");
            const label = labels[0];
            compare(label.horizontalAlignment, Text.AlignLeft, "Home link labels are left aligned");
        }
        const text = Render.texts(app.contentItem).map(item => item.text);
        verify(!text.includes("Learn") && !text.includes("Contact and about"), "The two Home link columns have no Learn or Contact and about headers");
        for (let i = 0; i < 3; ++i) {
            verify(Math.abs(points[i].x - points[0].x) < 1, "First-column links occupy one column");
            verify(Math.abs(points[i + 3].x - points[3].x) < 1, "Second-column links occupy the second column");
            if (i > 0) {
                verify(points[i].y > points[i - 1].y, "First-column links occur in the agreed vertical order");
                verify(points[i + 3].y > points[i + 2].y, "Second-column links occur in the agreed vertical order");
            }
        }
        verify(points[3].x > points[0].x, "The second link column follows the first horizontally");
    }
    function test_public_documentation_destinations_data() {
        return [
            {
                tag: "documentation",
                label: "Documentation"
            },
            {
                tag: "changes",
                label: "What's new"
            }
        ];
    }
    function test_public_documentation_destinations(data) {
        click(button(data.label));
        if (data.tag === "changes") {
            compare(OnboardingProbe.urls().length, 0, "What's new first opens an in-app popup rather than an external page");
            const popup = Probe.objectsWithProperty(app, "objectName").find(item => item.objectName === "whatsNew");
            verify(popup !== undefined, "What's new has its own actual changes popup");
            tryCompare(popup, "opened", true, 2000, "The changes popup is open before its documentation link receives input");
            const link = Probe.objectsWithProperty(popup, "objectName").find(item => item.objectName === "whatsNew.page");
            verify(link !== undefined, "The changes popup exposes its full documentation page link");
            Ui.scrollIntoView(link);
            verify(waitForPolish(link), "The changes-page link finishes layout after scrolling into view");
            const point = Ui.clickPoint(link);
            verify(point !== null && Ui.rendered(link), "The in-app changes page exposes its documentation link before real input");
            mouseClick(link, point.x, point.y);
        }
        const urls = OnboardingProbe.urls();
        compare(urls.length, 1, "Each documentation action dispatches exactly one URL");
        verify(/^https:\/\/enhantica\.github\.io\/edi(?:\/|$)/.test(urls[0]), "Home documentation actions use the public edi documentation origin and path");
        if (data.tag === "changes")
            verify(/changelog|whats-new|what.s.new|changes/.test(urls[0]), "The popup's full-page link opens the documentation's changes page");
    }
    function stubFeedback() {
        const form = Probe.objectsWithProperty(app, "objectName").find(item => item.objectName === "feedback.form");
        verify(form !== undefined, "The application exposes the real form before feedback entry");
        form.endpoint = "https://feedback.example.invalid/feedback";
        form.transport = function () {
            fail("Home feedback routing never invokes a network transport");
        };
    }
    function test_feedback_opens_one_form_with_default_attachment() {
        stubFeedback();
        click(button("Help and feedback"));
        const popups = Probe.visiblePopups(app);
        verify(popups.length > 0, "Help and feedback opens the application's form");
        const root = popups[popups.length - 1];
        const texts = Probe.objectsWithProperty(root, "text").map(item => item.text);
        for (const label of ["Include app version, system and log", "Show what will be sent", "Cancel", "Send"])
            verify(texts.includes(label), "The feedback form includes the agreed control: " + label);
        verify(!texts.includes("What is this about?"), "The feedback form omits the redundant kind question label");
        const attachments = Probe.objectsWithProperty(root, "checked").filter(item => item.text === "Include app version, system and log");
        compare(attachments.length, 1, "The feedback form has one attachment checkbox");
        compare(attachments[0].checked, true, "The feedback attachment checkbox starts ticked");
        compare(OnboardingProbe.urls().length, 0, "Opening feedback does not open an external destination");
    }

    function test_internal_actions_never_dispatch_resource_urls_data() {
        return [
            {
                tag: "tutorials",
                label: "Tutorials"
            },
            {
                tag: "citation",
                label: "How to cite"
            },
            {
                tag: "about",
                label: "About " + ApplicationInfo.name
            },
            {
                tag: "feedback",
                label: "Help and feedback"
            }
        ];
    }
    function test_internal_actions_never_dispatch_resource_urls(data) {
        click(button(data.label));
        tryVerify(() => Probe.visiblePopups(app).length > 0, 2000, "An internal Home action opens its actual popup: " + data.label);
        compare(OnboardingProbe.urls().length, 0, "Internal onboarding actions never dispatch local or relative URLs to the operating system");
    }
    function citationReference() {
        const source = OnboardingProbe.sourceText("CITATION.cff");
        const reference = {};
        for (const field of ["title", "doi"]) {
            const lines = source.split(/\r?\n/).filter(line => line.startsWith(field + ":"));
            compare(lines.length, 1, "The CFF reference declares exactly one top-level " + field);
            const scalar = lines[0].substring(field.length + 1).trim();
            if (scalar.startsWith('"'))
                reference[field] = JSON.parse(scalar);
            else if (scalar.startsWith("'")) {
                verify(scalar.endsWith("'"), "A quoted CFF reference scalar must close its quote");
                reference[field] = scalar.slice(1, -1).replace(/''/g, "'");
            } else
                reference[field] = scalar.replace(/\s+#.*$/, "").trim();
            verify(typeof reference[field] === "string" && reference[field].length > 0, "The CFF reference provides a nonempty scalar " + field);
        }
        return reference;
    }
    function test_citation_clipboard_uses_the_shared_placeholder() {
        click(button("How to cite"));
        const citation = citationReference();
        verify(citation && citation.title && citation.doi, "Citation acceptance reads the one CFF placeholder source");
        const popups = Probe.visiblePopups(app);
        verify(popups.length > 0, "Clipboard acceptance uses the real citation popup");
        const root = popups[popups.length - 1];
        for (const kind of ["text", "bibtex"]) {
            const matches = Probe.objectsWithProperty(root, "objectName").filter(item => item.objectName === "citation.copy." + kind);
            compare(matches.length, 1, "The citation popup exposes its actual copy action " + kind);
            mouseClick(matches[0]);
            const copied = OnboardingProbe.clipboard();
            verify(copied.includes(citation.title) && copied.includes(citation.doi), "Both citation copies use the title and DOI from the shared placeholder");
            if (kind === "bibtex")
                verify(/@\w+\s*\{/.test(copied) && /doi\s*=/.test(copied), "The BibTeX action copies a structured BibTeX entry");
        }
    }
    function test_citation_popup_offers_text_and_bibtex() {
        click(button("How to cite"));
        const popups = Probe.visiblePopups(app);
        verify(popups.length > 0, "How to cite opens the application's citation popup");
        const texts = Probe.objectsWithProperty(popups[popups.length - 1], "text").map(item => item.text);
        verify(texts.some(text => /BibTeX/i.test(text)), "The citation popup offers BibTeX copying");
        verify(texts.some(text => /copy.*text|text.*copy/i.test(text)), "The citation popup offers plain-text copying");
    }
}
