import QtQuick
import QtTest
import ReportAcceptance 1.0

Item {
    TestCase {
        name: "PolyhedraNeighbourhood"
        readonly property var reference: JSON.parse(SettingsProof.repoText("tests/fixtures/structure_features/polyhedra-reference.json"))
        function test_complete_periodic_neighbourhood_data() {
            return reference.neighbourhoods;
        }
        function key(point) {
            return point.map(value => value.toFixed(7)).join(",");
        }
        function test_complete_periodic_neighbourhood(data) {
            const inside = SettingsProof.polyhedraWitness(data, false);
            verify(inside.current, "The independently declared source is current for the inside-cell control");
            compare(inside.faces.length, 0, "Three in-cell neighbours enclose no coordination volume");
            const complete = SettingsProof.polyhedraWitness(data, true);
            verify(complete.current, "Complete extent consumes the same current declared source");
            verify(complete.faces.length > 0, "Complete periodic neighbours enclose a genuine volume");
            const actual = complete.corners.map(key).sort();
            const expected = data.expected.map(key).sort();
            compare(actual, expected, "Complete extent includes every independently enumerated neighbour in orthogonal or skew cells with explicit or bond-derived distance");
            verify(data.beyond_adjacent.length > 0 && data.beyond_adjacent.every(point => actual.includes(key(point))), "Every fixture exercises actual neighbours outside the old adjacent-cell image cube");
        }
        function test_affine_shell_volume_data() {
            return reference.shells;
        }
        function test_affine_shell_volume(data) {
            const result = SettingsProof.polyhedraWitness(data, true);
            compare(result.faces.length, data.faces, "A shell must span three dimensions; genuine polygonal faces remain triangulated");
            let volume = 0;
            const edges = {};
            for (const face of result.faces) {
                const [a, b, c] = face.map(index => data.points[index]);
                const cross = [b[1] * c[2] - b[2] * c[1], b[2] * c[0] - b[0] * c[2], b[0] * c[1] - b[1] * c[0]];
                volume += (a[0] * cross[0] + a[1] * cross[1] + a[2] * cross[2]) / 6;
                for (let i = 0; i < 3; ++i) {
                    const edge = [face[i], face[(i + 1) % 3]].sort((x, y) => x - y).join(",");
                    edges[edge] = (edges[edge] || 0) + 1;
                }
            }
            verify(Math.abs(volume - data.volume) < 1e-9, "Outward shell triangles enclose the independent analytic volume");
            verify(Object.values(edges).every(count => count === 2), "Every noncoplanar shell edge belongs to exactly two outward faces");
        }
    }
}
