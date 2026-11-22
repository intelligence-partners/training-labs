# Lab M13 : l'agent de support d'Acme sur Amazon Bedrock AgentCore

Code d'accompagnement du lab pratique du module M13 (Amazon Bedrock AgentCore) d'Intelligence
Training : l'agent de support « fil rouge », qui assemble tout le module.
[English version](README.md)

Vous construisez l'agent de support d'Acme, un site de vente en ligne fictif : il lit l'état des
commandes, ouvre des tickets et rembourse, mais **jamais plus de 50 euros**, et cette limite ne
dépend pas du modèle. Il se souvient des préférences de chaque client d'une session à l'autre et
chacune de ses actions est tracée. Vous partez d'une « API existante », comme dans une vraie
mission, sans en modifier une ligne.

## Architecture

Vous invoquez le runtime `agent`, qui raisonne avec Claude Opus 5.5 par le profil d'inférence
européen `eu.anthropic.claude-opus-5-5` et lit sa mémoire. Il appelle la Gateway `tools`, dont le
moteur Policy décide de chaque appel. La Gateway récupère la clé API dans Identity et appelle l'API
HTTP d'Acme, servie par une Lambda. Les traces et journaux vont dans CloudWatch.

| Brique | Rôle dans le lab |
| --- | --- |
| Runtime | Héberge l'agent Strands (`SupportLab/app/agent/main.py`), une microVM par session |
| Memory | Garde l'historique et extrait les préférences de chaque client |
| Gateway | Expose l'API REST d'Acme comme trois outils MCP : `support___getOrder`, `support___createTicket`, `support___createRefund` |
| Identity | Garde la clé de l'API dans le coffre de jetons ; la Gateway l'injecte dans l'en-tête `x-api-key` |
| Policy | Autorise lectures et tickets, et les remboursements jusqu'à 5 000 centimes |
| Observability | Traces, journaux et métriques de décision dans CloudWatch |

Tout se passe dans la région **Paris (`eu-west-3`)**, où la leçon indique que chacune de ces briques
est disponible au 27 octobre 2026.

L'infrastructure est en **Terraform** (`hashicorp/aws` 6.73.0), en deux piles : `terraform/acme-api`
(l'API existante, telle qu'elle existerait avant la mission) et `terraform/support-agent` (runtime,
mémoire, Identity, Gateway, Policy, évaluation en ligne). La CLI AgentCore ne sert que de client
(`invoke`, `memory record list`, `runtime traces`, `runtime logs`, `eval ondemand`) : rien n'est
déployé avec CDK ni CloudFormation.

## Organisation du dossier

```text
m13-agentcore-support-agent/
├── README.md, README.fr.md
├── .env.example              variables à adapter (région, modèle, noms), aucun secret
├── test.sh                   vérifications hors ligne (CI)
├── cleanup.sh                terraform destroy des deux piles, puis ce que Terraform ne possède pas
├── requirements-dev.txt      le verrou de l'agent et les outils de test
├── tests/                    tests unitaires (faux modèle, outils locaux, moteur Cedar) et contrôles Terraform
├── solution/
│   ├── acme-api/app.py       l'API existante (étape 1)
│   ├── SupportLab/
│   │   ├── app/agent/        main.py, gateway_client.py, memory/session.py (étape 5),
│   │   │                     pyproject.toml et requirements.txt (verrou épinglé)
│   │   ├── schemas/          acme-support.template.json (étape 3)
│   │   └── policies/         lecture, remboursement et b2b .template.cedar (étape 7)
│   ├── terraform/
│   │   ├── acme-api/         main.tf, variables.tf, outputs.tf, versions.tf (étape 1)
│   │   └── support-agent/    memory.tf (étape 2), gateway.tf (étapes 3 et 4), identity.tf (étape 4),
│   │                         runtime.tf (étape 6), policy.tf (étape 7), online_eval.tf (étape 10)
│   └── scripts/              check_api.sh, lab-env.sh, package_agent.sh, enable_transaction_search.sh
└── starter/                  la même arborescence, avec des marqueurs TODO (step N) là où vous écrivez
```

## Prérequis

- Un compte AWS de **bac à sable**, avec des droits d'administration (le lab crée des rôles IAM) et
  un budget AWS configuré (module M10).
- **AWS CLI v2** configurée : `aws sts get-caller-identity` doit répondre.
- **Terraform 1.5.7 ou plus** (testé avec 1.5.7 ; fournisseurs épinglés dans `versions.tf` et
  `.terraform.lock.hcl`).
- **Node.js 20.12 ou plus** et la CLI AgentCore, utilisée comme client :
  `npm install -g @aws/agentcore@1.0.1` (la version avec laquelle ces commandes ont été vérifiées).
- **Python 3.10 ou plus et `uv`** (pour construire l'artefact CodeZip ; testé avec uv 0.5.15), `jq`,
  `zip`, `curl`, `openssl`.
- L'accès aux modèles Anthropic dans Amazon Bedrock : une fois par compte, le formulaire de cas
  d'usage doit avoir été soumis depuis le catalogue de modèles de la console Bedrock.

## Coût estimé

Tel que la leçon l'indique : le lab ne crée que des ressources facturées à l'usage, sans engagement.
L'ordre de grandeur est de **quelques dollars** pour le lab complet si vous nettoyez le jour même,
l'essentiel étant les tokens de Claude (une vingtaine d'invocations, chacune avec plusieurs appels
au modèle). Le reste est marginal : Runtime facture à la seconde le CPU et la mémoire consommés,
Memory les événements et enregistrements, Gateway et Policy les appels, CloudWatch l'ingestion ; la
Lambda et l'API HTTP restent en général dans l'offre gratuite. Les prix changent : vérifiez les pages
de tarifs d'AgentCore et de Bedrock avant de commencer, et ne sautez pas l'étape de nettoyage.

## Les étapes de la leçon dans ce dossier

| Étape de la leçon | Ce que vous lancez | Où est le code |
| --- | --- | --- |
| 1. Déployer l'API existante | `terraform -chdir=terraform/acme-api apply`, `./scripts/check_api.sh` | `acme-api/app.py`, `terraform/acme-api/` |
| 2. Le projet AgentCore | rien à lancer : le projet est dans `SupportLab/` | `SupportLab/app/agent/`, `terraform/support-agent/memory.tf` |
| 3. Décrire l'API en OpenAPI | Terraform insère la vraie URL du serveur | `SupportLab/schemas/acme-support.template.json`, `terraform/support-agent/gateway.tf` |
| 4. La Gateway, la clé et la cible | `terraform apply` (étape 6) | `terraform/support-agent/identity.tf`, `gateway.tf` |
| 5. Le code de l'agent | `./scripts/package_agent.sh` | `gateway_client.py`, `main.py`, `memory/session.py` |
| 6. Déployer et tester | `terraform apply -var enable_policy=false`, `agentcore invoke` | `terraform/support-agent/runtime.tf` |
| 7. La règle de remboursement avec Policy | `terraform apply`, scénario | `SupportLab/policies/`, `terraform/support-agent/policy.tf` |
| 8. Vérifier la mémoire | `agentcore memory record list` | |
| 9. Observer | `agentcore runtime traces`, `agentcore runtime logs`, `aws cloudwatch list-metrics` | |
| 10. Évaluer (facultatif) | `terraform apply -var enable_online_eval=true`, `agentcore eval ondemand evaluate` | `terraform/support-agent/online_eval.tf` |
| Identity | `aws bedrock-agentcore-control list-api-key-credential-providers` | |
| Nettoyage | `../cleanup.sh` | `cleanup.sh` |

## Déployer et tester

```bash
git clone https://github.com/intelligence-partners/training-labs.git
cd training-labs/labs/m13-agentcore-support-agent/solution     # ou starter/
export AWS_REGION=eu-west-3
npm install -g @aws/agentcore@1.0.1

# Étape 1 : l'API existante, protégée par une clé
export ACME_API_KEY=$(openssl rand -hex 24)
echo "$ACME_API_KEY" > .acme-api-key              # à ne jamais committer (ignoré par Git)
export TF_VAR_acme_api_key="$ACME_API_KEY"
terraform -chdir=terraform/acme-api init
terraform -chdir=terraform/acme-api apply
eval "$(./scripts/lab-env.sh)"                     # API_ID, API_URL, TF_VAR_acme_api_url
./scripts/check_api.sh                             # 401, puis la commande A-1042 « expédiée »

# Étapes 5 et 6 : construire l'artefact CodeZip, puis déployer sans Policy
./scripts/package_agent.sh                         # build/agent.zip, roues Linux arm64
./scripts/enable_transaction_search.sh             # une fois par compte et région (traces, étape 9)
terraform -chdir=terraform/support-agent init
terraform -chdir=terraform/support-agent apply -var enable_policy=false
eval "$(./scripts/lab-env.sh)"                     # + RUNTIME_ARN, RUNTIME_ID, GATEWAY_ARN, MEMORY_ID

agentcore invoke --gateway "$GATEWAY_ARN" --path /mcp \
  --payload '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
agentcore invoke --runtime "$RUNTIME_ARN" \
  --session-id support-lab-session-0001-abcdefghijk \
  --payload '{"prompt":"Bonjour, où en est ma commande A-1042 ?","actorId":"c-4821"}'

# Étape 7 : attacher le moteur Policy et ses trois politiques (enable_policy vaut true par défaut)
terraform -chdir=terraform/support-agent apply
agentcore invoke --runtime "$RUNTIME_ARN" --session-id support-lab-session-0002-abcdefghijk \
  --payload '{"prompt":"Le colis A-1042 est arrivé abîmé. Remboursez-moi 120 euros.","actorId":"c-4821"}'
agentcore invoke --runtime "$RUNTIME_ARN" --session-id support-lab-session-0002-abcdefghijk \
  --payload '{"prompt":"Je confirme, 120 euros.","actorId":"c-4821"}'
agentcore invoke --runtime "$RUNTIME_ARN" --session-id support-lab-session-0002-abcdefghijk \
  --payload '{"prompt":"D accord, remboursez seulement 30 euros alors.","actorId":"c-4821"}'
agentcore invoke --gateway "$GATEWAY_ARN" --path /mcp --payload \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"support___createRefund","arguments":{"orderId":"A-1042","amountCents":12000,"reason":"colis endommagé"}}}'

# Étape 8 : la mémoire (attendez quelques minutes l'extraction)
agentcore invoke --runtime "$RUNTIME_ARN" --session-id support-lab-session-0003-abcdefghijk \
  --payload '{"prompt":"Pour la suite, contactez-moi uniquement par courriel, jamais par téléphone.","actorId":"c-4821"}'
agentcore memory record list --id "$MEMORY_ID" --namespace /users/c-4821/preferences
agentcore invoke --runtime "$RUNTIME_ARN" --session-id support-lab-session-0004-abcdefghijk \
  --payload '{"prompt":"Comment allez-vous me tenir au courant pour mon remboursement ?","actorId":"c-4821"}'

# Étape 9 : observer
agentcore runtime traces list --id "$RUNTIME_ID" --since 30m
agentcore runtime traces get <trace-id> --id "$RUNTIME_ID"
agentcore runtime logs --id "$RUNTIME_ID" --since 30m
aws cloudwatch list-metrics --namespace AWS/Bedrock-AgentCore --metric-name DenyDecisions

# Étape 10 (facultative) : évaluation en ligne, puis score immédiat d'une session
terraform -chdir=terraform/support-agent apply -var enable_online_eval=true
agentcore eval ondemand evaluate --agent "$RUNTIME_ID" --evaluators Builtin.Helpfulness \
  --session-ids support-lab-session-0002-abcdefghijk --lookback-days 1

# Ce que fait Identity dans ce lab
aws bedrock-agentcore-control list-api-key-credential-providers
```

L'identifiant de session doit compter au moins 33 caractères. Avec le **starter**, complétez les
blocs `TODO (step N)` de chaque étape avant le `apply` correspondant, et relancez
`package_agent.sh` après chaque modification du code de l'agent (Terraform téléverse alors le
nouveau zip et met à jour le runtime).

> Dans ce lab, l'identifiant du client arrive dans le payload, ce qui suffit pour tester. En
> production, il doit venir d'une identité vérifiée, par exemple le claim `sub` d'un JWT validé par
> l'autorisateur entrant du runtime : sinon, n'importe quel appelant peut lire la mémoire d'un autre
> client.

Hors ligne, sans compte AWS :

```bash
./test.sh
```

Le script crée `.venv` à partir du verrou de l'agent, lance les tests unitaires, vérifie les scripts
shell (`bash -n`, ShellCheck), puis lance `terraform fmt -check`, `terraform init -backend=false` et
`terraform validate` sur les quatre dossiers Terraform (solution et starter).

## Nettoyer

```bash
cd training-labs/labs/m13-agentcore-support-agent
./cleanup.sh               # ou ./cleanup.sh starter ; --yes pour ne pas confirmer
```

Le script détruit la pile support-agent, puis la pile acme-api, supprime ce qu'AgentCore a créé hors
de Terraform (les groupes de journaux du runtime, celui des résultats d'évaluation), efface
`.acme-api-key` et `build/`, puis lance les vérifications de la leçon (runtimes, gateways, mémoires,
moteurs Policy, fournisseurs de clé, groupes de journaux) et sort en erreur s'il reste une ressource
du lab. Transaction Search reste activé dans CloudWatch pour le compte : son indexation au-delà du
palier gratuit est facturée, réduisez le pourcentage indexé si vous n'en avez plus l'usage (le
script affiche la commande). Le lab ne crée pas de pile d'initialisation CDK.

## Changer de modèle

AgentCore est agnostique du framework et du modèle. L'agent lit son modèle dans `MODEL_ID` :

```bash
aws bedrock list-inference-profiles --query 'inferenceProfileSummaries[].inferenceProfileId'
terraform -chdir=terraform/support-agent apply -var model_id=<identifiant du profil>
```

Le rôle du runtime suit le profil (Terraform lit dans le profil les régions vers lesquelles il
route). Pour un autre fournisseur de modèles, remplacez `BedrockModel` dans `main.py` par un autre
fournisseur de modèles de Strands ; pour un autre framework, gardez `BedrockAgentCoreApp` et le
contrat de `@app.entrypoint` (`{"prompt", "actorId"}` en entrée, `{"result"}` en sortie). Gateway,
Policy, Identity et Memory ne changent pas.

## Ce que couvrent les vérifications hors ligne

- L'API existante : 401 sans la clé, le JSON exact de la commande de l'étape 1, tickets et
  remboursements.
- Le modèle OpenAPI : trois opérations, donc trois outils `support___*`, montant entier en
  centimes, et chaque opération servie par l'API.
- Les politiques Cedar, évaluées avec le moteur Cedar (`cedarpy`) : lectures et tickets autorisés,
  3 000 et 5 000 centimes autorisés, 5 001 et 12 000 refusés par défaut, B2B refusé par le `forbid`.
- L'agent, avec les SDK Strands Agents et AgentCore épinglés et un faux modèle scénarisé :
  validation du payload, boucle d'outils, remboursement refusé traité comme un résultat d'outil
  normal, un agent par session et par acteur, et le contrat HTTP du runtime (`/ping`,
  `/invocations`) par la vraie application du SDK.
- Le client de la Gateway (SigV4 pour `bedrock-agentcore`, point d'accès `/mcp`) et la session
  mémoire (espaces de noms par acteur, seuil 0,3, chaque espace alimenté par une stratégie Terraform).
- Le Terraform : noms et réglages de la leçon, moindre privilège, fournisseurs épinglés ;
  `terraform validate` contre le schéma du fournisseur épinglé.
- Le script d'empaquetage a été lancé en local : il produit un zip de 38 Mo avec des roues Linux arm64.

Seul un vrai déploiement peut montrer : l'accès au modèle, les réponses de l'agent, les appels de la
Gateway avec la clé injectée, les décisions du moteur Policy (et sa validation des politiques contre
le schéma des outils), l'extraction de la mémoire, les traces, l'évaluation en ligne, et les commandes
client de la CLI AgentCore sur de vraies ressources (vérifiées hors ligne jusqu'au chargement des
identifiants seulement).

## Remarques sur le code Terraform

- Les fichiers du projet sont dans `SupportLab/` et Terraform crée chaque ressource. La mémoire
  reproduit les quatre stratégies du modèle `agent-python-strands` de la CLI AgentCore 1.0.1
  (sémantique, préférences, résumé, épisodique). La CLI, utilisée ici comme simple client, est
  épinglée en 1.0.1 : la version 1.2.0 ne génère plus que deux stratégies et un seuil de 0,0, et la
  vérification de `/users/c-4821/preferences` dans la leçon suppose le comportement de la 1.0.x.
- Les noms des ressources portent le préfixe de projet `supportlab` (la CLI les préfixe aussi du nom
  du projet) : runtime `supportlab_agent`, mémoire `supportlab_agentMemory`, Gateway
  `supportlab-tools`, fournisseur de clé `supportlab-acme`, moteur `supportlab_guard`. La cible
  (`support`), les noms d'outils et les noms des politiques sont ceux de la leçon.
- Les rôles IAM reprennent ce qu'accordent les constructions de la CLI AgentCore, avec un accès
  Bedrock restreint au profil d'inférence et à ses modèles de destination. Les fonctions n'écrivent
  que dans leur propre groupe de journaux, au lieu de la politique gérée
  `AWSLambdaBasicExecutionRole`.
- La clé API est dans l'état Terraform (local, ignoré par Git). En production, référencez un secret
  Secrets Manager (`api_key_secret_config`) ou utilisez `api_key_wo` avec Terraform 1.11 ou plus.
- L'état Terraform reste local (`terraform/*/terraform.tfstate`, ignoré par Git).
