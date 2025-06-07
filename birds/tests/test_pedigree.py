# -*- mode: python -*-
import numpy as np
from numpy.testing import assert_allclose

from birds import pedigree


def test_inbreeding_mrode_2005():
    sires = np.asarray([0, 0, 1, 1, 4, 5])
    dams = np.asarray([0, 0, 2, 0, 3, 2])
    F = pedigree.inbreeding_coeffs(sires, dams)
    assert_allclose(F, [0.0, 0.0, 0.0, 0.0, 0.125, 0.125])


def test_inbreeding_inbred_common_ancestor():
    # from https://genetic-genealogy.co.uk/Toc115570144.html, figure 64
    names = "ABCDEFGHIJKLMNOPQR"
    sire_names = [
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
    ]
    dam_names = [
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
    ]
    sires = np.asarray([names.find(x) + 1 if x is not None else 0 for x in sire_names])
    dams = np.asarray([names.find(x) + 1 if x is not None else 0 for x in dam_names])
    assert (
        len(
            {sire for sire in sire_names if sire is not None}
            & {dam for dam in dam_names if dam is not None}
        )
        == 0
    ), "sires and dams are not disjoint"
    F = pedigree.inbreeding_coeffs(sires, dams)
    assert_allclose(F[names.find("I")], 0.0625)
    assert_allclose(F[names.find("Q")], 0.06445, rtol=1e-4)


def test_inbreeding_without_inbred_common_ancestor():
    # from https://genetic-genealogy.co.uk/Toc115570144.html, figure 65
    names = "ABCDEFGHIJKLMNO"
    sire_names = [
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
    ]
    dam_names = [
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
    ]
    sires = np.asarray([names.find(x) + 1 if x is not None else 0 for x in sire_names])
    dams = np.asarray([names.find(x) + 1 if x is not None else 0 for x in dam_names])
    assert (
        len(
            {sire for sire in sire_names if sire is not None}
            & {dam for dam in dam_names if dam is not None}
        )
        == 0
    ), "sires and dams are not disjoint"
    F = pedigree.inbreeding_coeffs(sires, dams)
    assert_allclose(F[names.find("O")], 0.0703125)


def test_inbreeding_closely_inbred():
    # from https://genetic-genealogy.co.uk/Toc115570144.html, figure 66
    names = "ABCDEFGHI"
    sire_names = [None, None, "A", "A", "C", "C", "E", "E", "G"]
    dam_names = [None, None, "B", "B", "D", "D", "F", "F", "H"]
    sires = np.asarray([names.find(x) + 1 if x is not None else 0 for x in sire_names])
    dams = np.asarray([names.find(x) + 1 if x is not None else 0 for x in dam_names])
    assert (
        len(
            {sire for sire in sire_names if sire is not None}
            & {dam for dam in dam_names if dam is not None}
        )
        == 0
    ), "sires and dams are not disjoint"
    F = pedigree.inbreeding_coeffs(sires, dams)
    assert_allclose(F[names.find("E")], 0.25)
    assert_allclose(F[names.find("I")], 0.50)


def test_inbreeding_18th_dynasty():
    # from https://genetic-genealogy.co.uk/Toc115570144.html, figure 67
    names = [
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
    ]
    sire_names = [
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
    ]
    dam_names = [
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
    ]
    sires = np.asarray([names.index(x) + 1 if x is not None else 0 for x in sire_names])
    dams = np.asarray([names.index(x) + 1 if x is not None else 0 for x in dam_names])
    assert (
        len(
            {sire for sire in sire_names if sire is not None}
            & {dam for dam in dam_names if dam is not None}
        )
        == 0
    ), "sires and dams are not disjoint"
    F = pedigree.inbreeding_coeffs(sires, dams)
    assert_allclose(F, [0.0, 0.0, 0.0, 0.0, 0.0, 0.25, 0.25, 0.0, 0.375, 0.25])


def test_inbreeding_double_grandchildren():
    # from https://genetic-genealogy.co.uk/Toc115570144.html, figure 69
    names = "ABCDEFGH"
    sire_names = [None, None, "A", "A", "C", None, "E", "E"]
    dam_names = [None, None, "B", "B", "D", None, "F", "G"]
    sires = np.asarray([names.find(x) + 1 if x is not None else 0 for x in sire_names])
    dams = np.asarray([names.find(x) + 1 if x is not None else 0 for x in dam_names])
    assert (
        len(
            {sire for sire in sire_names if sire is not None}
            & {dam for dam in dam_names if dam is not None}
        )
        == 0
    ), "sires and dams are not disjoint"
    F = pedigree.inbreeding_coeffs(sires, dams)
    assert_allclose(F[-1], 0.3125)


def test_inbreeding_direct_collateral():
    # from https://genetic-genealogy.co.uk/Toc115570144.html, figure 70
    names = "ABCDEFGHIJKLMNO"
    sire_names = [
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
    ]
    dam_names = [
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
    ]
    sires = np.asarray([names.find(x) + 1 if x is not None else 0 for x in sire_names])
    dams = np.asarray([names.find(x) + 1 if x is not None else 0 for x in dam_names])
    assert (
        len(
            {sire for sire in sire_names if sire is not None}
            & {dam for dam in dam_names if dam is not None}
        )
        == 0
    ), "sires and dams are not disjoint"
    F = pedigree.inbreeding_coeffs(sires, dams)
    assert_allclose(F[names.find("B")], 0.0)
    assert_allclose(F[names.find("J")], 0.125)
    assert_allclose(F[names.find("L")], 0.03125)
    assert_allclose(F[names.find("O")], 0.33203125)
