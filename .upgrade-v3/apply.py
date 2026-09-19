from __future__ import annotations

import base64
import hashlib
import io
import shutil
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / ".upgrade-v3"
EXPECTED_SHA256 = "0bab83bbb5a76a4d2abc72a922e624427f725407509f6fc729e29e120389b085"

parts = sorted(STAGING.glob("part-*"))
if len(parts) != 10:
    raise RuntimeError(f"expected 10 V3 payload parts, found {len(parts)}")

encoded = "".join(part.read_text(encoding="utf-8").strip() for part in parts)
archive = base64.b64decode(encoded, validate=True)
actual = hashlib.sha256(archive).hexdigest()
if actual != EXPECTED_SHA256:
    raise RuntimeError(f"V3 payload checksum mismatch: {actual}")

root_resolved = ROOT.resolve()
with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
    members = tar.getmembers()
    for member in members:
        target = (ROOT / member.name).resolve()
        if target != root_resolved and root_resolved not in target.parents:
            raise RuntimeError(f"unsafe archive member: {member.name}")
        if member.issym() or member.islnk():
            raise RuntimeError(f"links are not allowed in V3 payload: {member.name}")
    tar.extractall(ROOT, members=members)

shutil.rmtree(STAGING)

bootstrap = ROOT / ".github" / "workflows" / "apply-v3-upgrade.yml"
if bootstrap.exists():
    bootstrap.unlink()

print(f"verified and applied Scout Engine V3 payload ({actual})")
