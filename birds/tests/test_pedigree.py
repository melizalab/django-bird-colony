# -*- mode: python -*-
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.testing import assert_allclose

from birds import pedigree


@dataclass
class Pedigree:
    names: Sequence[str]
    sires: Sequence[str | None]
    dams: Sequence[str | None]

    def __post_init__(self):
        sire_set = {sire for sire in self.sires if sire is not None}
        dam_set = {dam for dam in self.dams if dam is not None}
        assert sire_set.isdisjoint(dam_set), "sires and dams are not disjoint"

    def idx(self, name):
        return self.names.index(name) + 1 if name is not None else 0

    def sire_idx(self):
        return np.asarray([self.idx(x) for x in self.sires])

    def dam_idx(self):
        return np.asarray([self.idx(x) for x in self.dams])

    def to_dict(self):
        out = defaultdict(list)
        for child, sire, dam in zip(self.names, self.sires, self.dams, strict=False):
            if sire is not None:
                out[child].append(sire)
            if dam is not None:
                out[child].append(dam)
        return dict(out)


# from https://genetic-genealogy.co.uk/Toc115570144.html, figure 64
inbred_common_ancestor = Pedigree(
    list("ABCDEFGHIJKLMNOPQR"),
    [
        None,
        None,
        None,
        "A",
        "A",
        None,
        "C",
        "E",
        "G",
        None,
        None,
        "I",
        "I",
        None,
        "K",
        "M",
        "O",
        "O",
    ],
    [
        None,
        None,
        None,
        "B",
        "B",
        None,
        "D",
        "F",
        "H",
        None,
        None,
        "J",
        "J",
        None,
        "L",
        "N",
        "P",
        "P",
    ],
)

# from https://genetic-genealogy.co.uk/Toc115570144.html, figure 65
no_inbred_common_ancestor = Pedigree(
    list("ABCDEFGHIJKLMNO"),
    [
        None,
        None,
        None,
        "A",
        "A",
        None,
        "C",
        "E",
        None,
        "G",
        "G",
        None,
        None,
        "K",
        "M",
    ],
    [
        None,
        None,
        None,
        "B",
        "B",
        None,
        "D",
        "F",
        None,
        "H",
        "H",
        None,
        "J",
        "L",
        "N",
    ],
)

# from https://genetic-genealogy.co.uk/Toc115570144.html, figure 66
closely_inbred = Pedigree(
    list("ABCDEFGHI"),
    [None, None, "A", "A", "C", "C", "E", "E", "G"],
    [None, None, "B", "B", "D", "D", "F", "F", "H"],
)


# from https://genetic-genealogy.co.uk/Toc115570144.html, figure 67
ped_18th_dynasty = Pedigree(
    [
        "Sequenenra III",
        "Aahotep I",
        "Aahmes",
        "Aahmes-Nefertari",
        "Senseneb",
        "Amenhotep I",
        "Aahotep II",
        "Thotmes I",
        "Aames",
        "Hatsheput",
    ],
    [
        None,
        None,
        "Sequenenra III",
        "Sequenenra III",
        None,
        "Aahmes",
        "Aahmes",
        "Amenhotep I",
        "Amenhotep I",
        "Thotmes I",
    ],
    [
        None,
        None,
        "Aahotep I",
        "Aahotep I",
        None,
        "Aahmes-Nefertari",
        "Aahmes-Nefertari",
        "Senseneb",
        "Aahotep II",
        "Aames",
    ],
)


# from https://genetic-genealogy.co.uk/Toc115570144.html, figure 69
double_grandchildren = Pedigree(
    list("ABCDEFGH"),
    [None, None, "A", "A", "C", None, "E", "E"],
    [None, None, "B", "B", "D", None, "F", "G"],
)


# from https://genetic-genealogy.co.uk/Toc115570144.html, figure 70
direct_collateral = Pedigree(
    list("ABCDEFGHIJKLMNO"),
    [
        None,
        None,
        None,
        None,
        None,
        "A",
        "C",
        "C",
        "E",
        "G",
        None,
        "J",
        "J",
        "L",
        "L",
    ],
    [
        None,
        None,
        None,
        None,
        None,
        "B",
        "B",
        "D",
        "F",
        "H",
        None,
        "I",
        "K",
        "M",
        "N",
    ],
)


def test_pedigree_to_dict():
    ped = closely_inbred.to_dict()
    assert ped["I"] == ["G", "H"]
    assert ped["E"] == ["C", "D"]


def test_inbreeding_mrode_2005():
    sires = np.asarray([0, 0, 1, 1, 4, 5])
    dams = np.asarray([0, 0, 2, 0, 3, 2])
    F = pedigree.inbreeding_coeffs(sires, dams)
    assert_allclose(F[1:], [0.0, 0.0, 0.0, 0.0, 0.125, 0.125])


def test_inbreeding_inbred_common_ancestor():
    ped = inbred_common_ancestor
    F = pedigree.inbreeding_coeffs(ped.sire_idx(), ped.dam_idx())
    assert_allclose(F[ped.idx("I")], 0.0625)
    assert_allclose(F[ped.idx("Q")], 0.06445, rtol=1e-4)


def test_kinship_inbred_common_ancestor():
    ped = inbred_common_ancestor.to_dict()
    rel = pedigree.kinship(ped, ["A", "D", "E", "G", "H", "O", "P"])
    # self
    assert rel[("A", "A")] == 0.5
    # child
    assert rel[("A", "D")] == 0.25
    # siblings
    assert rel[("D", "E")] == 0.25
    # uncle
    assert rel[("G", "E")] == 0.125
    # cousins
    assert rel[("G", "H")] == 0.0625
    # should be same as inbreeding coefficient for Q, but it will fail if the
    # algorithm counts paths through through ancestors of common ancestors
    assert rel[("O", "P")] == 0.06445


def test_inbreeding_without_inbred_common_ancestor():
    ped = no_inbred_common_ancestor
    F = pedigree.inbreeding_coeffs(ped.sire_idx(), ped.dam_idx())
    assert_allclose(F[ped.idx("O")], 0.0703125)


def test_inbreeding_closely_inbred():
    ped = closely_inbred
    F = pedigree.inbreeding_coeffs(ped.sire_idx(), ped.dam_idx())
    assert_allclose(F[ped.idx("E")], 0.25)
    assert_allclose(F[ped.idx("I")], 0.50)


def test_inbreeding_18th_dynasty():
    ped = ped_18th_dynasty
    F = pedigree.inbreeding_coeffs(ped.sire_idx(), ped.dam_idx())
    assert_allclose(F[1:], [0.0, 0.0, 0.0, 0.0, 0.0, 0.25, 0.25, 0.0, 0.375, 0.25])


def test_inbreeding_double_grandchildren():
    ped = double_grandchildren
    F = pedigree.inbreeding_coeffs(ped.sire_idx(), ped.dam_idx())
    assert_allclose(F[-1], 0.3125)


def test_inbreeding_direct_collateral():
    ped = direct_collateral
    F = pedigree.inbreeding_coeffs(ped.sire_idx(), ped.dam_idx())
    assert_allclose(F[ped.idx("B")], 0.0)
    assert_allclose(F[ped.idx("J")], 0.125)
    assert_allclose(F[ped.idx("L")], 0.03125)
    assert_allclose(F[ped.idx("O")], 0.33203125)
