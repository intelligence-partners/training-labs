# evaluation.py: small evaluation set, retrieval (free) and generation (calls to Claude)
# Step 8. Eleven questions: facts, paraphrase, identifier, an HR question asked by both
# profiles, and two out-of-corpus questions.
import argparse

from assistant import ABSTENTION, mettre_en_forme, repondre, sources_citees
from recherche import Recherche

JEU = [
    {"q": "Combien de jours de télétravail par semaine sont autorisés ?", "fichiers": ["politique-teletravail.md"], "profil": "salarie"},
    {"q": "Combien de jours puis-je travailler de chez moi ?", "fichiers": ["politique-teletravail.md"], "profil": "salarie"},
    {"q": "Je suis en CDD depuis huit mois, ai-je droit au télétravail ?", "fichiers": ["politique-teletravail.md"], "profil": "salarie"},
    {"q": "Quel est le plafond d'une nuit d'hôtel à Paris ?", "fichiers": ["notes-de-frais.md"], "profil": "salarie"},
    {"q": "Avant quelle date dois-je saisir mes notes de frais ?", "fichiers": ["notes-de-frais.md"], "profil": "salarie"},
    {"q": "Qui faut-il prévenir avant d'appliquer la PRC-114 ?", "fichiers": ["procedure-prc-114.md"], "profil": "salarie"},
    {"q": "J'ai cliqué sur un lien d'hameçonnage, que dois-je faire ?", "fichiers": ["securite-incidents.md"], "profil": "salarie"},
    {"q": "Combien de jours peut-on verser sur le compte épargne-temps ?", "fichiers": ["conges.md"], "profil": "salarie"},
    {"q": "Quelle est l'enveloppe d'augmentations collectives 2026 ?", "fichiers": [], "profil": "salarie"},
    {"q": "Quelle est l'enveloppe d'augmentations collectives 2026 ?", "fichiers": ["remunerations-2026.md"], "profil": "rh"},
    {"q": "L'entreprise rembourse-t-elle les abonnements de salle de sport ?", "fichiers": [], "profil": "salarie"},
]


def rang_premier(passages: list[dict], fichiers: list[str]) -> int | None:
    # TODO(step 8): the rank (from 1) of the first passage whose "fichier" is in fichiers, else None.
    raise NotImplementedError("TODO(step 8): rang_premier")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--generation", action="store_true", help="appelle Claude (payant)")
    p.add_argument("--sans-hybride", action="store_true")
    p.add_argument("--sans-rerank", action="store_true")
    a = p.parse_args()
    r = Recherche()

    # TODO(step 8): for each item of JEU, search with item["profil"] (and the --sans-* flags).
    # Retrieval (free), only for items with expected files: recall = 1 if rang_premier() finds one,
    # reciprocal rank = 1 / rang. Generation (--generation, paid): call repondre(), format it,
    # take the cited files from sources_citees(); an item with expected files is "ok" if it cites
    # something, only expected files, and does not abstain; an out-of-corpus item is "ok" if it
    # abstains (ABSTENTION in the text) and cites nothing.
    # Print a header f"{'question':<62} {'rang':>4}  génération", one row per question
    # f"{item['q'][:60]:<62} {rang or '-':>4}  {verdict}", then
    #   f"\nRappel@5 : {recall:.2f}   MRR : {mrr:.2f}" and, with --generation,
    #   f"Génération correcte : {ok}/{total}"
    raise NotImplementedError(f"TODO(step 8): evaluation ({len(JEU)} questions, {r.collection.count()} chunks, {a})")


if __name__ == "__main__":
    main()
