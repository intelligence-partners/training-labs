# Lab M15 : red team de votre propre agent

Code d'accompagnement du lab du module M15 (Sécurité et gouvernance) de la formation
Intelligence Training : *Lab : red team de votre propre agent*. [English version](README.md).

## Objectif

Un exercice de red team **défensif** : vous jouez l'attaquant contre votre propre agent, sur
votre propre banc d'essai, pour mesurer et combler ses faiblesses. Tout se passe en local, avec
des **outils simulés** qui n'envoient aucun e-mail et ne touchent à aucun système réel : un
appel d'outil se contente d'écrire une ligne dans une liste d'effets. Vous partez d'un agent
volontairement peu protégé, vous mesurez combien d'injections de test réussissent, puis vous
activez cinq défenses une par une et vous mesurez à chaque étape le progrès. L'objectif n'est
pas d'écrire des attaques, mais de voir que les contre-mesures déterministes bornent l'impact
là où le prompt seul échoue.

## Architecture

Le banc (`banc.py`) charge `scenarios.json` et lance `agent.py`, qui dialogue avec le modèle et
appelle `garde.py` avant les outils simulés d'`outils.py`. `garde.py` porte les défenses D2 à
D5 et, dans la partie AWS facultative (étape 8), le filtrage par Bedrock Guardrails ; une règle
AgentCore Policy sur une Gateway peut porter D5 hors du code de l'agent.

| Fichier | Rôle |
| --- | --- |
| `outils.py` | Les outils **simulés** (e-mail, CRM, remboursement) : ils journalisent, ils n'agissent pas |
| `agent.py` | La boucle d'appel d'outils, la défense D1 (séparation lecture/action) |
| `garde.py` | Les défenses D2 à D5 : liste blanche, confirmation, filtrage, règle de type Policy |
| `scenarios.json` | Les cas de test : tâches légitimes et documents contenant une injection de test |
| `banc.py` | Lance les scénarios, répète chacun N fois, compte les réussites |
| `providers.py` | Sélecteur facultatif de fournisseur (API Claude, Claude sur Bedrock, Converse) |
| `rapport-campagne.md` | Modèle du rapport de campagne (étape 7) |

Seules deux fonctions parlent au modèle : la boucle de `agent.traiter` et le classifieur
`garde._parait_injecte`. Les outils simulés, le module de garde, les scénarios et le comptage
du banc en sont indépendants. Le code garde les noms de fichiers, identifiants et textes en
français de la leçon ; les commentaires sont en anglais.

```text
m15-agent-red-team/
├── starter/      outils.py et scenarios.json prêts ; agent.py, garde.py, banc.py avec marqueurs TODO
├── solution/     le banc complet, les défenses D1 à D5 et le filtrage de l'étape 8
├── infra/        Terraform de l'étape 8 (guardrail, règle AgentCore Policy facultative)
├── tests/        tests hors ligne, et naive_agent.py, un agent sans modèle pour les essais à blanc
├── rapport-campagne.md, cleanup.sh, .env.example
└── test.sh       installe dans .venv et lance tous les contrôles, Terraform compris
```

## Prérequis

- Python 3.10 ou plus, un terminal, un compte Claude Console et une clé dans `ANTHROPIC_API_KEY`.
- Étape 8 (facultative) : un compte AWS autorisé à utiliser Amazon Bedrock Guardrails
  (`ApplyGuardrail`), Terraform 1.5.7 ou plus, et pour les plus avancés la Gateway du lab du
  module AgentCore. Région par défaut du parcours : `eu-west-3` (Paris). Avant l'étape 8,
  vérifiez sur la page « Supported Regions » de Guardrails qu'`ApplyGuardrail` y est offert ;
  sinon, utilisez une Région où il l'est, par exemple `eu-west-1` (Irlande), et notez la date
  de votre vérification.
- Facultatif : pour rejouer le banc sur un autre fournisseur de modèles (étape 7), ses accès et
  identifiants.

N'utilisez jamais de vraies coordonnées (adresses e-mail réelles, données clients réelles) dans
`scenarios.json` : les outils sont simulés, mais le contenu part quand même à l'API. Utilisez
des données fictives, du type `client@example.test`.

## Coût estimé

Tel que l'indique la leçon : les étapes 1 à 7 n'utilisent que l'API Claude, hors comparaison
facultative avec d'autres modèles, pour **moins de 2 $ pour tout le lab** (chaque passe du banc
fait quelques dizaines d'appels, surtout sur Claude Haiku 5.5). La leçon ne chiffre pas
l'étape 8 : consultez la page tarifs d'Amazon Bedrock Guardrails avant de la lancer.

## Étapes

| Étape de la leçon | Dans ce dépôt |
| --- | --- |
| 1. Préparer l'environnement | `.venv` + `pip install -r requirements.txt` (fixe `anthropic==2.12.0`) |
| 2. Les outils simulés | `outils.py` (prêt dans `starter/`) |
| 3. L'agent nu | `starter/agent.py` (TODO étape 3), `solution/agent.py` |
| 4. Le module de garde, sans défense | `starter/garde.py` (état de l'étape 4) |
| 5. Mesurer l'agent nu | `scenarios.json`, `starter/banc.py` (TODO étape 5), `python banc.py '{}' 5` |
| 6. Durcir, défense par défense | `starter/garde.py` (TODO étape 6), `solution/garde.py` |
| 7. Le rapport de campagne | `rapport-campagne.md` ; autres modèles : `MODEL_PROVIDER` (plus bas) |
| 8. Porter D4 et D5 sur AWS (facultatif) | `infra/` (Terraform), `garde.ticket_bloque`, défense `"guardrail"` |

## Lancer le lab

```bash
git clone https://github.com/intelligence-partners/training-labs.git
cd training-labs/labs/m15-agent-red-team
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."   # ou un profil créé avec « ant auth login »
python -c "import anthropic; print(anthropic.__version__)"
cd starter        # ou : cd solution, pour lancer le banc terminé
```

Mesure de référence (étape 5), puis chaque défense (étape 6) :

```bash
python banc.py '{}' 5
python banc.py '{"separation": true}' 5
python banc.py '{"liste_blanche": true}' 5
python banc.py '{"liste_blanche": true, "regle_montant": true}' 5
python banc.py '{"liste_blanche": true, "regle_montant": true, "filtrage": true}' 5
python banc.py '{"liste_blanche": true, "regle_montant": true, "filtrage": true, "confirmation": true}' 5
```

### Essai à blanc sans modèle

`tests/naive_agent.py` est un agent sans modèle qui obéit à toute instruction trouvée dans le
ticket : le pire cas d'un agent sans aucun jugement. Il ne coûte rien, ne demande aucune clé,
et montre que les défenses déterministes (D1, D2, D3, D5) l'arrêtent à elles seules :

```bash
BANC_AGENT=naive_agent:traiter PYTHONPATH=../tests python banc.py '{}' 2
BANC_AGENT=naive_agent:traiter PYTHONPATH=../tests python banc.py '{"liste_blanche": true, "regle_montant": true}' 2
```

### Viser un autre agent

Le jeu d'attaques (`scenarios.json`) et l'évaluation (`banc.py`) ne dépendent d'aucun modèle.
`BANC_AGENT=module:fonction` fait viser au banc tout agent importable depuis `PYTHONPATH` qui
respecte ce contrat :

- `traiter(ticket: str, demande: str, defenses: dict) -> list[dict]` ;
- chaque action passe par `garde.appeler(nom, args, demande, defenses)` (ou les mêmes
  contrôles), et les outils simulés d'`outils.py` enregistrent les effets ;
- la fonction renvoie les effets de ce seul ticket (videz d'abord `outils.EFFETS`).

### Étape 8 (facultative) : D4 et D5 sur AWS

```bash
cd ..   # le dossier du lab
cp infra/terraform.tfvars.example infra/terraform.tfvars   # Région, règle Policy facultative
terraform -chdir=infra init
terraform -chdir=infra apply
export AWS_REGION=$(terraform -chdir=infra output -raw region)
export BEDROCK_GUARDRAIL_ID=$(terraform -chdir=infra output -raw guardrail_id)
cd solution
python banc.py '{"guardrail": true}' 5
python banc.py '{"guardrail": true, "liste_blanche": true, "regle_montant": true}' 5
```

La défense `"guardrail"` appelle `ApplyGuardrail` (filtre d'attaques de prompt, version
`DRAFT`) sur le texte du ticket avant que l'agent ne le voie : le filtre n'évalue pas le contenu
d'un `toolResult`, d'où l'appel explicite. Pour D5 avec AgentCore Policy, renseignez
`policy_engine_id` et `gateway_arn` (la Gateway du lab AgentCore) dans `terraform.tfvars` :
Terraform ajoute la règle Cedar de la leçon (`infra/policy-rembourser.cedar.tftpl`), qui refuse
`rembourser` au-delà du plafond. Passez d'abord le moteur de Policy de la Gateway en mode
`LOG_ONLY`, puis en `ENFORCE`.

## Tester

```bash
bash test.sh
```

Le script crée `.venv`, installe `requirements-dev.txt`, lance les tests unitaires sur
`solution/`, vérifie que `starter/` se compile et s'importe, contrôle `cleanup.sh`, puis lance
`terraform fmt -check -recursive`, `terraform init -backend=false` et `terraform validate` sur
`infra/` (`SKIP_TERRAFORM=1` pour les sauter). Ni clé ni identifiant AWS ne sont nécessaires :
l'API Claude est remplacée par un transport simulé derrière un vrai client `anthropic`,
Converse et `ApplyGuardrail` passent par le Stubber de botocore, et le banc est piloté par
l'agent naïf.

## Nettoyer

Les étapes 1 à 7 ne créent aucune ressource facturée : supprimez le dossier et l'environnement
virtuel.

```bash
bash cleanup.sh        # détruit les ressources de l'étape 8, si infra/ a été appliqué
deactivate && rm -rf .venv
```

La Gateway et le moteur de Policy du lab AgentCore ne sont pas touchés : gardez-les si vous les
réutilisez ailleurs. Vérifiez enfin qu'aucune clé d'API ne traîne dans un historique de shell.

## Changer de modèle

Comparer plusieurs familles de modèles sur le même banc est le meilleur usage du lab. Ne
touchez ni à `outils.py`, ni à `garde.py` (hors modèle du classifieur), ni à `scenarios.json`,
ni au comptage de `banc.py` : changez le fournisseur des deux fonctions qui parlent au modèle.

| `MODEL_PROVIDER` | Client | Modèle de l'agent | Modèle du classifieur D4 |
| --- | --- | --- | --- |
| `anthropic` (défaut) | `anthropic.Anthropic()` | `claude-opus-5-5` | `claude-haiku-5-5` |
| `anthropic-bedrock` | `anthropic.AnthropicBedrock` | `BEDROCK_MODEL_ID` | `BEDROCK_CLASSIFIER_MODEL_ID` (défaut : `BEDROCK_MODEL_ID`) |
| `bedrock` | boto3 `bedrock-runtime` `converse` (Amazon Nova, Meta Llama, Mistral AI…) | `BEDROCK_MODEL_ID` | `BEDROCK_CLASSIFIER_MODEL_ID` (défaut : `BEDROCK_MODEL_ID`) |

```bash
export MODEL_PROVIDER=bedrock AWS_REGION=eu-west-3
export BEDROCK_MODEL_ID=<modèle de l'agent> BEDROCK_CLASSIFIER_MODEL_ID=<modèle du classifieur>
python banc.py '{}' 5
```

Avec Converse, le ticket reste dans un résultat d'outil étiqueté, la sortie structurée du
classifieur devient `outputConfig.textFormat`, et `thinking` n'est pas envoyé (il est propre à
Claude) ; une réponse du classifieur illisible bloque l'action (refus par défaut).
`BEDROCK_STRICT_TOOLS=false`, `BEDROCK_CACHE_POINTS=false` et `BEDROCK_MAX_TOKENS` adaptent les
requêtes à un modèle qui ne gère pas une de ces fonctions. Notez le modèle, sa version et la
date dans le rapport de campagne : les défenses déterministes donnent le même résultat quel que
soit le modèle, alors que D0 (politique du prompt) et D4 (filtrage) varient d'une famille et
d'une version à l'autre.
