"""M14 lab: instrumented ticket triage agent (traces, cost, quality).

STARTER: complete the TODO markers by following step 5 of the lesson (and step 11 for v2).

The agent, its prompt, its tools, its test tickets and its metric names stay in French, as in
the lesson, so that the commands, the dashboard, the alarms and the checks work unchanged.
"""
import json
import os
import time

import boto3
from opentelemetry import trace

from providers import ANTHROPIC_BEDROCK, BEDROCK, make_client, prices_from_env

REGION = os.environ.get("AWS_REGION", "eu-west-3")
MODELE = os.environ.get("MODEL_ID", "eu.anthropic.claude-opus-5-5")
VERSION = os.environ.get("PROMPT_VERSION", "v1")
ESPACE = "M14/AgentSupport"
MAX_TOURS = 6

# Dollars per million tokens. Claude API price sheet for Opus 5.5:
# replace it with the current Bedrock price sheet (Amazon Bedrock pricing page),
# for instance with PRICE_SHEET='{"input": ..., "cache_write": ..., "cache_read": ..., "output": ...}'.
GRILLE = prices_from_env({"input": 4.00, "cache_write": 5.00, "cache_read": 0.20, "output": 20.00})

# AnthropicBedrock (bedrock-runtime), as in the lesson. MODEL_PROVIDER=bedrock switches to the
# boto3 Converse API, to replay the evaluation set on another Bedrock model family.
client = make_client(ANTHROPIC_BEDROCK, REGION, allowed=(ANTHROPIC_BEDROCK, BEDROCK))
cloudwatch = boto3.client("cloudwatch", region_name=REGION)
tracer = trace.get_tracer("m14.agent-support")

POLITIQUE = """Vous êtes l'agent de tri du support d'un distributeur de matériel professionnel.
Pour chaque ticket :
1. Identifiez le client avec l'outil chercher_client, à partir de son adresse e-mail.
2. Si le ticket mentionne une commande (format CMD-XXXX), consultez-la avec consulter_commande.
3. Terminez en appelant enregistrer_tri une seule fois, avec la catégorie et la priorité.

Catégories : livraison, facturation, panne_produit, compte, autre.
Priorités :
- P1 : client du segment « grand compte », ou activité du client à l'arrêt.
- P2 : préjudice financier chiffré, ou livraison en retard de plus de 3 jours.
- P3 : tous les autres cas.
Vous ne répondez pas au client : vous triez seulement. Le référentiel produits ci-dessous fait foi."""

FAMILLES = ["Bureau", "Atelier", "Logistique", "Réseau", "Énergie"]
REFERENTIEL = "\n".join(
    f"- REF-{i:04d} · gamme {FAMILLES[i % 5]} · délai standard {2 + i % 7} jours · garantie {12 + 12 * (i % 3)} mois"
    for i in range(1, 301)
)


def systeme(version: str) -> list:
    texte = f"{POLITIQUE}\n\n<referentiel_produits>\n{REFERENTIEL}\n</referentiel_produits>"
    # TODO (step 5, used at step 11): for version "v2", put "Horodatage de la requête : <time.time_ns()>"
    # and a blank line at the top of the text: a deliberately faulty prompt whose prefix changes
    # on every request, so the cache is never hit.
    return [{"type": "text", "text": texte, "cache_control": {"type": "ephemeral"}}]


OUTILS = [
    {
        "name": "chercher_client",
        "description": "Retrouve un client par son adresse e-mail. Renvoie son identifiant, son segment et l'état de son activité.",
        "input_schema": {
            "type": "object",
            "properties": {"email": {"type": "string"}},
            "required": ["email"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "consulter_commande",
        "description": "Renvoie le statut, la date de livraison prévue et le retard en jours d'une commande (format CMD-XXXX).",
        "input_schema": {
            "type": "object",
            "properties": {"numero": {"type": "string"}},
            "required": ["numero"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "enregistrer_tri",
        "description": "Enregistre la décision de tri du ticket. À appeler une seule fois, en dernier.",
        "input_schema": {
            "type": "object",
            "properties": {
                "categorie": {"type": "string", "enum": ["livraison", "facturation", "panne_produit", "compte", "autre"]},
                "priorite": {"type": "string", "enum": ["P1", "P2", "P3"]},
                "justification": {"type": "string"},
            },
            "required": ["categorie", "priorite", "justification"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]

CLIENTS = {
    "achats@batimat-pro.fr": {"id": "C-101", "segment": "grand compte", "activite": "normale"},
    "compta@menuiserie-roux.fr": {"id": "C-207", "segment": "PME", "activite": "normale"},
    "atelier@meca-precision.fr": {"id": "C-318", "segment": "PME", "activite": "à l'arrêt"},
    "contact@cabinet-lefort.fr": {"id": "C-422", "segment": "TPE", "activite": "normale"},
}
COMMANDES = {
    "CMD-5521": {"statut": "en transit", "livraison_prevue": "2026-10-21", "retard_jours": 6},
    "CMD-5630": {"statut": "livrée chez un voisin", "livraison_prevue": "2026-10-24", "retard_jours": 0},
    "CMD-5702": {"statut": "en préparation", "livraison_prevue": "2026-10-29", "retard_jours": 0},
}

# Evaluation set: eight tickets and the expected decision.
TICKETS = [
    {"id": "T01", "email": "achats@batimat-pro.fr", "texte": "Notre commande CMD-5702 n'est pas encore partie, pouvez-vous confirmer la date ?",
     "attendu": {"categorie": "livraison", "priorite": "P1", "outil_requis": "consulter_commande"}},
    {"id": "T02", "email": "compta@menuiserie-roux.fr", "texte": "La facture F-88213 compte deux fois les frais de port : 145 € de trop.",
     "attendu": {"categorie": "facturation", "priorite": "P2"}},
    {"id": "T03", "email": "atelier@meca-precision.fr", "texte": "Le compresseur REF-0117 livré la semaine dernière ne démarre plus.",
     "attendu": {"categorie": "panne_produit", "priorite": "P1"}},
    {"id": "T04", "email": "contact@cabinet-lefort.fr", "texte": "Je n'arrive plus à me connecter à mon espace client depuis hier.",
     "attendu": {"categorie": "compte", "priorite": "P3"}},
    {"id": "T05", "email": "compta@menuiserie-roux.fr", "texte": "Où en est la commande CMD-5521 ? Elle devait arriver le 21.",
     "attendu": {"categorie": "livraison", "priorite": "P2", "outil_requis": "consulter_commande"}},
    {"id": "T06", "email": "contact@cabinet-lefort.fr", "texte": "Pouvez-vous m'envoyer votre catalogue papier 2027 ?",
     "attendu": {"categorie": "autre", "priorite": "P3"}},
    {"id": "T07", "email": "achats@batimat-pro.fr", "texte": "Merci d'ajouter un utilisateur, M. Dupont, à notre espace client.",
     "attendu": {"categorie": "compte", "priorite": "P1"}},
    {"id": "T08", "email": "contact@cabinet-lefort.fr", "texte": "La commande CMD-5630 a été déposée chez notre voisin, comment la récupérer ?",
     "attendu": {"categorie": "livraison", "priorite": "P3", "outil_requis": "consulter_commande"}},
]


def executer_outil(nom: str, arguments: dict) -> dict:
    if nom == "chercher_client":
        return CLIENTS.get(arguments["email"].strip().lower(), {"erreur": "client inconnu"})
    if nom == "consulter_commande":
        return COMMANDES.get(arguments["numero"].strip().upper(), {"erreur": "commande inconnue"})
    if nom == "enregistrer_tri":
        return {"statut": "enregistré"}
    return {"erreur": f"outil inconnu : {nom}"}


def cout_usd(c: dict) -> float:
    # TODO (step 5): cost in dollars of the counters c (input, cache_write, cache_read, output)
    # with the GRILLE prices, which are per million tokens.
    raise NotImplementedError("step 5: cout_usd")


def noter(ticket: dict, tri: dict | None, outils_appeles: list) -> bool:
    # TODO (step 5): deterministic check. False without a triage; otherwise the category and the
    # priority must match ticket["attendu"], and "outil_requis", when present, must have been called.
    raise NotImplementedError("step 5: noter")


def traiter(ticket: dict) -> dict:
    # TODO (step 5): one task, in a span "invoke_agent agent-support" with the attributes
    # gen_ai.operation.name, gen_ai.agent.name, app.task.id and app.prompt.version.
    #   - at most MAX_TOURS turns, until enregistrer_tri is called; each turn:
    #     with client.messages.stream(model=MODELE, max_tokens=4096, system=systeme(VERSION),
    #     tools=OUTILS, output_config={"effort": "low"}, messages=messages) as flux:
    #         reponse = flux.get_final_message()
    #   - add reponse.usage to the counters (input, cache_write, cache_read, output)
    #   - any stop_reason other than tool_use ends the task (it fails)
    #   - run each tool in a span f"execute_tool {bloc.name}" (gen_ai.operation.name,
    #     gen_ai.tool.name, gen_ai.tool.call.id), with executer_outil()
    #   - at the end, set app.task.turns, app.task.cost_usd, app.task.outcome ("reussie"/"echec")
    #     and app.task.stop_reason on the task span
    # Return {"id", "reussie", "tours", "cout_usd", "duree_ms", "tokens_entree_total", "tokens_lus_cache"}.
    raise NotImplementedError("step 5: traiter")


def publier(r: dict) -> None:
    # TODO (step 5): put_metric_data in the ESPACE namespace, each metric twice: without dimension
    # and with the PromptVersion dimension. Metrics: TacheTerminee (Count), TacheReussie (Count),
    # CoutTacheUSD (None), DureeTacheMs (Milliseconds), ToursParTache (Count),
    # TokensEntreeTotal (Count), TokensLusEnCache (Count).
    raise NotImplementedError("step 5: publier")


def main() -> None:
    resultats = []
    for ticket in TICKETS:
        r = traiter(ticket)
        publier(r)
        resultats.append(r)
        taux = r["tokens_lus_cache"] / r["tokens_entree_total"] if r["tokens_entree_total"] else 0
        print(f"[{VERSION}] {r['id']} {'ok   ' if r['reussie'] else 'ÉCHEC'} tours={r['tours']} "
              f"coût={r['cout_usd']:.4f} $ durée={r['duree_ms'] / 1000:.1f} s cache={taux:.0%}")
    n_ok = sum(r["reussie"] for r in resultats)
    cout_total = sum(r["cout_usd"] for r in resultats)
    lus = sum(r["tokens_lus_cache"] for r in resultats)
    total = sum(r["tokens_entree_total"] for r in resultats)
    par_reussite = cout_total / n_ok if n_ok else float("inf")
    print(f"Synthèse {VERSION} : réussite {n_ok}/{len(resultats)} · coût moyen {cout_total / len(resultats):.4f} $/tâche"
          f" · coût par tâche réussie {par_reussite:.4f} $ · lecture cache {lus / total:.0%}")


if __name__ == "__main__":
    main()
