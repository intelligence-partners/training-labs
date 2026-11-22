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
    index = _lire_index()
    cle = empreinte(chemin)
    if cle in index:
        return index[cle]
    with chemin.open("rb") as f:
        fichier = client.files.upload(file=(chemin.name, f, "application/pdf"))
    index[cle] = fichier.id
    _ecrire_index(index)
    return fichier.id


def oublier(chemin: Path) -> None:
    """Remove the PDF from the local index, for example when the file was deleted on the API side."""
    index = _lire_index()
    index.pop(empreinte(chemin), None)
    _ecrire_index(index)
