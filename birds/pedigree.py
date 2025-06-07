# -*- mode: python -*-
"""Functions for computing inbreeding and relatedness coefficients"""

import numpy as np
import numpy.typing as npt


def inbreeding_coeffs(sire_ids: npt.ArrayLike, dam_ids: npt.ArrayLike) -> np.ndarray:
    """Calculate inbreeding coefficients using LAP-based modification of
    Meuwissen & Luo algorithm.

    This algorithm from Sargolzaei and Iwaisaki (2005) uses Longest Ancestral Path (LAP)
    to organize processing by generation levels, making it more efficient than the basic
    M&L algorithm. Adapted from the C code in the R `pedigreemm` package.

    Parameters:
    -----------
    sire_ids : array-like
        Array of sire IDs (1-indexed, 0 for missing)
    dam_ids : array-like
        Array of dam IDs (1-indexed, 0 for missing)

    Returns:
    --------
    numpy.ndarray
        Array of inbreeding coefficients

    Notes:
    ------
    - Animals must be sorted so that parents appear before offspring
    """
    sire_ids = np.asarray(sire_ids, dtype=np.int32)
    dam_ids = np.asarray(dam_ids, dtype=np.int32)
    n = sire_ids.size
    assert dam_ids.size == n, "Sire and dam arrays must be same length"

    # Initialize arrays (the 0 slot is used for unknown parents)
    F = np.zeros(n + 1, dtype=np.float64)  # Inbreeding coefficients
    L = np.zeros(n + 1, dtype=np.float64)  # Working coefficients
    B = np.zeros(n + 1, dtype=np.float64)  # Diagonal elements
    LAP = np.zeros(n + 1, dtype=np.int32)  # Longest ancestral path
    Anc = np.zeros(n + 1, dtype=np.int32)  # Ancestor array

    # Set values for unknown parents (index 0)
    F[0] = -1.0
    LAP[0] = -1

    # Calculate LAP (Longest Ancestral Path) for each animal
    max_lap = -1
    for i in range(1, n + 1):
        sire_idx = sire_ids[i - 1]
        dam_idx = dam_ids[i - 1]
        LAP[i] = max(LAP[sire_idx], LAP[dam_idx]) + 1
        if LAP[i] > max_lap:
            max_lap = LAP[i]

    # Initialize start and minor indices for each LAP level
    SI = np.zeros(max_lap + 1, dtype=np.int32)  # Start index for each level
    MI = np.zeros(max_lap + 1, dtype=np.int32)  # Minor index for each level

    # Process each animal
    for i in range(1, n + 1):
        sire_idx = sire_ids[i - 1]
        dam_idx = dam_ids[i - 1]

        # Calculate diagonal element
        B[i] = 0.5 - 0.25 * (F[sire_idx] + F[dam_idx])

        # Adjust start and minor indices for this animal's LAP level
        for j in range(LAP[i]):
            SI[j] += 1
            MI[j] += 1

        # Handle special cases:
        # At least one parent unknown
        if sire_idx == 0 or dam_idx == 0:
            F[i] = 0.0
            L[i] = 0.0
            continue

        # Full sib of previous animal
        if i > 1 and sire_idx == sire_ids[i - 2] and dam_idx == dam_ids[i - 2]:
            F[i] = F[i - 1]
            L[i] = L[i - 1]
            continue

        # Initialize for this animal
        F[i] = -1.0
        L[i] = 1.0

        # Start processing from the highest LAP level
        t = LAP[i]
        Anc[MI[t]] = i
        MI[t] += 1

        # Process ancestors level by level
        while t > -1:
            # Get next ancestor from current level
            MI[t] -= 1
            j = Anc[MI[t]]

            # Get parents of current ancestor
            S_anc = sire_ids[j - 1] if j <= n else 0
            D_anc = dam_ids[j - 1] if j <= n else 0

            # Add sire to ancestor list if not already processed
            if S_anc > 0:
                if L[S_anc] == 0.0:  # Not yet added
                    Anc[MI[LAP[S_anc]]] = S_anc
                    MI[LAP[S_anc]] += 1
                L[S_anc] += 0.5 * L[j]

            # Add dam to ancestor list if not already processed
            if D_anc > 0:
                if L[D_anc] == 0.0:  # Not yet added
                    Anc[MI[LAP[D_anc]]] = D_anc
                    MI[LAP[D_anc]] += 1
                L[D_anc] += 0.5 * L[j]

            # Accumulate inbreeding coefficient
            F[i] += L[j] * L[j] * B[j]

            # Clear L[j] for next animal
            L[j] = 0.0

            # Move to next LAP level when current level is exhausted
            if MI[t] == SI[t]:
                t -= 1

    # Return inbreeding coefficients (dropping the placeholder)
    return F[1:]
