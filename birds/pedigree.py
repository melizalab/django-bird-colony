# -*- mode: python -*-
"""Functions for computing inbreeding and relatedness coefficients"""

from collections import defaultdict, deque
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt


@dataclass
class Pedigree:
    names: Sequence[str]
    sires: Sequence[str | None]
    dams: Sequence[str | None]
    indices: dict[str, int] = field(init=False)

    def __post_init__(self):
        self.indices = {name: index for index, name in enumerate(self.names, start=1)}

    @classmethod
    def from_animals(cls, animals: Sequence):
        """Construct a pedigree from a sequence of (id, sire, dam) tuples"""
        return cls(*zip(*animals, strict=False))

    def index(self, name: str) -> int:
        return self.indices.get(name, 0)

    def sire_array(self) -> np.ndarray:
        return np.asarray([self.index(x) for x in self.sires])

    def dam_array(self) -> np.ndarray:
        return np.asarray([self.index(x) for x in self.dams])

    def to_dict(self) -> dict[str, list[str]]:
        out = defaultdict(list)
        for child, sire, dam in zip(self.names, self.sires, self.dams, strict=False):
            if sire is not None:
                out[child].append(sire)
            if dam is not None:
                out[child].append(dam)
        return dict(out)

    def get_inbreeding(self) -> np.ndarray:
        return inbreeding_coeffs(self.sire_array(), self.dam_array())

    def get_kinship(self) -> np.ndarray:
        return kinship_coeffs(self.sire_array(), self.dam_array())


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
        Array of inbreeding coefficients (1-indexed)

    Notes:
    ------
    - Animals must be sorted so that parents appear before offspring
    - First element of the returned array should be ignored
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

    # Return inbreeding coefficients (leaving placeholder so that indices will work)
    return F


def kinship_coeffs(sire_ids: npt.ArrayLike, dam_ids: npt.ArrayLike) -> np.ndarray:
    """Calculate the full kinship array for the pedigree.

    Parameters:
    -----------
    sire_ids : array-like
        Array of sire IDs (1-indexed, 0 for missing)
    dam_ids : array-like
        Array of dam IDs (1-indexed, 0 for missing)

    Returns:
    --------
    numpy.ndarray
        2D Array of inbreeding coefficients (1-indexed)

    Notes:
    ------
    - Animals must be sorted so that parents appear before offspring
    - First row and column of the returned array should be ignored
    """
    sire_ids = np.asarray(sire_ids, dtype=np.int32)
    dam_ids = np.asarray(dam_ids, dtype=np.int32)

    # calculate inbreeding coefficients first
    F = inbreeding_coeffs(sire_ids, dam_ids)

    # initialize kinship array with inbreeding along the diagonal
    K = np.diag(0.5 * (1 + F))

    # Fill off-diagonal elements directly
    # Kinship K[i,j] = 0.5 * (K[sire_i, j] + K[dam_i, j])
    for i, (sire, dam) in enumerate(zip(sire_ids, dam_ids, strict=False), start=1):
        for j in range(1, i):  # Only fill lower triangle, then copy
            # This works for all cases because K[0, j] = 0 for missing parents
            K[i, j] = 0.5 * (K[sire, j] + K[dam, j])
            # Copy to upper triangle (symmetric matrix)
            K[j, i] = K[i, j]

    return K


def kinship_by_path(pedigree: dict[str, list[str]], targets: list[str]):
    """Calculate kinship coefficients between target animals from the relevant
    pedigree relationships using Malecot's path method.

    Args:
        pedigree: a {child: [parents]} dict containing the target animals and at least all their ancestors
        targets: List of target animals to calculate coefficients for

    Returns:
        Dict mapping (animal1, animal2) -> relatedness_coefficient

    Notes:
        Strings should all be unique names for the animals
    """
    ancestors = {target: find_ancestors(pedigree, target) for target in targets}

    # Calculate relatedness for all pairs
    results = {}
    for i, animal1 in enumerate(targets):
        for j, animal2 in enumerate(targets):
            if i <= j:  # Only calculate upper triangle + diagonal
                if animal1 == animal2:
                    coefficient = 0.5
                else:
                    coefficient = kinship_from_ancestors(
                        ancestors[animal1], ancestors[animal2]
                    )
                results[(animal1, animal2)] = coefficient
                results[(animal2, animal1)] = coefficient

    return results


def find_ancestors(pedigree: dict[str, list[str]], target):
    """Find all ancestors of target with their minimum distances"""
    ancestors = {}
    queue = deque([(target, 0)])
    visited = {target}

    while queue:
        child, distance = queue.popleft()

        # Add current animal as ancestor (except for the starting animal)
        # if distance > 0:
        if child not in ancestors:
            ancestors[child] = distance
        else:
            # Keep minimum distance if we've seen this ancestor before
            ancestors[child] = min(ancestors[child], distance)

        # Add parents to queue
        for parent in pedigree.get(child, []):
            if parent not in visited:
                queue.append((parent, distance + 1))
            visited.add(parent)
    return ancestors


def kinship_from_ancestors(
    ancestors1: dict[str, int], ancestors2: dict[str, int]
) -> float:
    """
    Calculate Malecot's kinship coefficient from ancestor distance dictionaries.

    Formula: Σ(0.5^(n1+n2+1)) for all common ancestors
    where n1, n2 are distances from each animal to the common ancestor
    """
    relatedness = 0.0
    common_ancestors = set(ancestors1.keys()) & set(ancestors2.keys())

    for ancestor_uuid in common_ancestors:
        dist1 = ancestors1[ancestor_uuid]
        dist2 = ancestors2[ancestor_uuid]
        relatedness += 0.5 ** (dist1 + dist2 + 1)

    return relatedness
