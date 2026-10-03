# Changelog: 2026-10-04 | Antigravity (Claude Opus 5.5) | Tạo mới — tách GGUF gemma4 gộp (text+vision+audio) thành bản chỉ-text cho llama.cpp upstream
"""Đọc GGUF gốc (KHÔNG sửa), ghi file mới chỉ gồm tensor text (bỏ tiền tố a./v./mm.) + toàn bộ metadata.
Dùng: python scripts/acc/strip_gguf_text.py <in.gguf> <out.gguf>
Lý do: llama.cpp 836d571 nạp gemma4 text-only -> 'wrong number of tensors; expected 2131, got 720'."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
from gguf import GGUFReader, GGUFValueType, GGUFWriter

DROP_PREFIXES = ("a.", "v.", "mm.")


def _value(field):
    t = field.types[0]
    if t == GGUFValueType.ARRAY:
        sub = field.types[-1]
        if sub == GGUFValueType.STRING:
            return [bytes(field.parts[i]).decode("utf-8") for i in field.data], sub
        return [field.parts[i].tolist()[0] for i in field.data], sub
    if t == GGUFValueType.STRING:
        return bytes(field.parts[field.data[0]]).decode("utf-8"), None
    return field.parts[field.data[0]].tolist()[0], None


def main(src: str, dst: str) -> int:
    src_p, dst_p = Path(src), Path(dst)
    if dst_p.exists():
        raise SystemExit(f"Từ chối ghi đè: {dst_p} đã tồn tại")
    r = GGUFReader(src_p)
    arch = _value(r.fields["general.architecture"])[0]
    w = GGUFWriter(dst_p, arch)
    for name, field in r.fields.items():
        if name.startswith("GGUF.") or name == "general.architecture":
            continue
        val, sub = _value(field)
        w.add_key_value(name, val, field.types[0], sub_type=sub)
    kept = [t for t in r.tensors if not t.name.startswith(DROP_PREFIXES)]
    dropped = len(r.tensors) - len(kept)
    for t in kept:
        w.add_tensor_info(t.name, t.data.shape, t.data.dtype, t.data.nbytes, raw_dtype=t.tensor_type)
    w.write_header_to_file()
    w.write_kv_data_to_file()
    w.write_ti_data_to_file()
    for t in kept:
        w.write_tensor_data(t.data)
    w.close()
    print(f"kept={len(kept)} dropped={dropped} out={dst_p} bytes={dst_p.stat().st_size}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
