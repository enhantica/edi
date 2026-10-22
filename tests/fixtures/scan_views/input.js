.pragma library
// Analytic input: the existing three-file scan container, hand-set temperatures
// and complete intensity bands. No application calculation supplies expectations.
function prepare(proof, root, kind) {
    const files = ["all594687.dat", "all594791.dat", "all594842.dat"];
    const levels = [0, 32, 64, 96, 128, 192, 255];
    for (let row = 0; row < files.length; ++row) {
        let text = "XYDATA analytic scan\nTEMP " + [100, 250, 700][row] + "\n";
        for (let i = 0; i <= 4096; ++i) {
            const value = kind === "rows" ? [0, 128, 255][row] : levels[Math.min(6, Math.floor(i * 7 / 4097))];
            text += (10 + i / 40).toFixed(3) + " " + value + " 1\n";
        }
        if (!proof.write(root, "experiments/d20_scan/" + files[row], kind === "broken" && row === 1 ? "invalid pattern\n" : text))
            throw Error("The private analytic scan input could not be written");
    }
}
