// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import edi.app

// A label shows the widest of its forms that fits: the long text, else the short one, else its icon alone, never cut,
// with the long text in its tooltip while another form shows.
Item {
    id: root

    width: 600
    height: 100

    AdaptiveLabel {
        id: label

        longText: "Site symmetry operator"
        shortText: "Sym"
        icon: "sync-alt"
    }

    // A registry row's forms, as a table header has them.
    HeaderLabel {
        id: header

        y: 40
        uid: "geom_bond.site_symmetry_1"
    }

    TestCase {
        name: "LabelForms"
        when: windowShown

        function test_the_widths_order_the_forms() {
            verify(label.longWidth > label.shortWidth);
            verify(label.shortWidth > label.iconWidth);
            verify(label.iconWidth > 0);
        }
        function test_the_widest_form_that_fits_shows() {
            label.width = label.longWidth;
            tryCompare(label, "form", "long");
            compare(label.text, "Site symmetry operator");
            verify(!label.shortened);

            label.width = label.longWidth - 1;
            tryCompare(label, "form", "short");
            compare(label.text, "Sym");

            label.width = label.shortWidth - 1;
            tryCompare(label, "form", "icon");
            compare(label.text, "");
        }
        function test_the_long_text_is_the_tooltip_while_shortened() {
            label.width = label.shortWidth;
            tryVerify(() => label.shortened);
            compare(label.fullText, "Site symmetry operator");
            label.width = label.iconWidth;
            tryCompare(label, "form", "icon");
            verify(label.shortened);
            compare(label.fullText, "Site symmetry operator");
        }
        function test_formFor_reads_the_widths_alone() {
            compare(label.formFor(label.longWidth), "long");
            compare(label.formFor(label.shortWidth), "short");
            compare(label.formFor(label.iconWidth), "icon");
            compare(label.formFor(0), "icon");
        }
        function test_a_header_takes_its_registry_row() {
            compare(header.longText, Session.label("geom_bond.site_symmetry_1"));
            compare(header.shortText, "Sym 1");
            compare(header.reservedWidth, header.shortWidth);
            header.width = header.shortWidth;
            tryCompare(header, "text", "Sym 1");
        }
    }
}
