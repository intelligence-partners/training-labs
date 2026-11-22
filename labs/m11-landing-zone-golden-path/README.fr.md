# Lab M11 : une landing zone et un golden path

Code d'accompagnement du lab du module M11 (platform engineering) d'Intelligence Training. English version: [README.md](README.md).

L'infrastructure est écrite en **Terraform** (HCL), avec le fournisseur `hashicorp/aws` épinglé à une version exacte. Le golden path est un **module** Terraform réutilisable, dont les étiquettes et les garde-fous sont des variables. Le code, les commentaires et les identifiants sont en anglais ; les noms de ressources du lab (`assistant-rh`, `assistant-rh-mensuel`, `brouillon`…) restent ceux de la leçon.

## Objectif et architecture

Tout est déployé dans le **compte de gestion** d'une organisation de test, Région `eu-west-3` (Organizations est un service global). En production, le service `assistant-rh` irait dans un compte membre `assistant-rh-dev` et le compte de gestion n'hébergerait aucune charge de travail, comme le recommande la leçon multi-comptes.

- **Landing zone** (`infra/landing-zone`) : six OU (Security, Infrastructure, Sandbox, Workloads, et Dev et Prod sous Workloads) et quatre SCP : `DenyLeaveOrganization` sur la racine, `DenyOutsideAllowedRegions` sur les quatre OU de premier niveau (pas sur la racine, pour tester sans risque), `ProtectSecurityBaseline` sur Infrastructure, Sandbox et Workloads (pas sur Security, où l'équipe sécurité administre ces services), `DenyIamUsers` sur Sandbox et Workloads. Le rôle `SoclePlatformAdmin` est exempté des SCP de protection. En option : les permission sets du catalogue de la leçon Identity Center (`enable_identity_center`).
- **Golden path** (`infra/modules/ai-service-baseline`), appelé par `infra/assistant-rh` : une clé KMS avec rotation (`alias/assistant-rh`), un bucket S3 chiffré par cette clé, privé, versionné et accessible en HTTPS seulement, un groupe de journaux `/socle-ia/assistant-rh` chiffré par la clé et conservé 30 jours, un rôle d'exécution au moindre privilège `assistant-rh-runtime` et un budget mensuel `assistant-rh-mensuel` (20 USD, alertes à 80 % réel et 100 % prévisionnel). Chaque ressource porte les quatre étiquettes obligatoires `Service`, `Team`, `CostCenter`, `DataClassification`.
- **Garde-fous**, à deux niveaux : les variables du module n'acceptent que des valeurs conformes (`sse_algorithm` vaut `aws:kms` ou `aws:kms:dsse`, rétention des journaux bornée, attente de suppression de la clé entre 7 et 30 jours, ARN Bedrock explicites), et `guardrails/require_kms_encrypted_buckets.py` refuse un plan Terraform qui crée **n'importe quel** bucket S3 non chiffré par KMS, dans le golden path ou en dehors.

```
labs/m11-landing-zone-golden-path/
├── starter/                         le point de départ (le projet socle-ia, avec des TODO)
├── solution/                        le projet complet et fonctionnel
│   ├── infra/
│   │   ├── landing-zone/            providers.tf, variables.tf, main.tf, identity-center.tf, outputs.tf
│   │   ├── assistant-rh/            providers.tf, variables.tf, main.tf, outputs.tf
│   │   └── modules/ai-service-baseline/   versions.tf, variables.tf, main.tf, outputs.tf
│   └── guardrails/require_kms_encrypted_buckets.py
├── tests/                           terraform plan hors ligne (bouchon local) et tests du garde-fou
├── test.sh                          lance toutes les vérifications hors ligne
├── cleanup.sh                       détruit les deux modules racines, dans l'ordre de la leçon
└── .env.example
```

## Prérequis

- Un **compte AWS dédié à la formation**, qui n'appartient à aucune organisation d'entreprise. Il devient le compte de gestion d'une organisation de test. Ne faites jamais ce lab dans le compte de gestion de l'organisation de votre entreprise.
- Un accès administrateur à ce compte, idéalement par IAM Identity Center ou un rôle, avec MFA, dans un profil de la CLI.
- **AWS CLI v2**, **Terraform 1.5.7 ou plus récent**, **Python 3.10 ou plus récent** (pour le garde-fou) et `git`. Terraform télécharge `hashicorp/aws` 6.72.0 au `terraform init`.
- Une adresse e-mail pour les alertes de budget.
- En option : IAM Identity Center activé pour l'organisation, pour créer les permission sets.

## Coût estimé

Tel que la leçon l'indique : Organizations, les OU et les SCP sont gratuits ; la clé KMS gérée par le client coûte de l'ordre de 1 $ par mois, au prorata horaire, soit moins d'un centime pour quelques heures, et n'est pas facturée pendant la période d'attente de suppression ; le bucket S3 et le groupe de journaux coûtent quelques centimes au plus, souvent couverts par l'offre gratuite ; le budget AWS Budgets est gratuit. Le lab coûte **moins de 0,10 $** si vous nettoyez le jour même. Les prix évoluent : vérifiez les pages tarifs de KMS et de Budgets. (Les lignes de la leçon sur la fonction Lambda de nettoyage et la pile CDKToolkit ne s'appliquent pas à la version Terraform : ni l'une ni l'autre n'existe.)

## Étapes (correspondance avec la leçon)

```bash
git clone https://github.com/intelligence-partners/training-labs.git
cd training-labs/labs/m11-landing-zone-golden-path/starter   # ou solution/ pour déployer le lab terminé
```

| Étape de la leçon | Dans ce dépôt |
| --- | --- |
| 1. Préparer l'organisation de test | les commandes CLI de la leçon (création de l'organisation, `enable-policy-type`), puis `export TF_VAR_root_id=$ROOT_ID TF_VAR_budget_email=$BUDGET_EMAIL` |
| 2. Créer le projet | `starter/` est le projet `socle-ia` ; `terraform version` doit afficher 1.5.7 ou plus |
| 3. Préparer le compte | pas de bootstrap avec Terraform : `terraform -chdir=infra/landing-zone init` et `terraform -chdir=infra/assistant-rh init` |
| 4. La landing zone simplifiée | `infra/landing-zone/main.tf` (TODO : OU Dev et Prod, trois SCP) et `outputs.tf` |
| 5. Le golden path « service IA » | `infra/modules/ai-service-baseline/main.tf` et `outputs.tf`, puis l'appel dans `infra/assistant-rh/main.tf` et `outputs.tf` |
| 6. Le garde-fou | `guardrails/require_kms_encrypted_buckets.py` (TODO dans `check()`) ; le `variables.tf` du module porte les garde-fous d'entrée |
| 7. Planifier et relire | `terraform plan` des deux modules racines, puis le garde-fou sur le plan du golden path |
| 8. Déployer la landing zone | `terraform -chdir=infra/landing-zone apply` (20 ressources), puis les vérifications de la leçon |
| 9. Déployer le golden path | `terraform -chdir=infra/assistant-rh apply tfplan` (11 ressources), puis les vérifications de la leçon |
| 10. Vérifier le garde-fou | ajoutez le bucket `brouillon` ci-dessous, planifiez, lancez le garde-fou : il échoue ; retirez-le ensuite |
| Nettoyage | `bash cleanup.sh` (voir plus bas) |

## Déployer

Depuis le dossier du projet (`starter/` une fois complété, ou `solution/`) :

```bash
export AWS_PROFILE=formation AWS_REGION=eu-west-3
aws sts get-caller-identity
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export BUDGET_EMAIL=vous@exemple.fr
# Étape 1 : créer l'organisation si besoin, activer les SCP (voir la leçon)
export ROOT_ID=$(aws organizations list-roots --query 'Roots[0].Id' --output text)
export TF_VAR_root_id=$ROOT_ID TF_VAR_budget_email=$BUDGET_EMAIL

# Étapes 3 et 7 : init, plan, relecture
terraform -chdir=infra/landing-zone init
terraform -chdir=infra/assistant-rh init
terraform -chdir=infra/landing-zone plan
terraform -chdir=infra/assistant-rh plan -out=tfplan
terraform -chdir=infra/assistant-rh show -json tfplan > plan.json
python3 guardrails/require_kms_encrypted_buckets.py plan.json
#   Socle IA guardrail: 1 S3 bucket(s) checked, all encrypted with KMS.

# Étape 8 : la landing zone
terraform -chdir=infra/landing-zone apply
aws organizations list-organizational-units-for-parent --parent-id $ROOT_ID --query 'OrganizationalUnits[].Name'
aws organizations list-policies --filter SERVICE_CONTROL_POLICY --query 'Policies[].Name' --output text

# Étape 9 : le golden path
terraform -chdir=infra/assistant-rh apply tfplan
export BUCKET=$(terraform -chdir=infra/assistant-rh output -raw bucket_name)
export KEY_ID=$(terraform -chdir=infra/assistant-rh output -raw kms_key_id)
aws s3api get-bucket-encryption --bucket $BUCKET
aws kms get-key-rotation-status --key-id $KEY_ID
aws logs describe-log-groups --log-group-name-prefix /socle-ia/ --query 'logGroups[].[logGroupName,retentionInDays,kmsKeyId]'
aws budgets describe-budgets --account-id $ACCOUNT_ID --query 'Budgets[].[BudgetName,BudgetLimit.Amount,BudgetLimit.Unit]'
```

Dans le plan de `infra/assistant-rh`, retrouvez la key policy (la déclaration `CloudWatchLogsForThisLogGroup` autorise `logs.eu-west-3.amazonaws.com`, pour le seul groupe `/socle-ia/assistant-rh`), la bucket policy qui refuse les requêtes sans TLS (`aws:SecureTransport` = `false`) et les quatre étiquettes du budget.

Étape 10 : ajoutez temporairement dans `infra/assistant-rh/main.tf`

```hcl
resource "aws_s3_bucket" "brouillon" {
  bucket_prefix = "brouillon-"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "brouillon" {
  bucket = aws_s3_bucket.brouillon.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
```

puis planifiez et relancez le garde-fou : il sort avec le code 1 et affiche `[Error at aws_s3_bucket.brouillon] Socle IA: every S3 bucket must be encrypted with a KMS key (aws:kms or aws:kms:dsse). Found: AES256.` Passer `sse_algorithm = "AES256"` au module échoue plus tôt encore, dès `terraform validate`, avec le même message. Retirez ensuite le bucket `brouillon`.

## Tester (hors ligne)

```bash
bash test.sh                      # la solution
LAB_TARGET=starter bash test.sh   # votre travail dans starter/ (échoue tant qu'il reste des TODO)
```

`test.sh` ne demande aucun compte AWS et ne fait aucun appel à AWS. Il crée `.venv`, lance `terraform fmt -check -recursive`, `terraform init -backend=false` et `terraform validate` sur les trois dossiers Terraform de `solution/` et de `starter/`, puis les tests de `tests/`. Ceux-ci exécutent de vrais `terraform plan` avec de faux identifiants, chaque point de terminaison AWS dirigé vers un bouchon local qui ne répond qu'à `sts:GetCallerIdentity` et `sso:ListInstances` avec des valeurs d'exemple, et vérifient :

- les six OU et leurs parents, le JSON exact des quatre SCP, leurs cibles (seule `DenyLeaveOrganization` sur la racine, pas de `ProtectSecurityBaseline` sur Security), leur taille sous 5 120 caractères, et les permission sets facultatifs ;
- pour le golden path : rotation de la clé, attente de suppression de 7 jours, key policy, chiffrement du bucket par la clé avec Bucket Key, blocage de l'accès public, versionnement, bucket policy HTTPS seulement, groupe de journaux chiffré conservé 30 jours, actions et ressources exactes du rôle d'exécution, budget et alertes, quatre étiquettes sur chaque ressource ;
- les garde-fous du module (chiffrement hors KMS, rétention, attente de suppression, nom de service, classification) et le garde-fou de plan sur le bucket `brouillon`.

Ce que seul un vrai déploiement peut vérifier : qu'Organizations accepte les SCP et leurs attachements, que CloudWatch Logs accepte la clé pour le groupe chiffré, l'effet des SCP sur un compte membre, et l'e-mail du budget.

## Nettoyer

```bash
bash cleanup.sh                          # étapes 1 à 3 du nettoyage de la leçon
bash cleanup.sh --disable-scp            # désactive aussi le type de politique SCP sur la racine
bash cleanup.sh --delete-organization    # supprime aussi l'organisation si elle n'a aucun compte membre
bash cleanup.sh --yes                    # sans les confirmations de Terraform
```

Dans l'ordre : `terraform destroy` de `infra/assistant-rh` (le bucket est vidé, versions comprises, le groupe de journaux et le budget sont supprimés, la clé passe en `PendingDeletion` pour 7 jours, ce que le script vérifie), puis `terraform destroy` de `infra/landing-zone` (attachements, SCP, puis OU vides ; le script vérifie qu'il ne reste aucune OU sous la racine). Ce que Terraform ne possède pas, parce que l'étape 1 l'a créé à la CLI, est facultatif : le type de politique SCP et l'organisation elle-même.
