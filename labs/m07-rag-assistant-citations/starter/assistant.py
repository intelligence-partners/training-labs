# assistant.py: generation with citations from the retrieved passages
# Step 7. The passages become search_result blocks with a stable kb://… source; the system
# prompt fixes the abstention sentence; fallbacks="default" retries on another model if a
# classifier declines the request; the formatting numbers the cited sources.
import argparse

import anthropic

from recherche import DROITS, Recherche

MODELE = "claude-opus-5-5"
ABSTENTION = "Je ne trouve pas cette information dans la documentation disponible."
# Opus 5.5 prices on 27 October 2026, in dollars per million tokens.
PRIX = {"input": 4.00, "cache_write": 5.00, "cache_read": 0.20, "output": 20.00}

SYSTEME = f"""Tu es l'assistant documentaire interne de Brivane, une entreprise industrielle.
Tu réponds aux questions des salariés uniquement à partir des résultats de recherche fournis dans
leur message. Tu n'utilises jamais tes connaissances générales pour compléter une réponse.
Si la question comporte plusieurs points, traite-les un par un.
Pour tout point que les résultats ne permettent pas de traiter, écris exactement :
« {ABSTENTION} »
Si deux résultats se contredisent, signale-le et donne les deux versions.
Réponds en français, en phrases courtes, sans titre et sans formule de politesse."""

client = anthropic.Anthropic()


def bloc_resultat(c: dict) -> dict:
    # TODO(step 7): a search_result block: source f"kb://{c['id']}", title f"{c['titre']} — {c['section']}",
    # content [{"type": "text", "text": c["texte"]}] (the original text, never the generated
    # context) and citations {"enabled": True}.
    raise NotImplementedError("TODO(step 7): bloc_resultat")


def repondre(question: str, passages: list[dict]):
    # TODO(step 7): the search_result blocks, then the question as a text block, sent with
    # client.beta.messages.create(model=MODELE, max_tokens=16000,
    # betas=["server-side-fallback-2026-07-01"], fallbacks="default",
    # output_config={"effort": "medium"}, system=SYSTEME, messages=[...]).
    raise NotImplementedError("TODO(step 7): repondre")


def sources_citees(reponse) -> list[tuple[str, str]]:
    # TODO(step 7): the (source, title) pairs of the search_result_location citations of the
    # text blocks, in order of first appearance, without duplicates.
    raise NotImplementedError("TODO(step 7): sources_citees")


def mettre_en_forme(reponse) -> str:
    # TODO(step 7):
    # - stop_reason "refusal" -> "La demande n'a pas pu être traitée."
    # - stop_reason "max_tokens" -> "La réponse a été interrompue : relancez la question."
    # - otherwise: each text block followed by the numbers [n] of the sources it cites, then
    #   "\n\nSources :\n" and one line per source: f"[{n}] {titre} ({source})"
    #   (no "Sources" section when nothing is cited, e.g. for the abstention).
    raise NotImplementedError("TODO(step 7): mettre_en_forme")


def cout(usage) -> float:
    return (usage.input_tokens * PRIX["input"]
            + (usage.cache_creation_input_tokens or 0) * PRIX["cache_write"]
            + (usage.cache_read_input_tokens or 0) * PRIX["cache_read"]
            + usage.output_tokens * PRIX["output"]) / 1_000_000


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("question")
    p.add_argument("--profil", default="salarie", choices=list(DROITS))
    a = p.parse_args()
    passages = Recherche().rechercher(a.question, a.profil)
    reponse = repondre(a.question, passages)
    print(mettre_en_forme(reponse))
    u = reponse.usage
    print(f"\n[{reponse.model} · entrée {u.input_tokens} · sortie {u.output_tokens} · {cout(u):.4f} $]")
