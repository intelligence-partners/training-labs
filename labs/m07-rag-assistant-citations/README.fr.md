# Lab m07 : un assistant documentaire avec citations

Code d'accompagnement du lab qui clôt le module **M07, RAG et ingénierie du contexte**, du parcours Intelligence Training (leçon « Lab : un assistant documentaire avec citations »). Version anglaise : [README.md](README.md).

## Objectif

Un assistant documentaire pour Brivane, une entreprise fictive. Il ingère la documentation interne, la découpe, l'indexe en vecteurs et en BM25, cherche de façon hybride en respectant versions et droits, reclasse les candidats, puis fait rédiger à Claude une réponse qui cite ses sources, ou qui dit honnêtement que la documentation est muette. Un petit jeu d'évaluation mesure la récupération et la génération. Tout tourne sur votre poste, sauf les appels à Claude.

```bash
python assistant.py "Je suis en CDD depuis huit mois, ai-je droit au télétravail ?"
```

## Architecture

| Fichier | Rôle |
| --- | --- |
| `corpus/` | Sept documents Markdown avec un en-tête (titre, version, statut, droits), dont trois pièges délibérés : une version archivée qui contredit la version en vigueur, un document réservé aux RH, et une procédure désignée par son identifiant (`PRC-114`) |
| `decoupage.py` | Le découpeur par phrases avec chevauchement de la leçon sur le découpage |
| `ingestion.py` | Lecture du corpus, découpage par section puis par taille, écriture de `chunks.jsonl` |
| `contextualiser.py` | Facultatif : un contexte rédigé par Claude Haiku 5.5 pour chaque chunk (Contextual Retrieval) |
| `index.py` | Embeddings locaux (`intfloat/multilingual-e5-small`) et index Chroma persistant, similarité cosinus |
| `recherche.py` | Recherche hybride (Chroma + BM25), filtres de statut et de droits, fusion RRF, reranking par `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` |
| `assistant.py` | Génération citée par Claude Opus 5.5 à partir de blocs `search_result`, avec une formule d'abstention fixe, et mise en forme des sources numérotées |
| `evaluation.py` | Onze questions : rappel à 5 et MRR pour la récupération (gratuit), contrôle des citations et des abstentions pour la génération (appels à Claude) |

Le document archivé est indexé mais écarté par son statut à la recherche, dans Chroma (`where`) comme dans BM25 ; le document RH n'est accessible qu'au profil `rh`. Seul le texte d'origine du chunk part vers Claude, jamais le contexte généré.

Le corpus est en français, les prompts et les sorties aussi : les leçons française et anglaise utilisent ce même code.

```text
m07-rag-assistant-citations/
├── README.md, README.fr.md
├── .env.example              variables lues par le lab
├── requirements.txt          les paquets de la leçon (étape 1), sentence-transformers compris
├── requirements-bedrock.txt  + boto3, pour la variante Bedrock facultative
├── requirements-test.txt     ce dont les tests ont besoin (ni PyTorch, ni téléchargement de modèle)
├── test.sh                   contrôles hors ligne (lancés aussi par la CI)
├── cleanup.sh                supprime l'index, chunks.jsonl et les deux modèles téléchargés
├── starter/                  corpus/ + les sept fichiers avec des marqueurs TODO(step N)
├── solution/                 corpus/ + le code complet
│   └── bedrock.py            sélecteur de fournisseur facultatif (hors leçon)
└── tests/                    tests hors ligne (fakes/ contient un substitut de sentence_transformers)
```

## Prérequis

Ceux de la leçon :

- Python 3.10 ou plus, un terminal, environ **3 Go** d'espace disque (bibliothèques et deux modèles locaux d'environ 470 Mo chacun, téléchargés au premier lancement depuis Hugging Face).
- Un compte Claude Console et une clé d'API dans `ANTHROPIC_API_KEY`, ou un profil créé avec `ant auth login`.
- Aucune ressource AWS : rien à facturer côté cloud.
- Accès aux modèles : `claude-opus-5-5` (réponses) et `claude-haiku-5-5` (contextualisation facultative).

Variante Bedrock facultative : un compte AWS avec accès à un modèle Bedrock qui accepte les blocs de résultats de recherche avec citations (les modèles Claude sur Bedrock), et des identifiants AWS sur votre poste.

Testé avec Python 3.12, `anthropic` 2.12.0, `chromadb` 1.5.9, `sentence-transformers` 6.3.0 (avec `torch` 2.15.0), `rank-bm25` 0.2.2, `numpy` 2.5.5, `boto3` 1.44.9.

## Coût estimé

Tel que la leçon l'indique, aux tarifs du 27 octobre 2026 : la contextualisation facultative du corpus coûte moins d'un centime avec Haiku 5.5 ; chaque question à l'assistant, de l'ordre de 1 à 5 centimes avec Opus 5.5 selon la longueur de la réflexion ; l'évaluation de la génération sur onze questions, moins de 0,50 $. Comptez **moins de 1 $** pour tout le lab.

Les tests de ce dépôt ne coûtent rien : ils n'appellent jamais de modèle et n'en téléchargent aucun.

## Lancer le lab

```bash
git clone https://github.com/intelligence-partners/training-labs.git
cd training-labs/labs/m07-rag-assistant-citations
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."   # ou un profil créé avec « ant auth login »
cd starter                               # complétez les TODO ; ou cd solution pour le code terminé
```

| Étape de la leçon | Où | Commande et sortie attendue |
| --- | --- | --- |
| 1. Préparer l'environnement | les commandes ci-dessus | `python -c "import anthropic, chromadb, sentence_transformers; print(anthropic.__version__, chromadb.__version__, sentence_transformers.__version__)"` |
| 2. Créer le corpus | `corpus/` est déjà là, identique au script de la leçon | `ls -R corpus` |
| 3. Découper et ingérer | `decoupage.py`, `ingestion.py`, `TODO(step 3)` | `python ingestion.py` → `18 chunks écrits dans chunks.jsonl, issus de 7 fichiers` |
| 4. (facultative) Contextualiser les chunks | `contextualiser.py`, `TODO(step 4)` | `python contextualiser.py` |
| 5. Indexer | `index.py`, `TODO(step 5)` | `python index.py` → `18 vecteurs de 384 dimensions indexés dans ./index` |
| 6. Rechercher | `recherche.py`, `TODO(step 6a/6b/6c)` | `python recherche.py "Que dit la PRC-114 avant un redémarrage ?"`, puis la question RH avec et sans `--profil rh` |
| 7. Générer une réponse citée | `assistant.py`, `TODO(step 7)` | `python assistant.py "Je suis en CDD depuis huit mois, ai-je droit au télétravail ?"` et la question hors corpus |
| 8. Évaluer | `evaluation.py`, `TODO(step 8)` | `python evaluation.py` (gratuit), puis `python evaluation.py --generation` |
| 9. (facultative) Comparer les variantes | | `python evaluation.py --sans-rerank`, `--sans-hybride`, `python contextualiser.py && python index.py && python evaluation.py` |

Les étapes 3 à 6 et la partie récupération de l'étape 8 ont été lancées dans ce dépôt avec les vrais modèles locaux : `18 chunks`, `18 vecteurs de 384 dimensions`, la question PRC-114 classe `procedure-prc-114.md#0`, `#2`, `#1` en tête, le profil salarié ne voit jamais `remunerations-2026.md` alors que le profil `rh` l'obtient en premier, et l'évaluation affiche `Rappel@5 : 1.00   MRR : 0.93`, avec la paraphrase au rang 3, exactement comme dans la leçon. `recherche.py` affiche cinq lignes (`k_final=5`) ; la leçon montre les trois premières.

## Tester

```bash
bash test.sh
```

`test.sh` crée `.venv`, installe `requirements-test.txt`, compile et importe le starter, puis lance les tests sur `solution/`. Il n'installe pas PyTorch et ne télécharge aucun modèle : `tests/fakes/sentence_transformers` est un substitut déterministe de même interface (tokenizer, embeddings de 384 dimensions, scores de cross-encodeur). Chroma et rank_bm25 sont les vraies bibliothèques. Claude est remplacé par une fausse API locale atteinte par le vrai SDK, et Bedrock par le `Stubber` de botocore, qui valide chaque requête contre le modèle de service.

Ce que couvrent les tests :

- le corpus et ses trois pièges, le découpage en phrases, la taille et le chevauchement des chunks, la lecture des en-têtes et des sections, et les 18 chunks avec leurs identifiants et métadonnées (étapes 2 et 3) ;
- la requête de contextualisation (Haiku 5.5, réflexion désactivée, effort bas, document en cache), la réécriture de `chunks.jsonl`, la ligne de coût, et les chunks d'un même document traités à la suite (étape 4) ;
- la collection Chroma : 18 vecteurs de 384 dimensions, espace cosinus, nom du modèle dans les métadonnées, texte d'origine stocké, réindexation complète (étape 5) ;
- la tokenisation (identifiants gardés, accents et mots vides retirés), la RRF, les filtres de statut et de droits avec et sans recherche hybride et reranking, le profil RH, le classement PRC-114 et le format exact de la ligne de commande (étape 6) ;
- les blocs `search_result`, la requête (modèle, effort, `fallbacks`, en-tête bêta, formule d'abstention dans le prompt système, question après les résultats, contexte généré jamais envoyé), la réponse citée et l'abstention exactes de la leçon, les messages de refus et de troncature, la numérotation des sources et le coût (étape 7) ;
- le jeu d'évaluation, les règles de rang et de notation, les passes récupération et génération (étape 8), et les variantes (étape 9) ;
- les commandes de la leçon lancées telles quelles dans un dossier neuf, et `cleanup.sh` ;
- la variante Bedrock facultative.

Non couverts hors ligne : la qualité des vrais modèles (la récupération a été vérifiée une fois à la main, voir plus haut) et les vraies réponses de Claude, qui exigent une clé d'API.

Pour vérifier votre propre travail au fil des TODO :

```bash
LAB_TARGET=starter .venv/bin/python -m pytest tests
```

## Nettoyer

Le lab ne crée aucune ressource AWS et n'entraîne aucun coût récurrent. Pour libérer l'espace disque :

```bash
bash ../cleanup.sh       # depuis le dossier du lab : supprime ./index, chunks.jsonl et les deux modèles
deactivate
cd ../.. && rm -rf m07-rag-assistant-citations/.venv   # l'environnement virtuel du lab, quand vous avez fini
```

`cleanup.sh` supprime `models--intfloat--multilingual-e5-small` et `models--cross-encoder--mmarco-mMiniLMv2-L12-H384-v1` de `${HF_HOME:-~/.cache/huggingface}/hub`, comme le nettoyage de la leçon. Si vous avez créé une clé d'API pour ce lab, désactivez-la dans la Claude Console.

## Changer de modèle

- **Un autre modèle Claude** : modifiez `MODELE` (et `PRIX`) dans `assistant.py` pour les réponses, ou dans `contextualiser.py` pour les contextes. Gardez la formule d'abstention mot pour mot dans le prompt système : `evaluation.py` la détecte par comparaison de texte.
- **D'autres embeddings ou un autre reranker** : modifiez `MODELE_EMBEDDINGS` (dans `ingestion.py` et `index.py`) et `MODELE_RERANKER` (dans `recherche.py`), puis relancez `ingestion.py` et `index.py` : le nom du modèle est enregistré dans les métadonnées de la collection, pour savoir quand réindexer.
- **Amazon Bedrock (facultatif, hors leçon)** : `pip install -r ../requirements-bedrock.txt`, puis

  ```bash
  export MODEL_PROVIDER=bedrock
  export BEDROCK_MODEL_ID="<identifiant d'un modèle activé dans votre compte>"
  export BEDROCK_CONTEXT_MODEL_ID="<facultatif, pour contextualiser.py ; par défaut BEDROCK_MODEL_ID>"
  export AWS_REGION=eu-west-3
  python assistant.py "Je suis en CDD depuis huit mois, ai-je droit au télétravail ?"
  python evaluation.py --generation
  ```

  `bedrock.py` envoie les mêmes passages en blocs `searchResult` de l'API Converse, citations activées, et la contextualisation avec un `cachePoint` après le document. Il convertit la réponse Converse dans la forme qu'attendent `mettre_en_forme()`, `sources_citees()` et `evaluation.py` : la sortie et l'évaluation ne changent pas. Ce qui change : pas de `fallbacks` côté serveur sur Bedrock (une requête bloquée, `content_filtered` ou `guardrail_intervened`, affiche le message de refus), les blocs de résultats de recherche exigent un modèle qui les accepte, et aucun coût n'est calculé, les tarifs Bedrock dépendant du modèle et de la région. La récupération ne change pas du tout. Aucun identifiant de modèle n'est écrit en dur.
