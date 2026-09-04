"""Tests mesh en dry_run (pas de root / pas de hardware)."""

import pytest

from airnet.mesh.legal import MAX_TXPOWER_DBM, IllegalTxPowerError, assert_legal_txpower
from airnet.mesh.setup import setup_ibss_batman


def test_max_txpower_constant():
    assert MAX_TXPOWER_DBM == 20


def test_assert_legal_ok():
    assert assert_legal_txpower(20) == 20
    assert assert_legal_txpower(10) == 10


def test_assert_legal_refuse_high():
    with pytest.raises(IllegalTxPowerError):
        assert_legal_txpower(21)
    with pytest.raises(IllegalTxPowerError):
        assert_legal_txpower(30)


def test_setup_dry_run_returns_steps():
    result = setup_ibss_batman(dry_run=True, ip_cidr="10.13.37.42/24")
    assert result["dry_run"] is True
    assert result["iface"] == "wlan0"
    assert result["bat_iface"] == "bat0"
    assert result["ip_cidr"] == "10.13.37.42/24"
    assert result["ssid"] == "AirNetPCTamalou"
    assert isinstance(result["steps"], list)
    assert len(result["steps"]) >= 5
    joined = "\n".join(result["steps"])
    assert "batman-adv" in joined
    assert "ibss" in joined
    assert "batctl" in joined
    # jamais de suggestion BO
    assert "reg set BO" not in joined
    assert " iw reg " not in joined


def test_setup_dry_run_txpower_legal():
    result = setup_ibss_batman(dry_run=True, txpower_dbm=20)
    assert any("txpower" in s for s in result["steps"])


def test_setup_dry_run_txpower_illegal():
    with pytest.raises(IllegalTxPowerError):
        setup_ibss_batman(dry_run=True, txpower_dbm=30)
