"""Independent residual sums over a fresh calculation of the written model.

The calculation is a save/reopen round-trip invariant, not a new absolute
profile-kernel reference. The residual, weighting, exclusion and pooling
formulae below are independent of the save and fit-result implementations.
"""

import math

import numpy as np


def sums(observed, calculated, sigma, background, nfree):
    weight = 1 / sigma**2
    delta = observed - calculated
    chi = float(np.sum(weight * delta**2))
    norm = float(np.sum(weight * observed**2))
    corrected = observed - background

    def ratio(numerator, denominator):
        return float(numerator / denominator) if denominator > 0 else 0.0

    return {
        'rp': ratio(np.sum(np.abs(delta)), np.sum(np.abs(observed))),
        'rwp': math.sqrt(ratio(chi, norm)),
        'rexp': math.sqrt(ratio(max(len(observed) - nfree, 0), norm)),
        'crp': ratio(np.sum(np.abs(delta)), np.sum(np.abs(corrected))),
        'cwrp': math.sqrt(ratio(chi, np.sum(weight * corrected**2))),
        'chi_square': chi,
        'n_points': len(observed),
    }


def rounded_model_reference(engine, directory, reference):
    fresh = engine.Project.load(directory)
    nfree = int(reference['n_free'])
    rows = []
    expected = dict(reference)
    masks = []
    for bank in fresh.experiments:
        axis = np.asarray(bank.data.axis())
        used = np.asarray(bank.data.intensity_meas_su) > 0
        for start, end in bank.excluded_regions:
            used &= (axis < min(start, end)) | (axis > max(start, end))
        masks.append(used)
    if any(np.any(mask) for mask in masks):
        fresh.analysis.calculate()
    for bank, used in zip(fresh.experiments, masks, strict=True):
        data = bank.data
        observed = np.asarray(data.intensity_meas)
        sigma = np.asarray(data.intensity_meas_su)
        calculated = np.asarray(data.intensity_calc) if np.any(used) else np.zeros(len(used))
        background = np.asarray(data.intensity_bkg) if np.any(used) else np.zeros(len(used))
        arrays = tuple(a[used] for a in (observed, calculated, sigma, background))
        rows.append(arrays)
        metrics = sums(*arrays, nfree)
        expected.update({'bank.' + bank.name + '.' + key: value for key, value in metrics.items()})
    pooled = sums(*(np.concatenate([row[i] for row in rows]) for i in range(4)), nfree)
    expected.update({key: pooled[key] for key in ('rp', 'rwp', 'rexp', 'crp', 'cwrp')})
    expected['n_points_fitted'] = pooled['n_points']
    expected['chi_square'] = pooled['chi_square']
    expected['reduced_chi_square'] = pooled['chi_square'] / max(pooled['n_points'] - nfree, 1)
    return expected
