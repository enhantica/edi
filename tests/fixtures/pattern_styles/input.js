.pragma library
function prepare(proof, root, balanced = false) {
    const file="experiments/bank.edi";
    let text=proof.text(root,file).replace("phase 0.7","phase 0");
    const first=text.indexOf("_background.type");
    if(first<0) throw Error("The style fixture requires its declared background section");
    text=text.slice(0,first)+"_background_estimate.mode manual\n_background.type line-segment\nloop_\n_background.id\n_background.position\n_background.intensity\nleft 30 6\nright 80 6\n\nloop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n40 20 2\n52 33 3\n64 25 4\n";
    if (balanced) text = text.replace("40 20 2\n52 33 3\n64 25 4", "40 5 2\n52 7 3\n64 6 4");
    if(!proof.write(root,file,text)) throw Error("The independent three-point style input could not be written");
}
