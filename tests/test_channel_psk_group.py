"""Canal PSK groupe : 3 identités avec le même secret déchiffrent ; outsider non."""

from pathlib import Path

import pytest

from airnet.crypto.channel import (
    ChannelStore,
    derive_channel_key,
    open_channel,
    seal_channel,
)
from airnet.crypto.keys import generate_or_load_identity
from airnet.transport.framing import CHANNEL_MSG, build_channel, parse_frame


def test_channel_psk_group(tmp_path: Path):
    secret = b"cle-propre-a-eux-groupe-airnet!!"  # 32-ish passphrase as bytes
    # three local stores join same name+secret
    stores = []
    metas = []
    for name in ("alice", "bob", "carol"):
        store = ChannelStore(tmp_path / f"ch_{name}")
        meta = store.join("soirée", secret, channel_type="group")
        stores.append(store)
        metas.append(meta)

    assert metas[0].channel_id == metas[1].channel_id == metas[2].channel_id

    # outsider with wrong secret
    outsider = ChannelStore(tmp_path / "ch_eve")
    eve_meta = outsider.join("soirée", b"mauvais-secret-eve-xxxxxx", channel_type="group")
    # different secret → different channel_id
    assert eve_meta.channel_id != metas[0].channel_id

    plaintext = b"bonjour le groupe mesh"
    blob = stores[0].encrypt(metas[0], plaintext)

    for store, meta in zip(stores, metas):
        assert store.decrypt(meta, blob) == plaintext

    # outsider cannot decrypt even if they somehow get the blob with right id
    # (they don't have the secret for that id)
    with pytest.raises((ValueError, FileNotFoundError)):
        outsider.decrypt_by_id(metas[0].id_bytes, blob)

    # wrong key explicitly
    wrong_key = derive_channel_key(b"mauvais-secret-eve-xxxxxx", metas[0].id_bytes)
    with pytest.raises(ValueError):
        open_channel(blob, wrong_key, metas[0].id_bytes)


def test_channel_framing_roundtrip(tmp_path: Path):
    store = ChannelStore(tmp_path / "ch")
    meta, _ = store.create("labo", b"secret-labo-32-octets-airnet!!", channel_type="pair")
    blob = store.encrypt(meta, b"ping")
    raw = build_channel(meta.id_bytes, blob)
    frame = parse_frame(raw)
    assert frame.msg_type == CHANNEL_MSG
    assert frame.is_channel
    assert frame.channel_id == meta.id_bytes
    assert store.decrypt(meta, frame.channel_blob) == b"ping"


def test_channel_seal_open_direct():
    secret = b"x" * 32
    from airnet.crypto.channel import channel_id_from_name_secret

    cid = channel_id_from_name_secret("duo", secret)
    key = derive_channel_key(secret, cid)
    blob = seal_channel(b"hi", key, cid)
    assert open_channel(blob, key, cid) == b"hi"


def test_secret_file_mode(tmp_path: Path):
    store = ChannelStore(tmp_path / "ch")
    meta, _ = store.create("m", b"s" * 32)
    sp = store._secret_path(meta.channel_id)
    mode = sp.stat().st_mode & 0o777
    assert mode == 0o600 or mode == 0o644  # some fs ignore chmod
