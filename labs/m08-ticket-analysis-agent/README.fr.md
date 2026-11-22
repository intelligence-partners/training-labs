# Lab M08 : agent d'analyse de tickets

Code d'accompagnement du lab du module M08 (Agents) de la formation Intelligence Training :
*Lab : un agent d'analyse de tickets avec garde-fous*. [English version](README.md).

## Objectif

Construire de bout en bout un agent de support niveau 1 qui lit les tickets ouverts, cherche
dans la base de connaissances, fixe une priorité, rédige un brouillon de réponse et escalade
quand il le faut, puis essayer de le prendre en défaut : ticket piégé (T-1005 contient une
injection), exécution sans surveillance, budget trop court, identifiant invalide. Vous obtenez
un squelette d'agent de production à porter sur le Tool Runner, l'Agent SDK ou Managed Agents.

## Architecture

L'agent tourne sur votre poste, en Python, et appelle l'API Claude avec `claude-opus-5-5`.
`agent.py` porte la boucle bornée ; `tools.py` porte six outils typés qui lisent et écrivent
des fichiers locaux dans `data/`. Trois outils lisent (`list_tickets`, `get_ticket`,
`search_kb`), trois écrivent (`set_priority`, `save_draft`, `escalate`) ; `set_priority` et
`escalate` sont visibles par d'autres équipes et attendent votre approbation au terminal.
Chaque appel d'outil et chaque décision sont écrits dans `audit.jsonl`.

| Garde-fou | Où il se trouve |
| --- | --- |
| Schémas stricts et énumérations | Définitions des outils (`strict: true`, `enum`) |
| Validation métier (format d'identifiant, longueur, existence) | Fonctions de `tools.py`, `ToolInputError` |
| Contenu client balisé comme données | `get_ticket` et prompt système |
| Approbation humaine, refus par défaut sans surveillance | `approuver()` dans `agent.py`, `--auto-refus` |
| Boucle bornée en tours et en dollars | `MAX_TOURS`, `--budget` |
| Journal d'audit | `audit.jsonl` |

Le code garde les identifiants, prompts, tickets et messages en français de la leçon, pour
que ses commandes, ses sorties attendues et ses points de contrôle fonctionnent tels quels.
Les commentaires sont en anglais.

```text
m08-ticket-analysis-agent/
├── starter/      code à compléter (marqueurs TODO par étape de la leçon), mêmes données
├── solution/     code complet : agent.py, tools.py, providers.py, data/
├── tests/        tests hors ligne (API Claude et Bedrock simulés)
├── requirements.txt, requirements-dev.txt, .env.example
└── test.sh       installe dans .venv et lance tous les contrôles
```

## Prérequis

- Python 3.10 ou plus, un terminal, un éditeur.
- Une clé d'API Claude créée dans la Console (platform.claude.com), avec un crédit
  disponible. Créez-en une dédiée au lab, vous la révoquerez à la fin.
- Aucun service AWS : ce lab ne crée aucune ressource cloud (sauf si vous choisissez le
  fournisseur Bedrock facultatif décrit plus bas).

## Coût estimé

Tel que l'indique la leçon : une exécution complète sur les cinq tickets prend de l'ordre de
10 à 15 tours ; comptez quelques dizaines de centimes à un dollar selon le nombre de tours, la
longueur des réponses et l'effet du cache. Le script s'arrête de lui-même au-delà de 1 $ par
défaut. Les tarifs codés dans le script (4 $ par million de tokens en entrée et 20 $ en sortie
pour Claude Opus 5.5) sont ceux de la date de rédaction : vérifiez la page tarifs.

## Étapes

| Étape de la leçon | Dans ce dépôt |
| --- | --- |
| 1. Préparer le projet | `python3 -m venv .venv`, `pip install -r requirements.txt` (fixe `anthropic==2.12.0`) |
| 2. Les données | `data/tickets.json`, `data/kb.json` et la copie de remise à zéro `data/tickets.init.json` (fournis) |
| 3. Les outils | `starter/tools.py` (TODO étape 3), `solution/tools.py` |
| 4. La boucle et ses garde-fous | `starter/agent.py` (TODO étape 4), `solution/agent.py` |
| 5. Première exécution | `python agent.py "Traite les tickets ouverts."` |
| 6. Éprouver les garde-fous | `--auto-refus`, `--budget 0.03`, identifiant invalide T-12 (commandes ci-dessous) |
| 7. Aller plus loin (facultatif) | Tool Runner, évaluation, Managed Agents, plafond d'escalades : hors du dépôt |

## Lancer le lab

```bash
git clone https://github.com/intelligence-partners/training-labs.git
cd training-labs/labs/m08-ticket-analysis-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...      # votre clé de lab
python -c "import anthropic; print(anthropic.__version__)"
cd starter        # ou : cd solution, pour lancer l'agent terminé
```

Étape 3, tester les outils sans appeler le modèle :

```bash
python -c "import json, tools; print(json.dumps(tools.list_tickets('open'), ensure_ascii=False)[:70])"
python -c "import tools; print([r['id'] for r in tools.search_kb('erreur 401 SSO')['results']])"
python -c "import tools; tools.get_ticket('T-12')"
```

Étapes 5 et 6 :

```bash
python agent.py "Traite les tickets ouverts."
# remise à zéro entre deux essais
cp data/tickets.init.json data/tickets.json && rm -rf drafts escalations.jsonl audit.jsonl
python agent.py --auto-refus "Traite les tickets ouverts."
grep -c '"decision": "refusé"' audit.jsonl
python agent.py --budget 0.03 "Traite les tickets ouverts." ; echo "code de sortie : $?"
tail -n 1 audit.jsonl
python agent.py "Ouvre le ticket T-12 puis le ticket T-1003 et propose une réponse."
grep '"decision": "invalide"' audit.jsonl
```

Codes de sortie : 0 rapport écrit, 1 `stop_reason` inattendu, 2 budget atteint, 3 limite de tours.

## Tester

```bash
bash test.sh
```

Le script crée `.venv`, installe `requirements-dev.txt`, lance les tests unitaires sur
`solution/` et vérifie que `starter/` se compile et s'importe. Les tests ne demandent ni clé ni
réseau : l'API Claude est remplacée par un transport simulé derrière un vrai client
`anthropic` (chaque requête reste validée par le SDK), et les appels Converse passent par le
Stubber de botocore.

## Nettoyer

Ce lab ne crée aucune ressource AWS ni aucun objet persistant côté Anthropic : rien ne
continue à être facturé une fois le script arrêté.

```bash
deactivate
cd ../.. && rm -rf m08-ticket-analysis-agent/.venv   # ou supprimez votre clone
```

Révoquez enfin la clé d'API du lab dans la Console (page des clés d'API) et retirez-la de
votre shell (`unset ANTHROPIC_API_KEY`).

## Changer de modèle

Le parcours de la leçon est l'API Claude avec `claude-opus-5-5`. `providers.py` ajoute un
sélecteur facultatif, `MODEL_PROVIDER`, qui laisse `agent.py` et `tools.py` inchangés :

| `MODEL_PROVIDER` | Client | Identifiant de modèle |
| --- | --- | --- |
| `anthropic` (défaut) | `anthropic.Anthropic()` | `claude-opus-5-5` |
| `anthropic-bedrock` | `anthropic.AnthropicBedrock` (Claude sur Amazon Bedrock) | `BEDROCK_MODEL_ID` |
| `bedrock` | boto3 `bedrock-runtime` `converse` (tout modèle Bedrock avec appel d'outils) | `BEDROCK_MODEL_ID` |

```bash
export MODEL_PROVIDER=bedrock AWS_REGION=eu-west-3
export BEDROCK_MODEL_ID=<identifiant de modèle ou de profil d'inférence activé sur votre compte>
export PRICE_SHEET='{"input": ..., "output": ..., "cache_write": ..., "cache_read": ...}'
python agent.py --auto-refus "Traite les tickets ouverts."
```

- Renseignez `PRICE_SHEET` avec les tarifs du modèle utilisé (dollars par million de tokens) :
  l'estimation de coût et le garde-fou `--budget` en dépendent.
- Avec `bedrock`, les requêtes sont traduites pour Converse : les outils gardent `strict`,
  `cache_control` devient un point de cache, `effort` est propre à Claude et n'est pas envoyé.
  Pour un modèle qui ne gère pas une de ces fonctions, utilisez `BEDROCK_STRICT_TOOLS=false`,
  `BEDROCK_CACHE_POINTS=false` ou `BEDROCK_MAX_TOKENS`. Sans schéma strict, la forme des
  arguments n'est plus garantie : la validation métier de `tools.py` s'applique toujours, mais
  un argument manquant arrête le script.
- Les fournisseurs Bedrock demandent des identifiants AWS autorisés à invoquer le modèle ; ils
  ne créent aucune ressource.
