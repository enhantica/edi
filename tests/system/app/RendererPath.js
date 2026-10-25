.pragma library

function software(observed) {
    return observed.api === "Software" || /llvmpipe|softpipe|swiftshader|swrast|lavapipe|software rasterizer|microsoft basic render/i.test(observed.renderer);
}

function effectiveGpu(observed, requested) {
    return observed.api !== "Software" && (requested === "gpu" || (requested === "auto" && !software(observed)));
}

function snapshot(test, proof, layer) {
    const image = proof.snapshot(layer);
    test.verify(image.valid, "The renderer witness captures the actual plot subtree");
    return image;
}

function check(test, proof, layer, expectedGpu, settle) {
    test.compare(typeof layer.gpu, "boolean", "The loaded scan exposes its effective renderer choice");
    test.compare(layer.gpu, expectedGpu, "The effective renderer follows the saved choice and Qt backend capability");
    const child = test.findChild(layer, layer.objectName + ".gpuLines");
    test.verify(child !== null, "The Stacked view exposes its named scene-graph line child");
    test.compare(child.visible, expectedGpu, "Only the selected GPU path has a visible scene-graph line child");
    const painted = proof.paintedInk(layer);
    test.verify(painted >= -1, "The painter observation reaches a valid loaded plot surface");
    if (painted >= 0) {
        if (expectedGpu)
            test.compare(painted, 0, "A GPU-selected wrapper contributes no painted scan pixels");
        else
            test.verify(painted > 0, "The software path paints the loaded independent scan data");
    } else if (!expectedGpu) {
        test.verify(snapshot(test, proof, layer).ink > 0, "A software successor still draws visible scan content");
    }
    if (expectedGpu) {
        test.verify(!proof.painted(child), "The GPU line child draws through the scene graph");
        settle();
        const visible = snapshot(test, proof, layer);
        let hidden;
        try {
            child.visible = false;
            settle();
            test.compare(child.visible, false, "The renderer witness actually hides the GPU line child");
            hidden = snapshot(test, proof, layer);
        } finally {
            child.visible = true;
            settle();
        }
        test.compare(hidden.width, visible.width, "Renderer observations keep the same plot width");
        test.compare(hidden.height, visible.height, "Renderer observations keep the same plot height");
        test.compare(hidden.ink, 0, "The GPU-selected plot has no fallback painting behind its line child");
        test.verify(visible.ink > 0 && visible.signature !== hidden.signature, "The selected GPU child contributes actual rendered scan pixels");
    }
}
