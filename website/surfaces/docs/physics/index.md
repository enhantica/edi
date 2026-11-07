---
template: physics.html
html_title: "Physics: Start here"
---

# Start here

This reference explains the models and numerical conventions used to calculate and refine EasyDiffraction projects. The equations apply across the application, Python and the command line; the [feature matrix](../user-guide/features.md) distinguishes what each interface can do.

## Find a physical model

[Physical models](physical-models/index.md) lists each model with the questions it answers, grouped from the diffraction itself to the refinement.

## Look up a type or parameter

The [model catalogue](models.md) lists supported model tokens and their explanations. The [parameter index](parameters.md) links each scientific parameter to its equation, units and applicable model. [Conventions](conventions.md) fixes the notation used throughout the reference.

## Use the reference with the assistant

Use a model's exact name and the parameter or equation link when asking a question. The assistant should identify the experiment type and units before applying an equation, distinguish an active parameter from a stored field, and cite the relevant section. Model availability is scoped to the [reference snapshot](models.md#reference-snapshot).

The [assistant index](../llms.txt) provides a machine-friendly entry point; the [machine-readable catalogue](catalogue.json) identifies model and parameter pages. These are a retrieval source for the assistant, not a claim that chat integration has already been implemented.
