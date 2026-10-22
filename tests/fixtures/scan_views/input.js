.pragma library
// Analytic input: the existing three-file scan container, hand-set temperatures
// and complete intensity bands. No application calculation supplies expectations.
function prepare(proof, root, kind) {
    const files = ["all594687.dat", "all594791.dat", "all594842.dat"];
    const levels = [0, 32, 64, 96, 128, 192, 255];
    if (kind === "excluded") {
        const file = "experiments/d20.edi";
        const text = proof.text(root, file).replace("1 0. 8", "1 35 45");
        if (!proof.write(root, file, text)) throw Error("The overlapping excluded-region witness could not be written");
    }
    for (let row = 0; row < files.length; ++row) {
        let text = "XYDATA analytic scan\nTEMP " + [100, 250, 700][row] + "\n";
        for (let i = 0; i <= 4096; ++i) {
            const value = kind === "zoom" ? [0, 17, 230, 41, 180, 64, 255, 11][i % 8] : kind === "rows" ? [0, 128, 255][row] : levels[Math.min(6, Math.floor(i * 7 / 4097))];
            text += (10 + i / 40).toFixed(3) + " " + value + " 1\n";
        }
        if (!proof.write(root, "experiments/d20_scan/" + files[row], kind === "broken" && row === 1 ? "invalid pattern\n" : text))
            throw Error("The private analytic scan input could not be written");
    }
}
function joint(proof, root, independent) {
    for (const [row, name] of [[0,"expt_n2"],[1,"expt_s2"]]) {
        const file="experiments/"+name+".edi";
        let text=proof.text(root,file);
        const offset=[13,-19][row], slope=[1000,2500][row];
        for(const [key,value] of [["offset",offset],["linear",slope],["quadratic",0],["reciprocal",0]])
            text=text.replace(new RegExp("(_instrument.calib_d_to_tof_"+key+" )[^\\n]+"),function(match, prefix) { return prefix+value; });
        const header=text.indexOf("loop_\n_data.time_of_flight");
        if(header<0) throw Error("The independent joint fixture requires the declared measured-data loop");
        text=text.slice(0,header)+"loop_\n_data.time_of_flight\n_data.intensity_meas\n_data.intensity_meas_su\n";
        for(let index=0;index<=128;++index) {
            const d=.8+index/64, intensity=Math.max(0,255*(1-Math.abs(index-64)/16));
            text+=(offset+slope*d).toFixed(8)+" "+intensity+" 1\n";
        }
        if(!proof.write(root,file,text)) throw Error("The analytic joint bank could not be written");
    }
    if(independent) {
        const file="analysis/analysis.edi", text=proof.text(root,file).replace(/_fitting_mode.type joint/,"_fitting_mode.type single");
        if(!proof.write(root,file,text)) throw Error("The independent fitting-mode control could not be written");
    }
}
