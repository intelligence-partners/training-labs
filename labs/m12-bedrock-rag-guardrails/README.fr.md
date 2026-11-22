# Lab M12 : un assistant RAG sur Amazon Bedrock, avec Knowledge Bases et Guardrails

Code d'accompagnement du lab pratique du module M12 (Amazon Bedrock) d'Intelligence Training.
[English version](README.md)

Vous construisez, sur votre propre compte AWS à Paris (`eu-west-3`), un assistant RH interne : un
collaborateur pose une question par une API HTTP, une fonction Lambda récupère les passages utiles
dans une base de connaissances, Claude Opus 5.5 rédige la réponse, et un guardrail filtre la
question et la réponse. Le lab dure environ 75 minutes et se termine par un nettoyage complet.

## Objectif

Une requête `POST` sur votre API renvoie un JSON avec la réponse (`reponse`), les documents sources
(`sources`), la raison d'arrêt (`stopReason`) et le verdict du guardrail (`guardrail`). Cinq
comportements doivent être observés :

1. une question couverte par les documents reçoit une réponse correcte, avec sa source ;
2. une réponse qui contient un numéro de téléphone le voit masqué ;
3. une tentative de détournement est bloquée à l'entrée ;
4. une demande de conseil juridique individuel est refusée ;
5. une question hors du périmètre des documents ne reçoit pas de réponse inventée.

## Architecture

Les collaborateurs appellent une **API HTTP** (Amazon API Gateway, création rapide). L'API invoque
la **fonction Lambda** `lab-rag-rh`, qui :

1. appelle **Retrieve** sur la base de connaissances `kb-lab-rh` (4 passages). La base est alimentée
   par le bucket `lab-rag-rh-<compte>` et range ses vecteurs (Titan Text Embeddings V2, 1 024
   dimensions) dans une collection **OpenSearch Serverless** ;
2. appelle l'API **Converse** avec le profil d'inférence `eu.anthropic.claude-opus-5-5`, les passages
   qualifiés comme source d'ancrage et la question comme requête, sous le guardrail `lab-rag-rh`
   (niveau Classic) en entrée et en sortie.

Journaux et traces vont dans CloudWatch. Les choix de conception viennent de la leçon : un magasin
vectoriel géré par vous (OpenSearch Serverless), pas de reranking, Retrieve puis Converse plutôt
que RetrieveAndGenerate (pour maîtriser le prompt et qualifier les blocs du guardrail), et le niveau
Classic du guardrail.

Toute l'infrastructure est en **Terraform** (`hashicorp/aws` 6.73.0). Deux étapes restent des
appels CLI parce que ce sont des actions, pas des ressources : le job d'ingestion (étape 3) et les
tests.

## Organisation du dossier

```text
m12-bedrock-rag-guardrails/
├── README.md, README.fr.md
├── .env.example            variables à adapter (région, modèle, noms), aucun secret
├── test.sh                 vérifications hors ligne (CI)
├── cleanup.sh              terraform destroy, puis vérifie qu'il ne reste rien
├── requirements-dev.txt    versions épinglées pour les vérifications hors ligne
├── tests/                  tests unitaires (appels AWS simulés) et contrôles statiques du Terraform
├── solution/               le lab complet
│   ├── docs/               les trois documents et leurs fichiers .metadata.json (étape 1)
│   ├── lambda/app.py       la fonction (étape 6)
│   ├── index_builder/      fonction utilitaire qui crée l'index vectoriel (étape 2)
│   ├── terraform/          versions.tf, variables.tf, s3.tf (étape 1), opensearch.tf et
│   │                       knowledge_base.tf (étape 2), guardrail.tf (étape 5), lambda.tf (étape 6),
│   │                       api.tf (étape 7), outputs.tf
│   └── scripts/            00-check-model.sh, lab-env.sh, 03-sync.sh ... 08-test-behaviours.sh
└── starter/                la même arborescence, avec des marqueurs TODO (step N) là où vous écrivez
```

## Prérequis

- Un compte AWS **de test** où vous avez des droits d'administration, et l'accès aux modèles
  Anthropic ouvert (formulaire de cas d'usage soumis une fois, voir la première leçon du module).
- La région **eu-west-3** (Paris).
- **AWS CLI v2** configurée : `aws sts get-caller-identity` répond.
- **Terraform 1.5.7 ou plus** (code testé avec 1.5.7 ; fournisseurs épinglés dans `versions.tf` et
  `.terraform.lock.hcl`).
- `curl` et `jq`.
- Pour les vérifications hors ligne seulement : Python 3.10 ou plus (la CI utilise 3.12).

## Coût estimé

Tel que la leçon l'indique :

| Élément | Estimation |
| --- | --- |
| Collection OpenSearch Serverless | la documentation de Bedrock ne précise pas la génération de la collection créée rapidement : comptez le cas classique, 1 OCU d'indexation et 1 OCU de recherche au minimum, facturés même sans requête, à environ 0,24 $ par OCU-heure en us-east-1 (vérifiez le tarif de Paris), soit près de 0,50 $ par heure et de l'ordre de 350 $ par mois si elle reste en place. Un groupe de nouvelle génération peut descendre à 0 OCU au repos, mais ne comptez pas dessus ici |
| Claude Opus 5.5 | une trentaine de requêtes de quelques milliers de tokens : moins d'un dollar |
| Embeddings Titan, guardrail | quelques centimes |
| Lambda, API Gateway, S3, CloudWatch | négligeable, souvent couvert par l'offre gratuite |
| **Total si vous nettoyez le jour même** | **moins de 5 $** |

> Créez une alerte AWS Budgets à 10 $ sur le compte avant de commencer. Et ne passez pas à la suite
> d'une session de travail sans avoir fait le nettoyage : une collection OpenSearch Serverless de
> génération classique oubliée coûte de l'ordre de 350 dollars par mois.

## Les étapes de la leçon dans ce dossier

| Étape de la leçon | Ce que vous lancez | Où est le code |
| --- | --- | --- |
| 0. Préparer | `./scripts/00-check-model.sh` | vérification du profil et premier appel Converse |
| 1. Déposer les documents | `terraform apply` | `docs/`, `terraform/s3.tf` |
| 2. Créer la base | `terraform apply` | `terraform/opensearch.tf`, `terraform/knowledge_base.tf` |
| 3. Synchroniser | `./scripts/03-sync.sh` | `start-ingestion-job`, puis `get-ingestion-job` jusqu'à `COMPLETE` |
| 4. Vérifier la récupération | `./scripts/04-retrieve.sh` | deux appels `retrieve`, le second filtré sur `service` |
| 5. Créer le guardrail | `terraform apply`, puis `./scripts/05-test-guardrail.sh` | `terraform/guardrail.tf` |
| 6. Déployer la fonction | `terraform apply`, puis `./scripts/06-invoke-function.sh` | `lambda/app.py`, `terraform/lambda.tf` |
| 7. Exposer une API HTTP | `terraform apply`, puis `./scripts/07-ask.sh` | `terraform/api.tf` |
| 8. Tester les cinq comportements | `./scripts/08-test-behaviours.sh` | |
| Nettoyage | `../cleanup.sh` | `cleanup.sh` |

## Déployer

```bash
git clone https://github.com/intelligence-partners/training-labs.git
cd training-labs/labs/m12-bedrock-rag-guardrails/solution     # ou starter/, voir plus bas
export AWS_REGION=eu-west-3

./scripts/00-check-model.sh                  # étape 0 : ARN de modèles dans l'Union, puis OK
terraform -chdir=terraform init
terraform -chdir=terraform apply             # étapes 1, 2, 5, 6 et 7 (la collection est la plus longue)
eval "$(./scripts/lab-env.sh)"               # BUCKET, KB_ID, DS_ID, COLL_ARN, GR_ID, API_URL...
aws s3 ls "s3://$BUCKET/docs/"               # étape 1 : six objets
./scripts/03-sync.sh                         # étape 3 : COMPLETE, 3 documents indexés
./scripts/04-retrieve.sh                     # étape 4
./scripts/05-test-guardrail.sh               # étape 5 : GUARDRAIL_INTERVENED
./scripts/06-invoke-function.sh              # étape 6 : statusCode 200, « deux jours »
./scripts/07-ask.sh "Combien de jours de télétravail par semaine ?"   # étape 7
./scripts/08-test-behaviours.sh              # étape 8
```

`lab-env.sh` écrit aussi les identifiants dans `lab-ids.env`, pour les garder si votre terminal se
ferme.

Pour suivre la leçon étape par étape (et avec le **starter**, où vous complétez les blocs
`TODO (step N)`), déployez d'abord les étapes 1 et 2, puis le reste :

```bash
# après TODO (step 1) et TODO (step 2)
terraform -chdir=terraform apply -target=aws_bedrockagent_data_source.docs
./scripts/03-sync.sh && ./scripts/04-retrieve.sh
# après TODO (step 5), (step 6) et (step 7)
terraform -chdir=terraform apply
```

> L'API n'a pas d'authentification : elle est publique tant qu'elle existe. C'est acceptable pour un
> lab de quelques heures sur des documents fictifs, jamais en production (autorisateur JWT ou
> authentification IAM). Une API HTTP coupe l'intégration à 30 secondes : la réponse est
> volontairement courte et l'effort bas.

## Tester

Sur AWS, comparez chaque réponse de `08-test-behaviours.sh` au tableau de la leçon (25 euros et
`notes-de-frais.md` ; `{PHONE}` et « masqué » ; blocage d'entrée et « bloqué » ; sujet refusé ;
pas de réponse inventée). Hors ligne, sans compte AWS :

```bash
./test.sh
```

Le script crée `.venv`, installe les versions épinglées, lance les tests unitaires, vérifie les
scripts shell (`bash -n`, ShellCheck), puis lance `terraform fmt -check`,
`terraform init -backend=false` et `terraform validate` sur `solution/terraform` et
`starter/terraform`.

## Nettoyer

```bash
cd training-labs/labs/m12-bedrock-rag-guardrails
./cleanup.sh               # ou ./cleanup.sh starter ; --yes pour ne pas confirmer
```

`terraform destroy` supprime, dans l'ordre des dépendances, l'API, les fonctions et leurs groupes de
journaux, les rôles, le guardrail et sa version, la source de données, la base de connaissances,
l'index vectoriel, la collection OpenSearch Serverless et ses trois politiques, le bucket et ses
documents. Supprimer une base ne supprime pas sa collection : ici la collection est une ressource
Terraform à part entière, elle part donc aussi. Le script lance ensuite les vérifications de la leçon
(collections, bases, guardrails) et sort en erreur s'il reste une ressource du lab. Le lendemain,
contrôlez dans Billing que la ligne OpenSearch Serverless ne progresse plus.

## Changer de modèle

Bedrock est multi-modèle : l'API Converse fonctionne avec toute famille de modèles ouverte sur votre
compte.

```bash
aws bedrock list-inference-profiles --query 'inferenceProfileSummaries[].inferenceProfileId'
terraform -chdir=terraform apply -var model_id=<identifiant du profil> -var model_effort=""
```

La politique IAM de la fonction suit le profil : Terraform lit dans le profil lui-même les régions
vers lesquelles il route. `model_effort` est un réglage propre à Anthropic, transmis par
`additionalModelRequestFields` ; laissez-le vide pour une autre famille. La base, le guardrail et le
code de la fonction ne changent pas. Vérifiez d'abord l'accès avec
`MODEL_ID=<identifiant du profil> ./scripts/00-check-model.sh`.

## Ce que couvrent les vérifications hors ligne

- La fonction : validation des requêtes, requêtes Retrieve et Converse exactes (validées contre les
  modèles de service de botocore par `Stubber`), sources, verdicts, et absence des valeurs de la
  trace dans la réponse.
- La fonction de création d'index : nouvelles tentatives pendant la propagation de la politique
  d'accès, idempotence, erreurs, signature SigV4 pour `aoss`.
- Le Terraform : noms et réglages de la leçon, politiques du guardrail, moindre privilège,
  fournisseurs épinglés ; `terraform validate` contre le schéma du fournisseur épinglé.
- Les documents et leurs métadonnées ; l'import du starter et ses marqueurs TODO.

Seul un vrai déploiement peut montrer : l'accès au modèle sur votre compte, les réponses de Bedrock
et les verdicts du guardrail, les statistiques d'ingestion, le délai de propagation de la politique
d'accès OpenSearch Serverless (la fonction de création d'index réessaie pendant 4 minutes), et la
transmission de `output_config.effort` à Claude Opus 5.5 par `additionalModelRequestFields`.

## Remarques sur le code Terraform

- Terraform crée le magasin vectoriel que produirait la création rapide de la console : la collection, ses politiques de chiffrement, de réseau et d'accès aux données, et
  l'index vectoriel avec les noms de champs de la création rapide. Ni `hashicorp/aws` ni `awscc` ne
  savent créer un index k-NN (`awscc_opensearchserverless_collection_index` s'appuie sur l'API
  `CreateIndex`, qui crée des index à enrichissement sémantique automatique) : une petite fonction
  signe l'appel OpenSearch et Terraform l'invoque une fois (`aws_lambda_invocation`).
- Le rôle de la base est `lab-rag-rh-kb`, créé par Terraform, plutôt que le rôle
  `AmazonBedrockExecutionRoleForKnowledgeBase_*` que créerait la console : rien n'est à supprimer à
  la main.
- La fonction n'écrit que dans son propre groupe de journaux, au lieu de la politique gérée
  `AWSLambdaBasicExecutionRole`. Chaque ressource porte les tags `Course`, `Lab` et `ManagedBy`.
- L'état Terraform reste local (`terraform/terraform.tfstate`, ignoré par Git).
