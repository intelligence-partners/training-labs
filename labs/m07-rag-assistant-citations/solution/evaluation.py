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
    for rang, c in enumerate(passages, start=1):
        if c["fichier"] in fichiers:
            return rang
    return None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--generation", action="store_true", help="appelle Claude (payant)")
    p.add_argument("--sans-hybride", action="store_true")
    p.add_argument("--sans-rerank", action="store_true")
    a = p.parse_args()
    r = Recherche()

    rappels, rrs, generation_ok = [], [], []
    print(f"{'question':<62} {'rang':>4}  génération")
    for item in JEU:
        passages = r.rechercher(item["q"], item["profil"], hybride=not a.sans_hybride,
                                rerank=not a.sans_rerank)
        rang = rang_premier(passages, item["fichiers"]) if item["fichiers"] else None
        if item["fichiers"]:
            rappels.append(1.0 if rang else 0.0)
            rrs.append(1.0 / rang if rang else 0.0)

        verdict = "-"
        if a.generation:
            reponse = repondre(item["q"], passages)
            texte = mettre_en_forme(reponse)
            cites = {s.removeprefix("kb://").split("#")[0] for s, _ in sources_citees(reponse)}
            if item["fichiers"]:
                ok = bool(cites) and cites <= set(item["fichiers"]) and ABSTENTION not in texte
            else:
                ok = ABSTENTION in texte and not cites
            generation_ok.append(ok)
            verdict = "ok" if ok else "ÉCHEC"
        print(f"{item['q'][:60]:<62} {rang or '-':>4}  {verdict}")

    print(f"\nRappel@5 : {sum(rappels) / len(rappels):.2f}   MRR : {sum(rrs) / len(rrs):.2f}")
    if generation_ok:
        print(f"Génération correcte : {sum(generation_ok)}/{len(generation_ok)}")


if __name__ == "__main__":
    main()
