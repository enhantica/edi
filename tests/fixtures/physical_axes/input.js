.pragma library
.import "../pattern_styles/input.js" as Input

// Declared stimulus only: three measured values, a zero-scale structure and flat background.
function prepare(proof, root, beam) {
            if (beam === "cw") {
                
                Input.prepare(proof, root);
                const path = "experiments/bank.edi";
                const input = proof.text(root, path).replace("_instrument.setup_wavelength 1.54", "_instrument.setup_wavelength 1.87");
                if (!proof.write(root, path, input)) throw Error("Cannot write the declared CW axis input");
            } else {
                
                const path = "experiments/pattern.edi";
                let input = proof.text(root, path).replace("_instrument.calib_d_to_tof_offset 37", "_instrument.calib_d_to_tof_offset 0").replace("_instrument.calib_d_to_tof_linear 5000", "_instrument.calib_d_to_tof_linear 1734.5").replace("_instrument.calib_d_to_tof_quadratic 2.5", "_instrument.calib_d_to_tof_quadratic 0").replace("phase 1", "phase 0");
                const start = input.indexOf("_background.type");
                if (start < 0) throw Error("The TOF input must declare its background");
                input = input.slice(0, start) + "_background.type line-segment\nloop_\n_background.id\n_background.position\n_background.intensity\nleft 1200 6\nright 5900 6\nloop_\n_data.time_of_flight\n_data.intensity_meas\n_data.intensity_meas_su\n1200 20 2\n3100 33 3\n5900 25 4\n";
                if (!proof.write(root, path, input)) throw Error("Cannot write the declared TOF axis input");
            }
    const file = beam === "cw" ? "experiments/bank.edi" : "experiments/pattern.edi";
    const peer = proof.text(root, file).replace(/^data_\S+/, "data_z_axis_peer");
    if (!proof.write(root, "experiments/z_axis_peer.edi", peer)) throw Error("Cannot write the second independently declared axis dataset");
    if (!proof.write(root, "analysis/analysis.edi", "_edi.schema_version 3\n_fitting_mode.type joint\n")) throw Error("Cannot declare the two-dataset axis project");
}
