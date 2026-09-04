"""Tests des constantes d'identité projet."""

from airnet import AUTHOR, NAME, ORGS, URLS, VERSION
from airnet import identity as ident


def test_name():
    assert NAME == "AirNet PCTamalou"
    assert ident.NAME == NAME


def test_version_trust():
    assert VERSION == "0.4.0-trust"
    assert "trust" in VERSION


def test_author():
    assert "Platon-Y" in AUTHOR
    assert "Jonathan Ducros" in AUTHOR


def test_orgs_and_urls():
    assert "PCTamalou" in ORGS
    assert "Echoes of Hackers" in ORGS
    assert "https://pctamalou.fr" in URLS
    assert "https://e-of-h.fr" in URLS


def test_contacts():
    assert "admin@pctamalou.fr" in ident.CONTACTS
    assert "admin@e-of-h.fr" in ident.CONTACTS
