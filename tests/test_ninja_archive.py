"""ninja_archive decodes poe.ninja's protobuf answers without a schema (no network here)."""
import gzip
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine" / "tools"))
import ninja_archive as na  # noqa: E402


def _v(n):
    out = b""
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out += bytes([b | 0x80])
        else:
            return out + bytes([b])


def _f(field, val):
    if isinstance(val, int):
        return _v(field << 3) + _v(val)
    if isinstance(val, str):
        val = val.encode()
    return _v(field << 3 | 2) + _v(len(val)) + val


def test_decode_search_and_dictionary():
    entry0 = _f(2, 300)                    # index 0 is left out (protobuf default)
    entry2 = _f(1, 2) + _f(2, 100)
    dim = _f(1, "skills") + _f(2, "gem") + _f(3, entry0) + _f(3, entry2)
    body = _f(1, 1000) + _f(2, dim) + _f(6, _f(1, "gem") + _f(2, "abc"))
    total, dims, refs = na.decode_search(gzip.compress(_f(1, body)))
    assert total == 1000
    assert dims["skills"] == ("gem", {0: 300, 2: 100})
    assert refs == {"gem": "abc"}
    kind, names = na.decode_dictionary(_f(1, "gem") + _f(2, "Comet") + _f(2, "Spark") + _f(2, "Twister"))
    assert kind == "gem" and names == ["Comet", "Spark", "Twister"]
