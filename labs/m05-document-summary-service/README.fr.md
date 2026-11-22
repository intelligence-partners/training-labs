# Lab m05 : un service de synthèse de documents

Code d'accompagnement du lab qui clôt le module **M05, L'API Claude en profondeur**, du parcours Intelligence Training (leçon « Lab : un service de synthèse de documents »). Version anglaise : [README.md](README.md).

## Objectif

Un service en ligne de commande qui prend un PDF, le téléverse une seule fois, demande à Claude une synthèse structurée adaptée à un profil de lecteur (`direction`, `juridique`, `operationnel`), vérifie la réponse avant de la transmettre et affiche ce que l'appel a coûté. Un second profil sur le même document relit le PDF depuis le cache de prompt, pour une fraction du prix.

```bash
python main.py rapport.pdf --profil direction > synthese-direction.json
```

## Architecture

Quatre fichiers, comme dans la leçon :

| Fichier | Rôle |
| --- | --- |
| `schema.py` | Le schéma JSON envoyé à l'API (`SCHEMA_SYNTHESE`) et le modèle Pydantic qui revalide la sortie (`Synthese`), règles métier comprises |
| `fichiers.py` | Le téléversement par la Files API, avec un index local (`.fichiers.json`, empreinte SHA-256 du PDF vers `file_id`) pour ne jamais envoyer deux fois le même PDF |
| `service.py` | L'appel à Claude (`synthetiser()`), les contrôles et le coût (`cout_estime()`) |
| `main.py` | La ligne de commande, avec un code de sortie par famille d'erreur |

`main.py` passe le chemin du PDF à `fichiers.py`, qui ne le téléverse que s'il est nouveau ; il transmet ensuite le `file_id` et le profil à `service.py`, qui appelle la Messages API avec un prompt système figé, le document comme point de cache, une sortie structurée (`output_config.format`), `effort: "medium"` et le repli côté serveur `fallbacks="default"`. La réponse passe trois contrôles avant d'être rendue : `stop_reason` (refus, troncature), le schéma Pydantic, les règles métier (trois à sept points clés, numéros de page d'au moins 1).

Codes de sortie : `0` succès, `2` pas un PDF, `3` synthèse non fiable (refusée, tronquée, invalide), `4` authentification, `5` limite de débit, `6` autre erreur d'API, `7` connexion.

## Deux éditions du code

Les identifiants (noms de fichiers, de fonctions, de classes et de champs JSON) sont ceux des deux éditions de la leçon. Les textes affichés suivent la langue de la leçon que vous lisez :

| Dossiers | Leçon | Prompts et messages |
| --- | --- | --- |
| `starter/`, `solution/` | Leçon française | Français (`Synthèse impossible : sortie tronquée : ...`) |
| `starter-en/`, `solution-en/` | Leçon anglaise (`content-en`) | Anglais (`Summary failed: output truncated: ...`) |

```text
m05-document-summary-service/
├── README.md, README.fr.md
├── .env.example            variables lues par le lab
├── requirements.txt        anthropic, pydantic (étape 1)
├── requirements-bedrock.txt  + boto3, pour la variante Bedrock facultative
├── requirements-dev.txt    + pytest, pour les tests
├── test.sh                 contrôles hors ligne (lancés aussi par la CI)
├── cleanup.sh              supprime les fichiers téléversés dans la Files API
├── starter/ starter-en/    le code de départ, avec des marqueurs TODO(step N)
│   └── ts/                 la variante TypeScript (étape 8), avec ses TODO
├── solution/ solution-en/  le code complet
│   ├── schema.py fichiers.py service.py main.py
│   ├── bedrock.py          sélecteur de fournisseur facultatif (hors leçon)
│   └── ts/synthese.ts      la variante TypeScript (étape 8)
└── tests/                  tests hors ligne : tout appel de modèle ou d'AWS est simulé
```

## Prérequis

Ceux de la leçon :

- Python 3.10 ou plus, un terminal, un compte Claude Console et une clé d'API dans `ANTHROPIC_API_KEY` (ou un profil créé avec `ant auth login`).
- Un PDF de 10 à 40 pages sans mot de passe : rapport d'activité, contrat type, compte rendu public. Évitez les documents confidentiels de vos clients pour un exercice.
- Aucune ressource AWS : le lab utilise uniquement l'API Claude.
- Accès au modèle : `claude-opus-5-5` sur l'API Claude.
- Facultatif, étape 8 : Node.js 20 ou plus pour la variante TypeScript.
- Facultatif, variante Bedrock : un compte AWS avec accès à un modèle Bedrock qui accepte les documents PDF et la sortie structurée, et des identifiants AWS sur votre poste.

Testé avec Python 3.12, Node.js 20, `anthropic` 2.12.0, `pydantic` 2.14.4, `@anthropic-ai/sdk` 1.12.0, `zod` 4.6.7, `boto3` 1.44.9 (versions exactes dans les fichiers requirements et `package.json`).

## Coût estimé

Tel que la leçon l'indique : **moins de 1 $ pour l'ensemble du lab** avec un PDF d'une vingtaine de pages sur `claude-opus-5-5`. La première synthèse paie l'écriture du document dans le cache (5 $ par million de tokens), les suivantes le relisent à 0,20 $ par million. Les opérations de la Files API sont gratuites.

Les tests de ce dépôt ne coûtent rien : ils n'appellent jamais de modèle.

## Lancer le lab

```bash
git clone https://github.com/intelligence-partners/training-labs.git
cd training-labs/labs/m05-document-summary-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."   # ou un profil créé avec « ant auth login »
cd starter                               # complétez les TODO ; ou cd solution pour le code terminé
cp ~/Documents/mon-rapport.pdf rapport.pdf   # un PDF de 10 à 40 pages
```

Puis suivez les étapes de la leçon :

| Étape de la leçon | Où | Commande |
| --- | --- | --- |
| 1. Préparer l'environnement | les commandes ci-dessus | `python -c "import anthropic, pydantic; print(anthropic.__version__, pydantic.VERSION)"` |
| 2. Écrire le schéma | `schema.py`, `TODO(step 2)` | |
| 3. Téléverser une seule fois | `fichiers.py`, `TODO(step 3)` | `python -c "import anthropic, pathlib; from fichiers import file_id_pour; print(file_id_pour(anthropic.Anthropic(), pathlib.Path('rapport.pdf')))"` |
| 4. Appeler le modèle et contrôler la réponse | `service.py`, `TODO(step 4a/4b/4c)` | |
| 5. La ligne de commande et les erreurs | `main.py`, `TODO(step 5)` | `python main.py rapport.pdf --profil direction > synthese-direction.json` |
| 6. Vérifier le cache | | `python main.py rapport.pdf --profil juridique > synthese-juridique.json` (dans les cinq minutes) |
| 7. Provoquer les cas d'échec | | `SYNTHESE_MAX_TOKENS=300 python main.py rapport.pdf --profil operationnel; echo "code de sortie : $?"` |
| 8. (facultative) Variante TypeScript | `ts/synthese.ts`, `TODO(step 8)` | `cd ts && npm ci && npx tsx synthese.ts ../rapport.pdf direction` |

Les lignes d'usage et de coût vont sur la sortie d'erreur ; la synthèse JSON sur la sortie standard.

## Tester

```bash
bash test.sh
```

`test.sh` crée `.venv`, installe `requirements-dev.txt`, lance `npm ci` et la vérification de types TypeScript dans chaque dossier `ts/`, compile et importe les deux starters, puis lance les tests sur `solution/` et `solution-en/`. Ni clé d'API, ni identifiants AWS, ni accès réseau à Claude : une fausse API locale répond aux vrais SDK (Python et TypeScript) en HTTP, et le `Stubber` de botocore répond à Bedrock en validant chaque requête contre le modèle de service.

Ce que couvrent les tests :

- le schéma et les règles métier (étape 2) ;
- le téléversement unique et l'index, y compris la requête multipart envoyée par le SDK (étape 3) ;
- la requête exacte (modèle, effort, schéma, point de cache sur le document, `fallbacks`, en-tête bêta, version d'API `2026-10-21`), un préfixe identique d'un profil à l'autre, et chaque contrôle : refus avec sa catégorie, troncature (`max_tokens`, `model_context_window_exceeded`), motif de fin inattendu, JSON invalide et règles enfreintes (étape 4) ;
- chaque code de sortie et message de `main.py`, le nouveau téléversement quand un `file_id` a été supprimé, et les lignes de coût de la leçon (`0.3678 $` puis `0.0717 $`) (étapes 5 et 6) ;
- les commandes shell des étapes 3, 5, 6 et 7, lancées telles quelles dans un dossier neuf ;
- la variante TypeScript, vérifiée par le compilateur et exécutée de bout en bout contre la fausse API (étape 8) ;
- `cleanup.sh` ;
- la variante Bedrock facultative.

Pour vérifier votre propre travail au fil des TODO :

```bash
LAB_TARGET=starter .venv/bin/python -m pytest tests      # ou LAB_TARGET=starter-en
```

## Nettoyer

Le lab ne crée aucune ressource AWS. Il laisse des PDF dans la Files API de votre workspace Claude, listés dans `.fichiers.json` ; ils persistent jusqu'à leur suppression :

```bash
bash ../cleanup.sh            # depuis le dossier où vous avez lancé main.py
```

`cleanup.sh` reprend le code de nettoyage de la leçon : il supprime chaque `file_id` de l'index, puis l'index. La variante TypeScript téléverse le PDF à chaque lancement : listez vos fichiers avec `client.files.list()` et supprimez ceux qui portent le nom de votre PDF. Si vous avez créé une clé d'API dédiée au lab, révoquez-la dans la Console.

## Changer de modèle

- **Un autre modèle Claude** : modifiez `MODELE` dans `service.py` (et `PRIX`, pour que la ligne de coût reste juste). Gardez `fallbacks="default"` : en cas de refus, l'API relance sur un modèle de repli, et la ligne « modèle » indique celui qui a répondu.
- **Amazon Bedrock (facultatif, hors leçon)** : `pip install -r ../requirements-bedrock.txt`, puis

  ```bash
  export MODEL_PROVIDER=bedrock
  export BEDROCK_MODEL_ID="<identifiant d'un modèle activé dans votre compte>"
  export AWS_REGION=eu-west-3        # ou la région de votre profil
  python main.py rapport.pdf --profil direction
  ```

  `bedrock.py` envoie le même prompt système, le même profil et le même schéma JSON par l'API Converse de Bedrock Runtime, avec un `cachePoint` après le document, et applique les trois mêmes contrôles avec les mêmes codes de sortie. Ce qui change : Bedrock n'a pas de Files API (les octets du PDF partent dans chaque requête, rien à nettoyer), pas de `fallbacks` côté serveur (une requête bloquée, `content_filtered` ou `guardrail_intervened`, se termine en code 3), et la ligne de coût n'est pas calculée, les tarifs Bedrock dépendant du modèle et de la région. Le modèle doit accepter les documents PDF et la sortie structurée ; aucun identifiant de modèle n'est écrit en dur.
