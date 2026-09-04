"""Limites radio légales FR/UE pour AirNet.

Ne jamais suggérer ``iw reg set BO`` ni tout autre contournement de domaine
réglementaire. La puissance TX max acceptée par ce package est 20 dBm.
"""

from __future__ import annotations

MAX_TXPOWER_DBM = 20


class IllegalTxPowerError(ValueError):
    """Puissance TX demandée supérieure à la limite légale du package."""


def assert_legal_txpower(dbm: int | float) -> int:
    """Refuse toute puissance > ``MAX_TXPOWER_DBM``.

    Returns
    -------
    int
        Valeur entière validée (≤ 20).
    """
    value = int(dbm)
    if value > MAX_TXPOWER_DBM:
        raise IllegalTxPowerError(
            f"txpower {value} dBm refusé : maximum autorisé par AirNet = "
            f"{MAX_TXPOWER_DBM} dBm (cadre FR/UE). Ne change pas le domaine "
            f"réglementaire pour contourner cette limite."
        )
    if value < 0:
        raise IllegalTxPowerError(f"txpower invalide: {value}")
    return value
