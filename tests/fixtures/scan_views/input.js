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
function joint(proof, root, independent, axes = "tof") {
    for (const [row, name] of [[0,"expt_n2"],[1,"expt_s2"]]) {
        const file="experiments/"+name+".edi";
        let text=proof.text(root,file);
        const offset=[13,-19][row], slope=[1000,2500][row];
        for(const [key,value] of [["offset",offset],["linear",slope],["quadratic",0],["reciprocal",0]])
            text=text.replace(new RegExp("(_instrument.calib_d_to_tof_"+key+" )[^\\n]+"),function(match, prefix) { return prefix+value; });
        const header=text.indexOf("loop_\n_data.time_of_flight");
        if(header<0) throw Error("The independent joint fixture requires the declared measured-data loop");
        const cwl = axes === "cwl" || axes === "mixed" && row === 1;
        const wavelength=[1.54,1.87][row];
        text=text.slice(0,header);
        if(cwl) {
            text=text.replace("_experiment_type.beam_mode time-of-flight", '_experiment_type.beam_mode "constant wavelength"').replace("_peak.type tof-pseudo-voigt","_peak.type cwl-tch-pseudo-voigt");
            text=text.replace(/^_instrument.calib_d_to_tof_.*\n/gm,"").replace(/^_instrument.setup_twotheta_bank.*\n/gm,"").replace(/^_peak.broad_.*\n/gm,"");
            text+="_instrument.setup_wavelength "+wavelength+"\n_instrument.calib_twotheta_offset 0\n_peak.broad_gauss_u 0\n_peak.broad_gauss_v 0\n_peak.broad_gauss_w .15\n_peak.broad_lorentz_x 0\n_peak.broad_lorentz_y 0\n";
        }
        text+="loop_\n_data."+(cwl?"two_theta":"time_of_flight")+"\n_data.intensity_meas\n_data.intensity_meas_su\n";
        for(let index=0;index<=128;++index) {
            const d=(cwl?1.2:.8)+index/64, intensity=Math.max(0,255*(1-Math.abs(index-64)/16));
            const x=cwl?Math.asin(wavelength/(2*d))*360/Math.PI:offset+slope*d;
            text+=x.toFixed(8)+" "+intensity+" 1\n";
        }
        if(!proof.write(root,file,text)) throw Error("The analytic joint bank could not be written");
    }
    if(independent) {
        const file="analysis/analysis.edi", text=proof.text(root,file).replace(/_fitting_mode.type joint/,"_fitting_mode.type single");
        if(!proof.write(root,file,text)) throw Error("The independent fitting-mode control could not be written");
    }
}

function dense(proof, root, jointRows) {
    const count=48;
    const pattern="XYDATA dense independent rows\n";
    if(!jointRows) {
        for(const name of ["all594687.dat","all594791.dat","all594842.dat"])
            if(!proof.remove(root,"experiments/d20_scan/"+name)) throw Error("The dense fixture replaces the original private scan files");
        for(let i=0;i<count;++i) {
            const text=pattern+"TEMP "+(100+i*7+.345).toFixed(3)+"\n10 10 1\n40 20 1\n80 10 1\n";
            if(!proof.write(root,"experiments/d20_scan/row_"+String(i).padStart(3,"0")+".dat",text)) throw Error("The dense independent scan file could not be written");
        }
    } else {
        const template=proof.text(root,"experiments/expt_n2.edi");
        for(let i=0;i<count;++i) {
            const name="row_"+String(i).padStart(3,"0");
            if(!proof.write(root,"experiments/"+name+".edi",template.replace(/^data_[^\n]+/,"data_"+name))) throw Error("The dense independent datablock could not be written");
        }
        for(const name of ["expt_n2","expt_s2"])
            if(!proof.remove(root,"experiments/"+name+".edi")) throw Error("The dense joint fixture replaces its original private banks");
    }
    return count;
}
