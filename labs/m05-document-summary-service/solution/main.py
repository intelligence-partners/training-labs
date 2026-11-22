# main.py
# Step 5: the command line. Each error family gets a clear message and its own exit code,
# and the PDF is uploaded again once if the file_id from the index was deleted on the API side.
import argparse
import os
import sys
from pathlib import Path

import anthropic

from fichiers import file_id_pour, oublier
from service import PROFILS, ErreurSynthese, client, cout_estime, synthetiser

# Optional provider switch (not in the lesson): MODEL_PROVIDER=bedrock routes the call
# through Amazon Bedrock's Converse API instead of the Claude API. See bedrock.py.
PROVIDERS = ("anthropic", "bedrock")


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthèse structurée d'un PDF avec Claude")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--profil", choices=sorted(PROFILS), default="direction")
    args = parser.parse_args()

    if not args.pdf.is_file() or args.pdf.suffix.lower() != ".pdf":
        print("Fichier PDF introuvable.", file=sys.stderr)
        return 2

    provider = os.environ.get("MODEL_PROVIDER", "anthropic")
    if provider not in PROVIDERS:
        print(f"MODEL_PROVIDER doit valoir anthropic ou bedrock, pas {provider!r}.", file=sys.stderr)
        return 2
    if provider == "bedrock":
        from bedrock import main_bedrock  # imported lazily: boto3 is only needed for this path

        return main_bedrock(args.pdf, args.profil)

    try:
        file_id = file_id_pour(client, args.pdf)
        try:
            resultat = synthetiser(file_id, args.profil)
        except anthropic.NotFoundError:
            # The file_id from the local index may have been deleted on the API side: upload once more.
            oublier(args.pdf)
            resultat = synthetiser(file_id_pour(client, args.pdf), args.profil)
    except ErreurSynthese as e:
        print(f"Synthèse impossible : {e}", file=sys.stderr)
        return 3
    except anthropic.AuthenticationError:
        print("Clé d'API absente ou invalide (ANTHROPIC_API_KEY).", file=sys.stderr)
        return 4
    except anthropic.RateLimitError:
        print("Limite de débit atteinte malgré les relances : réessayez plus tard.", file=sys.stderr)
        return 5
    except anthropic.APIStatusError as e:
        print(f"Erreur API {e.status_code} : {e.message}", file=sys.stderr)
        return 6
    except anthropic.APIConnectionError:
        print("Connexion à l'API impossible.", file=sys.stderr)
        return 7

    u = resultat.usage
    print(resultat.synthese.model_dump_json(indent=2))
    print(f"modèle : {resultat.modele} | request-id : {resultat.request_id}", file=sys.stderr)
    print(
        f"usage : input={u.input_tokens} cache_write={u.cache_creation_input_tokens or 0} "
        f"cache_read={u.cache_read_input_tokens or 0} output={u.output_tokens}",
        file=sys.stderr,
    )
    print(f"coût estimé (tarif Opus 5.5) : {cout_estime(u):.4f} $", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
