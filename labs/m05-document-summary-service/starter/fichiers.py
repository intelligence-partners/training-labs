# fichiers.py
# Step 3: upload each PDF once. The local index maps the SHA-256 of the PDF to its file_id,
# so the same file keeps the same file_id, hence the same prompt prefix and the same cache.
import hashlib
import json
from pathlib import Path

INDEX = Path(".fichiers.json")


def empreinte(chemin: Path) -> str:
    h = hashlib.sha256()
    with chemin.open("rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def _lire_index() -> dict:
    return json.loads(INDEX.read_text()) if INDEX.exists() else {}


def _ecrire_index(index: dict) -> None:
    INDEX.write_text(json.dumps(index, indent=2, sort_keys=True))


def file_id_pour(client, chemin: Path) -> str:
    """Return the PDF's file_id, uploading it only if it is new."""
    # TODO(step 3):
    # 1. read the index and compute the fingerprint of the PDF
    # 2. if the fingerprint is already indexed, return its file_id without uploading
    # 3. otherwise upload with client.files.upload(file=(chemin.name, f, "application/pdf")),
    #    store fichier.id in the index, write the index and return the id
    raise NotImplementedError("TODO(step 3): file_id_pour")


def oublier(chemin: Path) -> None:
    """Remove the PDF from the local index, for example when the file was deleted on the API side."""
    # TODO(step 3): drop the fingerprint of chemin from the index, then write the index.
    raise NotImplementedError("TODO(step 3): oublier")
