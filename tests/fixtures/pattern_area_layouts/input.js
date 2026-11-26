.pragma library

function mixed(proof, root) {
    const cw = proof.text(root, "experiments/pattern.edi");
    const tof = proof.repoText("tests/fixtures/excluded_display/tof/experiments/pattern.edi");
    const block = cw.replace(/^data_pattern/m, "data_z_cw_peer").replace("2 90.0 80", "2 90.0 160");
    return proof.write(root, "experiments/time_of_flight.edi", tof.replace(/^data_pattern/m, "data_time_of_flight")) &&
           proof.write(root, "experiments/z_cw_peer.edi", block);
}
