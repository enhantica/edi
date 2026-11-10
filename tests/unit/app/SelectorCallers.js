.pragma library

var callers = [
    {
        "component": "GeneratedGroup",
        "path": "app/qml/Components/GeneratedGroup.qml",
        "owner": "generated",
        "names": [
            "generated.*"
        ]
    },
    {
        "component": "FittingModeGroup",
        "path": "app/qml/Pages/Analysis/FittingModeGroup.qml",
        "owner": "analysis",
        "names": [
            "fittingMode.type"
        ]
    },
    {
        "component": "MinimizerGroup",
        "path": "app/qml/Pages/Analysis/MinimizerGroup.qml",
        "owner": "analysis",
        "magnetic": true,
        "names": [
            "minimizer.type",
            "minimizer.descent",
            "minimizer.stopRule",
            "minimizer.momentsNearZero"
        ],
        "choices": {
            "minimizer.stopRule": {"property": "stopRule", "tokens": ["chi_square_change", "shift_su"]},
            "minimizer.momentsNearZero": {"property": "momentsNearZero", "tokens": ["try_exact_zero", "keep_free"]}
        }
    },
    {
        "component": "AbsorptionGroup",
        "path": "app/qml/Pages/Experiment/AbsorptionGroup.qml",
        "owner": "experiment",
        "names": [
            "absorption.type"
        ]
    },
    {
        "component": "BackgroundExtrasGroup",
        "path": "app/qml/Pages/Experiment/BackgroundExtrasGroup.qml",
        "owner": "experiment",
        "names": [
            "background_estimate.use_model",
            "background_estimate.method"
        ]
    },
    {
        "component": "BackgroundGroup",
        "path": "app/qml/Pages/Experiment/BackgroundGroup.qml",
        "owner": "experiment",
        "names": [
            "background.type",
            "background_estimate.mode"
        ]
    },
    {
        "component": "ExperimentTypeGroup",
        "path": "app/qml/Pages/Experiment/ExperimentTypeGroup.qml",
        "owner": "experiment",
        "names": [
            "experimentType.sampleForm",
            "experimentType.beamMode",
            "experimentType.radiationProbe",
            "experimentType.scatteringType",
            "experimentType.dimensionality",
            "experimentType.polarisation"
        ]
    },
    {
        "component": "ExtinctionGroup",
        "path": "app/qml/Pages/Experiment/ExtinctionGroup.qml",
        "owner": "experiment",
        "names": [
            "extinction.type",
            "extinction.mosaicDistribution"
        ]
    },
    {
        "component": "InstrumentGroup",
        "path": "app/qml/Pages/Experiment/InstrumentGroup.qml",
        "owner": "experiment",
        "names": [
            "instrument.facility",
            "instrument.name"
        ]
    },
    {
        "component": "ObservedThresholdRow",
        "path": "app/qml/Pages/Experiment/ObservedThresholdRow.qml",
        "owner": "experiment",
        "names": [
            "reflns.thresholdBasis"
        ]
    },
    {
        "component": "PeakGroup",
        "path": "app/qml/Pages/Experiment/PeakGroup.qml",
        "owner": "experiment",
        "names": [
            "peak.type"
        ]
    },
    {
        "component": "ScatteringSourceGroup",
        "path": "app/qml/Pages/Experiment/ScatteringSourceGroup.qml",
        "owner": "experiment",
        "names": [
            "scatteringSource.*"
        ]
    },
    {
        "component": "AppearanceGroup",
        "path": "app/qml/Pages/Structure/AppearanceGroup.qml",
        "owner": "appearance",
        "magnetic": true,
        "names": [
            "structure.appearance.atomView",
            "structure.appearance.momentView"
        ],
        "choices": {
            "structure.appearance.momentView": {"property": "momentView", "tokens": ["through_atom", "from_centre", "from_surface"]}
        }
    },
    {
        "component": "AtomSiteMomentGroup",
        "path": "app/qml/Pages/Structure/AtomSiteMomentGroup.qml",
        "owner": "moments",
        "magnetic": true,
        "names": ["atomSiteMoments.form"],
        "choices": {
            "atomSiteMoments.form": {"property": "momentForm", "tokens": ["crystal_axes", "cartesian", "spherical"]}
        }
    }
];
