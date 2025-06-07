# -*- mode: python -*-
"""Functions for computing inbreeding and relatedness coefficients"""
from typing import Optional, Tuple, List

from django.db.models import F, Q, OuterRef, Subquery, Window, Count
from django.db.models.functions import RowNumber
import numpy as np
import numpy.typing as npt

from birds.models import Animal

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
    missing_parent : int
        Value indicating missing parent (default: -1)
        
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
        sire_idx = sire_ids[i-1]
        dam_idx = dam_ids[i-1]
        LAP[i] = max(LAP[sire_idx], LAP[dam_idx]) + 1
        if LAP[i] > max_lap:
            max_lap = LAP[i]
    
    # Initialize start and minor indices for each LAP level  
    SI = np.zeros(max_lap + 1, dtype=np.int32)  # Start index for each level
    MI = np.zeros(max_lap + 1, dtype=np.int32)  # Minor index for each level
    
    # Process each animal
    for i in range(1, n + 1):
        sire_idx = sire_ids[i-1]
        dam_idx = dam_ids[i-1]
        
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
        if (i > 1 and sire_idx == sire_ids[i-2] and dam_idx == dam_ids[i-2]):
            F[i] = F[i-1]
            L[i] = L[i-1]
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
            S_anc = sire_ids[j-1] if j <= n else 0
            D_anc = dam_ids[j-1] if j <= n else 0
            
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

def get_pedigree():
    """Retrieves a sorted pedigree from the database"""
    qs = Animal.objects.annotate(
        sire=Subquery(Animal.objects.filter(children=OuterRef("uuid"), sex="M").values("uuid")[:1]),
        dam=Subquery(Animal.objects.filter(children=OuterRef("uuid"), sex="F").values("uuid")[:1]),
        idx=Window(expression=RowNumber(), order_by=['created', 'uuid']),
    )
    return tuple(qs.order_by("idx").values("idx", "uuid", "sire", "dam"))


def calculate_inbreeding(sire_ids, dam_ids, missing_parent=-1):
    """
    Calculate inbreeding coefficients using the Meuwissen and Luo algorithm.

    Parameters:
    -----------
    sire_ids : array-like
        Array of sire IDs (0-indexed, negative for missing)
    dam_ids : array-like  
        Array of dam IDs (0-indexed, negative for missing)
        
    Returns:
    --------
    numpy.ndarray
        Array of inbreeding coefficients

    Notes:
    ------
    - Animals must be sorted so that parents appear before offspring
    - Animal IDs should be 0-based indices (0, 1, 2, ..., n-1)
    - Use negative values for unknown parents    
    """
    n = len(sire_ids)
    sire_ids = np.asarray(sire_ids, dtype=np.int32)
    dam_ids = np.asarray(dam_ids, dtype=np.int32)
    
    F = np.zeros(n + 1, dtype=np.float64)  # inbreeding coefficients
    L = np.zeros(n, dtype=np.float64)  # working array
    D = np.zeros(n, dtype=np.float64)  # diagonal of inverse relationship matrix
    
    for i in range(n):
        # Calculate diagonal element
        sire_id = sire_ids[i]
        dam_id = dam_ids[i]
        sire_f = F[sire_id] if sire_id >= 0 else -1.0
        dam_f = F[dam_id] if dam_id >= 0 else -1.0
        D[i] = 0.5 - 0.25 * (sire_f + dam_f)
        
        # Check for full sibs
        if (i > 0 and sire_id == sire_ids[i-1] and dam_id == dam_ids[i-1]):
            F[i] = F[i-1]
            continue
            
        # Initialize
        L.fill(0.0)
        L[i] = 1.0
        F[i] = -1.0
        
        # Ancestor list (using list for simplicity in basic version)
        ancestors = [i]
        
        while ancestors:
            # Find oldest ancestor
            j = max(ancestors)
            ancestors.remove(j)
            
            # Add parents if they exist
            if sire_ids[j] != missing_parent:
                if L[sire_ids[j]] == 0.0:
                    ancestors.append(sire_ids[j])
                L[sire_ids[j]] += 0.5 * L[j]
                
            if dam_ids[j] != missing_parent:
                if L[dam_ids[j]] == 0.0:
                    ancestors.append(dam_ids[j])
                L[dam_ids[j]] += 0.5 * L[j]
            
            # Accumulate coefficient
            F[i] += L[j] * L[j] * D[j]
    
    return F

def calculate_inbreeding_coefficients(
    dam: np.ndarray, 
    sire: np.ndarray, 
    f: Optional[np.ndarray] = None,
    missing_parent_id: int = -1
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate inbreeding coefficients using the Meuwissen and Luo algorithm.
    
    Parameters:
    -----------
    dam : np.ndarray
        Array of dam (mother) IDs for each animal. Use missing_parent_id for unknown dams.
    sire : np.ndarray  
        Array of sire (father) IDs for each animal. Use missing_parent_id for unknown sires.
    f : np.ndarray, optional
        Pre-calculated inbreeding coefficients. If None, will be calculated.
    missing_parent_id : int, default -1
        ID used to represent missing/unknown parents
        
    Returns:
    --------
    Tuple[np.ndarray, np.ndarray]
        f: inbreeding coefficients for each animal
        dii: diagonal elements of the inverse additive relationship matrix
        
    Notes:
    ------
    - Animals must be sorted so that parents appear before offspring
    - Animal IDs should be 0-based indices (0, 1, 2, ..., n-1)
    - Use missing_parent_id (default -1) for unknown parents
    """
    n = len(dam)
    
    # Validate inputs
    if len(sire) != n:
        raise ValueError("dam and sire arrays must have the same length")
    
    # Initialize arrays
    if f is None:
        f = np.zeros(n, dtype=np.float64)
        calculate_f = True
    else:
        if len(f) != n:
            raise ValueError("f array must have the same length as dam and sire")
        calculate_f = False
        
    dii = np.zeros(n, dtype=np.float64)
    
    if calculate_f:
        # Working arrays for the algorithm
        AN = np.full(2 * n, -1, dtype=np.int32)  # Ancestor list
        li = np.zeros(n, dtype=np.float64)       # L matrix diagonal
        
        for k in range(n):
            # Calculate diagonal element of inverse relationship matrix
            dam_f = f[dam[k]] if dam[k] != missing_parent_id and dam[k] >= 0 else 0.0
            sire_f = f[sire[k]] if sire[k] != missing_parent_id and sire[k] >= 0 else 0.0
            dii[k] = 0.5 - 0.25 * (dam_f + sire_f)
            
            # Check if this animal has the same parents as the previous one
            if (k > 0 and 
                dam[k] == dam[k-1] and 
                sire[k] == sire[k-1] and
                dam[k] != missing_parent_id and 
                sire[k] != missing_parent_id):
                # Same parents as previous animal - copy inbreeding coefficient
                f[k] = f[k-1]
            else:
                # Calculate inbreeding coefficient from scratch
                li[k] = 1.0  # Set l_kk to 1
                ai = 0.0     # Initialize diagonal element
                j = k
                cnt = 0
                
                # Reset ancestor list
                AN.fill(-1)
                
                while j >= 0:
                    sj = sire[j] if sire[j] != missing_parent_id else -1
                    dj = dam[j] if dam[j] != missing_parent_id else -1
                    
                    # Add sire to ancestor list if known
                    if sj >= 0:
                        AN[cnt] = sj
                        li[sj] += 0.5 * li[j]
                        cnt += 1
                        
                    # Add dam to ancestor list if known  
                    if dj >= 0:
                        AN[cnt] = dj
                        li[dj] += 0.5 * li[j]
                        cnt += 1
                    
                    # Update diagonal element
                    ai += li[j] * li[j] * dii[j]
                    
                    # Find the eldest (highest ID) individual in ancestor list
                    j = -1
                    for h in range(cnt):
                        if AN[h] > j:
                            j = AN[h]
                    
                    # Mark duplicates for deletion by subtracting n
                    for h in range(cnt):
                        if AN[h] == j:
                            AN[h] -= n
                
                # Set inbreeding coefficient
                f[k] = ai - 1.0
                
                # Reset li array for next iteration
                li.fill(0.0)
    else:
        # Only calculate dii when f is provided
        for k in range(n):
            dam_f = f[dam[k]] if dam[k] != missing_parent_id and dam[k] >= 0 else 0.0
            sire_f = f[sire[k]] if sire[k] != missing_parent_id and sire[k] >= 0 else 0.0
            dii[k] = 0.5 - 0.25 * (dam_f + sire_f)
    
    return f, dii


def calculate_inbreeding_coefficients(sire_idx: List[int], dam_idx: List[int], n: int) -> Tuple[List[float], List[float]]:
    """
    Calculate inbreeding coefficients using Meuwissen & Luo algorithm.
    
    Args:
        sire_idx: List of sire indices (-1 for unknown)
        dam_idx: List of dam indices (-1 for unknown)  
        n: Number of individuals

    The indices and arrays need to be sorted such that ancestors precede descendents.
    
    Returns:
        Tuple of (inbreeding_coefficients, diagonal_elements)
    """
    
    f = [0.0] * n  # Inbreeding coefficients
    dii = [0.0] * n  # Diagonal elements
    li = [0.0] * n  # Working array for L matrix elements
    
    for k in range(n):
        # Calculate diagonal element
        sire_f = f[sire_idx[k]] if sire_idx[k] != -1 else 0.0
        dam_f = f[dam_idx[k]] if dam_idx[k] != -1 else 0.0
        dii[k] = 0.5 - 0.25 * (sire_f + dam_f)
        
        # Check if same parents as previous individual (optimization)
        if (k > 0 and 
            sire_idx[k] == sire_idx[k-1] and 
            dam_idx[k] == dam_idx[k-1]):
            f[k] = f[k-1]
            continue
        
        # Calculate inbreeding coefficient
        li[k] = 1.0
        ai = 0.0
        ancestors = []
        
        # Trace back through ancestors
        j = k
        while j >= 0:
            sj = sire_idx[j]
            dj = dam_idx[j]
            
            # Add contributions from parents
            if sj != -1:
                li[sj] += 0.5 * li[j]
                ancestors.append(sj)
            if dj != -1:
                li[dj] += 0.5 * li[j]
                ancestors.append(dj)
            
            # Accumulate diagonal contribution
            ai += li[j] * li[j] * dii[j]
            
            # Find next ancestor to process (highest index)
            next_j = -1
            for idx, anc in enumerate(ancestors):
                if anc > next_j:
                    next_j = anc
            
            # Remove processed ancestor
            ancestors = [anc for anc in ancestors if anc != next_j]
            j = next_j
        
        f[k] = ai - 1.0
        
        # Reset working array
        for h in range(k + 1):
            li[h] = 0.0
    
    return f, dii
