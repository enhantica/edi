import QtQuick
import QtTest
import ReportBoundaryAcceptance 1.0

TestCase {
    name: "ReportStaticCellBorders"
    function test_pdf_text_layout_retains_every_empty_and_filled_cell_border() {
        const cells = BoundaryProof.staticCorrelationCellBorders();
        compare(cells.length, 4, "The PDF's real Qt text layout consumes the independent two-by-two matrix");
        const filled = cells.find(cell => cell.row === 2 && cell.column === 1);
        verify(filled !== undefined && filled.top > 0 && filled.right > 0 && filled.bottom > 0 && filled.left > 0, "The filled-cell control proves Qt actually consumes the delivered border styles");
        const failures = [];
        for (const cell of cells)
            for (const side of ["top", "right", "bottom", "left"])
                if (!(cell[side] > 0))
                    failures.push([cell.row, cell.column, side].join(":"));
        compare(failures.length, 0, "The actual PDF text layout borders all filled, diagonal and empty correlation cells: " + failures.join(", "));
    }
}
