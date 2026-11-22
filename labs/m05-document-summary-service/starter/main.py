# main.py
# Step 5: the command line. Each error family gets a clear message and its own exit code.
import argparse
import sys
from pathlib import Path

import anthropic

from fichiers import file_id_pour, oublier
from service import PROFILS, ErreurSynthese, client, cout_estime, synthetiser


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthèse structurée d'un PDF avec Claude")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--profil", choices=sorted(PROFILS), default="direction")
    args = parser.parse_args()

    if not args.pdf.is_file() or args.pdf.suffix.lower() != ".pdf":
        print("Fichier PDF introuvable.", file=sys.stderr)
        return 2

    # TODO(step 5): upload with file_id_pour(client, args.pdf), then synthetiser(file_id, args.profil).
    # - anthropic.NotFoundError on the synthesis: the file_id of the index was deleted on the API side,
    #   so call oublier(args.pdf) and retry once with a fresh file_id_pour(...)
    # - ErreurSynthese -> "Synthèse impossible : {e}", exit 3
    # - anthropic.AuthenticationError -> "Clé d'API absente ou invalide (ANTHROPIC_API_KEY).", exit 4
    # - anthropic.RateLimitError -> "Limite de débit atteinte malgré les relances : réessayez plus tard.", exit 5
    # - anthropic.APIStatusError -> f"Erreur API {e.status_code} : {e.message}", exit 6
    # - anthropic.APIConnectionError -> "Connexion à l'API impossible.", exit 7
    # All messages go to stderr.
    #
    # TODO(step 5): print the summary as JSON on stdout (model_dump_json(indent=2)), then on stderr:
    #   modèle : {modele} | request-id : {request_id}
    #   usage : input=... cache_write=... cache_read=... output=...
    #   coût estimé (tarif Opus 5.5) : {cout_estime(u):.4f} $
    raise NotImplementedError("TODO(step 5): main")


if __name__ == "__main__":
    sys.exit(main())
