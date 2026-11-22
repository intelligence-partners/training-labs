# assistant.py: generation with citations from the retrieved passages
# Step 7. The passages become search_result blocks with a stable kb://… source; the system
# prompt fixes the abstention sentence; fallbacks="default" retries on another model if a
# classifier declines the request; the formatting numbers the cited sources.
import argparse

import anthropic

import bedrock
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
    return {
        "type": "search_result",
        "source": f"kb://{c['id']}",
        "title": f"{c['titre']} — {c['section']}",
        "content": [{"type": "text", "text": c["texte"]}],   # the original text, never the generated context
        "citations": {"enabled": True},
    }


def repondre(question: str, passages: list[dict]):
    if bedrock.provider() == "bedrock":  # optional provider switch, see bedrock.py
        return bedrock.repondre(question, passages, SYSTEME)
    contenu = [bloc_resultat(c) for c in passages]
    contenu.append({"type": "text", "text": question})
    return client.beta.messages.create(
        model=MODELE,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "medium"},
        system=SYSTEME,
        messages=[{"role": "user", "content": contenu}],
    )


def sources_citees(reponse) -> list[tuple[str, str]]:
    vues = []
    for bloc in reponse.content:
        if bloc.type == "text":
            for c in bloc.citations or []:
                if c.type == "search_result_location" and (c.source, c.title) not in vues:
                    vues.append((c.source, c.title))
    return vues


def mettre_en_forme(reponse) -> str:
    if reponse.stop_reason == "refusal":
        return "La demande n'a pas pu être traitée."
    if reponse.stop_reason == "max_tokens":
        return "La réponse a été interrompue : relancez la question."
    sources = sources_citees(reponse)
    morceaux = []
    for bloc in reponse.content:
        if bloc.type != "text":
            continue
        morceaux.append(bloc.text)
        renvois = sorted({sources.index((c.source, c.title)) + 1 for c in (bloc.citations or [])
                          if c.type == "search_result_location"})
        morceaux.extend(f"[{n}]" for n in renvois)
    texte = "".join(morceaux).strip()
    if sources:
        texte += "\n\nSources :\n" + "\n".join(f"[{n}] {titre} ({source})"
                                               for n, (source, titre) in enumerate(sources, start=1))
    return texte


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
    if bedrock.provider() == "bedrock":  # Bedrock prices depend on the model and the region
        print(f"\n[{reponse.model} · entrée {u.input_tokens} · sortie {u.output_tokens}]")
    else:
        print(f"\n[{reponse.model} · entrée {u.input_tokens} · sortie {u.output_tokens} · {cout(u):.4f} $]")
