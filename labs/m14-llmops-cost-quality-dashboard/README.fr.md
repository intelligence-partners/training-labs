# Lab M14 : tableau de bord coût et qualité d'un agent

Code d'accompagnement du lab du module M14 (LLMOps) de la formation Intelligence Training :
*Lab : tableau de bord coût et qualité d'un agent*. [English version](README.md).

## Objectif

Construire le poste de pilotage d'un agent de tri de tickets qui tourne sur Claude Opus 5.5 via
Amazon Bedrock : traces OpenTelemetry vers CloudWatch, coût par tâche calculé à partir des
compteurs `usage`, métriques de qualité et de coût, jeu d'évaluation de huit tickets, tableau
de bord, trois alarmes et un budget. Livrer ensuite une version volontairement fautive du
prompt (`v2`) et vérifier que le dispositif détecte la régression de coût, la localise et la
fait corriger. Comptez une heure.

## Architecture

Trois flux partent de l'agent (`agent.py`, sur votre poste) : l'inférence vers Bedrock
(streaming, client `AnthropicBedrock`, point de terminaison `bedrock-runtime`, Région
eu-west-3, profil d'inférence `eu.anthropic.claude-opus-5-5`), les spans en OTLP vers
l'endpoint X-Ray (ADOT, Transaction Search, `aws/spans`), et les métriques métier vers
CloudWatch (`M14/AgentSupport`, avec et sans la dimension `PromptVersion`). Bedrock ajoute ses
métriques `AWS/Bedrock` et ses journaux d'invocation. Trois alarmes notifient un sujet SNS
puis un e-mail ; AWS Budgets envoie aussi un e-mail.

L'agent, son prompt, ses outils, ses tickets et ses noms de métriques restent en français,
comme dans la leçon, pour que ses commandes, son tableau de bord, ses alarmes et ses points de
contrôle fonctionnent tels quels. Les commentaires sont en anglais.

```text
m14-llmops-cost-quality-dashboard/
├── starter/       agent.py à compléter (marqueurs TODO de l'étape 5), verifier.py, providers.py
├── solution/      agent.py (agent instrumenté), verifier.py (étape 2), providers.py
├── infra/         Terraform des étapes 3, 4, 8, 9 et 10 (hashicorp/aws fixé à 6.72.0)
├── otel.env       variables ADOT de l'étape 6
├── cleanup.sh     nettoyage de la leçon (terraform destroy et ce que Terraform ne couvre pas)
├── tests/         tests hors ligne (Bedrock, CloudWatch, Converse et spans simulés)
└── test.sh        installe dans .venv et lance tous les contrôles, Terraform compris
```

La leçon crée les ressources AWS avec des commandes AWS CLI et des fichiers JSON ; ce dépôt
crée les mêmes ressources, avec les mêmes noms et réglages, avec Terraform. Les deux parcours
aboutissent au même état du compte : suivez l'un ou l'autre, pas les deux.

| Fichier ou commande de la leçon | Terraform (`infra/`) |
| --- | --- |
| Étape 3 : groupe de journaux, `confiance-bedrock.json`, `ecrire-journaux.json`, `journalisation.json` | `invocation_logging.tf` |
| Étape 4 : `transaction-search.json`, `update-trace-segment-destination` | `transaction_search.tf` (si `enable_transaction_search`) |
| Étape 8 : `tableau.json`, `put-dashboard` | `dashboard.tf`, `tableau.json.tftpl` |
| Étape 9 : sujet SNS et abonnement, `alarme-cout.json`, `alarme-reussite.json`, `alarme-cache.json` | `alarms.tf` (l'alarme de cache est la solution de l'exercice) |
| Étape 10 : `budget.json`, `notifications.json` | `budget.tf` |

## Prérequis

- Un **compte AWS de bac à sable**, jamais la production, et un profil AWS CLI v2 disposant des
  droits d'administration de ce compte.
- Le droit d'invoquer Claude Opus 5.5 dans Bedrock depuis eu-west-3 (le lab du module M12
  détaille l'accès aux modèles).
- Python 3.10 ou plus récent, Terraform 1.5.7 ou plus récent, et une adresse e-mail pour les
  notifications.
- Une console AWS ouverte sur la Région eu-west-3.

## Coût estimé

Tel que l'indique la leçon :

| Poste | Estimation |
| --- | --- |
| Inférence Claude Opus 5.5 (trois passages de huit tâches, dont un sans cache) | 1 à 3 $ selon la grille Bedrock en vigueur |
| Métriques personnalisées et alarmes | quelques centimes, au prorata (l'offre gratuite couvre 10 métriques et 10 alarmes) |
| Tableau de bord | gratuit dans la limite de 3 tableaux personnalisés |
| Journaux d'invocation et spans | quelques mégaoctets, moins de 0,10 $ |
| Budget sans action | gratuit |

Comptez **moins de 5 $** si vous faites le nettoyage à la fin.

## Étapes

| Étape de la leçon | Dans ce dépôt |
| --- | --- |
| 1. Préparer l'environnement | `.venv` + `pip install -r requirements.txt` (versions fixées) |
| 2. Vérifier l'accès au modèle | `python verifier.py` |
| 3. Activer la journalisation des invocations | `infra/invocation_logging.tf` |
| 4. Activer Transaction Search | `infra/transaction_search.tf`, variable `enable_transaction_search` |
| 5. Écrire l'agent instrumenté | `starter/agent.py` (TODO étape 5), `solution/agent.py` |
| 6. Lancer la version v1 avec ADOT | `source ../otel.env`, puis `PROMPT_VERSION=v1 opentelemetry-instrument python agent.py` |
| 7. Lire une trace | Console CloudWatch, Transaction Search, service `agent-support-m14` |
| 8. Le tableau de bord | `infra/dashboard.tf`, variable `model_id_observe` |
| 9. Le sujet SNS et trois alarmes | `infra/alarms.tf`, variables `alert_email`, `cost_alarm_threshold` |
| 10. Le budget | `infra/budget.tf` |
| 11. Livrer la version fautive | `PROMPT_VERSION=v2 opentelemetry-instrument python agent.py` |
| 12. Revenir en arrière et mesurer | `PROMPT_VERSION=v1 opentelemetry-instrument python agent.py` |

## Lancer le lab

```bash
git clone https://github.com/intelligence-partners/training-labs.git
cd training-labs/labs/m14-llmops-cost-quality-dashboard
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export AWS_PROFILE=<votre profil de bac à sable> AWS_REGION=eu-west-3
aws sts get-caller-identity --query Account --output text
(cd solution && python verifier.py)     # étape 2 : end_turn ['prêt'] ...
```

### Avant d'appliquer (étapes 3 et 4)

Bedrock garde une seule configuration de journalisation par compte et par Région, et
appliquer `infra/` la remplace. Sauvegardez d'abord l'actuelle ; `cleanup.sh` la restaure à la
fin :

```bash
aws bedrock get-model-invocation-logging-configuration --query loggingConfig --output json \
  > infra/previous-logging-config.json
aws xray get-trace-segment-destination
```

Si la destination X-Ray est déjà `CloudWatchLogs` avec le statut `ACTIVE`, mettez
`enable_transaction_search = false` : le lab laisse alors Transaction Search tel quel, et le
nettoyage ne le désactive pas.

### Créer les ressources (étapes 3, 4, 8, 9, 10)

```bash
cp infra/terraform.tfvars.example infra/terraform.tfvars   # renseignez alert_email et enable_transaction_search
terraform -chdir=infra init
terraform -chdir=infra apply
```

Confirmez l'abonnement SNS depuis l'e-mail reçu. Après le premier passage v1 (étape 6),
réglez `cost_alarm_threshold` au double du coût moyen par tâche relevé, et `model_id_observe`
sur la valeur renvoyée par la commande ci-dessous, puis relancez
`terraform -chdir=infra apply` :

```bash
aws cloudwatch list-metrics --namespace AWS/Bedrock --metric-name Invocations \
  --query 'Metrics[].Dimensions[?Name==`ModelId`].Value' --output text
```

### Lancer l'agent (étapes 6, 11, 12)

```bash
cd solution          # ou starter, une fois ses TODO complétés
source ../otel.env
PROMPT_VERSION=v1 opentelemetry-instrument python agent.py
PROMPT_VERSION=v2 opentelemetry-instrument python agent.py   # étape 11 : la version fautive
PROMPT_VERSION=v1 opentelemetry-instrument python agent.py   # étape 12 : retour arrière
aws cloudwatch describe-alarms --alarm-name-prefix m14- \
  --query 'MetricAlarms[].[AlarmName,StateValue]' --output table
```

Si un appel apparaît deux fois dans les traces, une autre instrumentation trace déjà le SDK :
relancez avec `ANTHROPIC_OPEN_TELEMETRY=false`.

## Tester

```bash
bash test.sh
```

Le script crée `.venv`, installe `requirements-dev.txt`, lance les tests unitaires sur
`solution/`, vérifie que `starter/` se compile et s'importe, contrôle les scripts shell, puis
lance `terraform fmt -check -recursive`, `terraform init -backend=false` et
`terraform validate` sur `infra/` (`SKIP_TERRAFORM=1` pour les sauter). Aucun identifiant AWS
n'est nécessaire : les appels Bedrock passent par un transport simulé derrière un vrai client
du SDK Anthropic, les appels CloudWatch et Converse par le Stubber de botocore (validés contre
les modèles de service), et les spans par un exportateur en mémoire. Les tests vérifient aussi
que chaque métrique lue par le tableau de bord et les alarmes est bien publiée par l'agent.

## Nettoyer

```bash
bash cleanup.sh        # ou AUTO_APPROVE=1 bash cleanup.sh
deactivate && rm -rf .venv
```

`cleanup.sh` lance `terraform destroy` (budget, alarmes, tableau de bord, sujet SNS et son
abonnement, journalisation des invocations, groupe de journaux, rôle IAM, politique de
ressource de Transaction Search), puis, seulement si le lab a activé Transaction Search,
repasse X-Ray sur `XRay` et supprime `aws/spans` (Terraform ne modifie pas X-Ray à la
destruction). Si vous avez sauvegardé une configuration de journalisation Bedrock, il la
restaure. Les métriques personnalisées `M14/AgentSupport` ne se suppriment pas : elles cessent
d'être alimentées, leur facturation au prorata horaire s'arrête, et elles disparaissent
d'elles-mêmes de la console.

## Changer de modèle

- **Un autre modèle Claude ou profil d'inférence sur Bedrock** : réglez `MODEL_ID` (la
  variable de la leçon), et `model_id_observe` pour le tableau de bord.
- **Une autre famille de modèles sur Bedrock** (Amazon Nova, Meta Llama, Mistral AI…) :
  réglez `MODEL_PROVIDER=bedrock` et `MODEL_ID` sur un identifiant activé dans votre compte.
  L'agent passe alors par l'API Converse de boto3 (`bedrock-runtime`), via `providers.py`, sans
  modification de code. Renseignez `PRICE_SHEET` avec les tarifs de ce modèle, sinon les coûts
  et l'alarme de coût sont faux :

  ```bash
  export MODEL_PROVIDER=bedrock MODEL_ID=<identifiant du modèle>
  export PRICE_SHEET='{"input": ..., "cache_write": ..., "cache_read": ..., "output": ...}'
  ```

  Avec Converse, `cache_control` devient un point de cache, les outils gardent `strict`, et
  `effort` n'est pas envoyé (il est propre à Claude) ; `BEDROCK_CACHE_POINTS=false`,
  `BEDROCK_STRICT_TOOLS=false` et `BEDROCK_MAX_TOKENS` adaptent la requête à un modèle qui ne
  gère pas une de ces fonctions. L'adaptateur appelle `Converse`, pas `ConverseStream` : la
  métrique `TimeToFirstToken` d'`AWS/Bedrock` n'est pas alimentée dans ce mode.
- Pour comparer deux familles sur le même tableau de bord, comme le suggère la leçon dans
  « Pour aller plus loin », ajoutez une dimension modèle aux métriques métier dans
  `publier()` : ce dépôt ne le fait pas.
