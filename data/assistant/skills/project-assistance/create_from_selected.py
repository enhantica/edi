# SPDX-License-Identifier: BSD-3-Clause
"""Reference only: explicit selected CIF/raw data + actual experiment recipe -> new saved candidate.
No inference, fit, original mutation, converter, or host publication. Not yet executed.
"""
from pathlib import Path
import argparse
import json
import edi

def main():
    a = argparse.ArgumentParser()
    a.add_argument("--cif", type=Path, required=True)
    a.add_argument("--data", type=Path, required=True)
    a.add_argument("--recipe", type=Path, required=True)
    a.add_argument("--output", type=Path, required=True)
    args = a.parse_args()
    if args.output.exists():
        raise ValueError("Choose a new candidate directory; existing output is preserved")
    recipe = json.loads(args.recipe.read_text(encoding="utf-8"))
    axes = recipe["experiment_type"]
    for name in ("sample_form", "beam_mode", "radiation_probe", "scattering_type"):
        if not isinstance(axes.get(name), str) or not axes[name]:
            raise ValueError("Actual measurement type is required: " + name)
    if not recipe.get("instrument") or not recipe.get("peak") or "background" not in recipe:
        raise ValueError("Supply genuine instrument, profile and background metadata first")
    structure = edi.StructureFactory.from_cif_path(args.cif)
    experiment = edi.ExperimentFactory.from_dict(recipe)
    observed = edi.ExperimentFactory.from_data_path(
        name=experiment.name, data_path=args.data, **{k: axes[k] for k in
        ("sample_form", "beam_mode", "radiation_probe", "scattering_type")})
    experiment.data = observed.data
    experiment.linked_structure.structure_id = structure.name
    project = edi.Project(name=args.output.name)
    # Actual singular setters replace the default first structure/experiment;
    # appending blindly would leave their default siblings in the candidate.
    project.structure = structure
    project.experiment = experiment
    project.save_as(args.output)
    edi.Project.load(args.output)
    print("Saved and reopened candidate. Calculation/refinement/publication have not run.")

if __name__ == "__main__":
    main()
