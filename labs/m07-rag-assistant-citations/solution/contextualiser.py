# contextualiser.py: adds to each chunk a context written by Claude Haiku 5.5 (optional)
# Step 4 (optional): Contextual Retrieval. The whole document is the cached prefix; the chunks
# of one document are processed one after the other so the cache stays warm.
import json
from collections import defaultdict
from pathlib import Path

import anthropic

import bedrock
from ingestion import lire

client = anthropic.Anthropic()
MODELE = "claude-haiku-5-5"
# Haiku 5.5 prices (prompt under 100,000 tokens), in dollars per million tokens.
PRIX = {"input": 0.10, "cache_write": 0.125, "cache_read": 0.01, "output": 0.50}

CONSIGNE = """Voici le passage à situer dans l'ensemble du document :
<chunk>
{chunk}
</chunk>
Rédige un contexte bref (une ou deux phrases) qui situe ce passage dans le document : de quel
document il s'agit, quelle section, quel sujet. Ce contexte sert uniquement à améliorer la
recherche du passage. Réponds seulement par ce contexte, sans autre texte."""


def contextualiser(document: str, chunk: str) -> tuple[str, object]:
    if bedrock.provider() == "bedrock":  # optional provider switch, see bedrock.py
        return bedrock.contextualiser(document, CONSIGNE.format(chunk=chunk))
    reponse = client.messages.create(
        model=MODELE,
        max_tokens=300,
        thinking={"type": "disabled"},
        output_config={"effort": "low"},
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": f"<document>\n{document}\n</document>",
                 "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": CONSIGNE.format(chunk=chunk)},
            ],
        }],
    )
    if reponse.stop_reason != "end_turn":
        return "", reponse.usage
    texte = "".join(b.text for b in reponse.content if b.type == "text").strip()
    return texte, reponse.usage


def main() -> None:
    chunks = [json.loads(l) for l in open("chunks.jsonl", encoding="utf-8")]
    par_fichier = defaultdict(list)
    for c in chunks:
        par_fichier[c["fichier"]].append(c)

    cout, lus = 0.0, 0
    for fichier, liste in par_fichier.items():
        _, document = lire(Path("corpus") / fichier)
        for c in liste:                      # the chunks of one document in a row: warm cache
            c["contexte"], u = contextualiser(document, c["texte"])
            lus += u.cache_read_input_tokens or 0
            cout += (u.input_tokens * PRIX["input"]
                     + (u.cache_creation_input_tokens or 0) * PRIX["cache_write"]
                     + (u.cache_read_input_tokens or 0) * PRIX["cache_read"]
                     + u.output_tokens * PRIX["output"]) / 1_000_000

    with open("chunks.jsonl", "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    if bedrock.provider() == "bedrock":
        print(f"{len(chunks)} chunks contextualisés, {lus} tokens lus depuis le cache "
              "(tarif Amazon Bedrock propre au modèle : coût non calculé)")
        return
    print(f"{len(chunks)} chunks contextualisés, {lus} tokens lus depuis le cache, coût estimé {cout:.4f} $")


if __name__ == "__main__":
    main()
