# Lab M10 : votre premier service serverless

Code d'accompagnement du lab du module M10 (Fondations AWS) d'Intelligence Training : un **registre de prompts**, l'API où une équipe enregistre ses modèles de prompts et les relit par identifiant. English version: [README.md](README.md).

L'infrastructure est écrite en **Terraform** (HCL), avec le fournisseur `hashicorp/aws` épinglé à une version exacte. Le code, les commentaires et les identifiants sont en anglais ; les champs JSON et les messages restent en français.

## Objectif et architecture

Une **HTTP API** d'API Gateway expose deux routes, `POST /prompts` et `GET /prompts/{id}`. Elles invoquent une fonction **Lambda** en Python 3.13 sur Graviton (`arm64`), qui écrit et lit dans une table **DynamoDB** à la demande. La fonction écrit des journaux JSON dans un groupe **CloudWatch Logs** conservé 7 jours, et son rôle d'exécution n'autorise rien d'autre : `dynamodb:PutItem` et `dynamodb:GetItem` sur cette table, `logs:CreateLogStream` et `logs:PutLogEvents` sur ce groupe. L'API limite le débit à 5 requêtes par seconde, avec des pointes à 10. Tout est déployé en `eu-west-3` et étiqueté `Projet=formation-m10`, `Environnement=lab`.

```
labs/m10-first-serverless-service/
├── starter/            le point de départ (le projet registre-prompts, avec des TODO)
│   ├── src/app.py
│   └── infra/          providers.tf, variables.tf, main.tf, outputs.tf
├── solution/           le projet complet et fonctionnel
│   ├── src/app.py      la fonction (handler app.handler)
│   └── infra/          providers.tf, variables.tf, main.tf, outputs.tf, .terraform.lock.hcl
├── tests/              tests hors ligne : handler (DynamoDB simulé par moto), terraform plan hors ligne
├── test.sh             lance toutes les vérifications hors ligne
├── cleanup.sh          terraform destroy, puis vérifie qu'il ne reste rien
└── .env.example
```

| Ressource (adresse Terraform) | Rôle |
| --- | --- |
| `aws_dynamodb_table.prompts` | Table `registre-prompts`, à la demande, clé `id` |
| `aws_cloudwatch_log_group.prompts` | `/aws/lambda/registre-prompts-prompts`, 7 jours |
| `aws_iam_role.prompts_function`, `aws_iam_role_policy.minimal` | Rôle d'exécution, policy intégrée `registre-prompts-minimal`, aucune policy gérée |
| `aws_lambda_function.prompts` | Fonction `registre-prompts-prompts`, python3.13, arm64, 256 Mo, 10 s, journaux JSON au niveau INFO |
| `aws_apigatewayv2_api.prompts`, `aws_apigatewayv2_stage.default`, `aws_apigatewayv2_integration.prompts`, `aws_apigatewayv2_route.*` | HTTP API, étape `$default`, deux routes |
| `aws_lambda_permission.*` | API Gateway peut invoquer la fonction, pour ces deux routes seulement |

## Prérequis

- Un compte AWS sécurisé selon la leçon IAM (MFA sur l'utilisateur racine, que vous n'utilisez pas ici) et un budget avec alerte, selon la leçon sur les coûts.
- Une identité d'administration du compte d'apprentissage : le lab crée un rôle IAM, ce que la policy gérée `PowerUserAccess` ne permet pas.
- Des identifiants temporaires dans la CLI : un profil `aws configure sso` (Identity Center) ou `aws login` (AWS CLI 2.32.0 ou plus). Aucune clé d'accès longue durée.
- **AWS CLI v2** et **Terraform 1.5.7 ou plus récent** (`aws --version`, `terraform version`). Terraform télécharge les fournisseurs (`hashicorp/aws` 6.72.0, `hashicorp/archive` 2.8.1) au `terraform init`.
- Pour les seuls tests hors ligne : Python 3.10 ou plus récent.
- Si votre compte est en plan gratuit, vérifiez dans la FAQ de l'offre gratuite que Lambda, API Gateway, DynamoDB et CloudWatch y sont accessibles.

## Coût estimé

Tel que la leçon l'indique : aucune ressource de ce lab n'est facturée à l'heure : pas de passerelle NAT, pas d'endpoint d'interface, pas d'instance. Tout est facturé à l'usage : requêtes API Gateway, requêtes et Go-secondes Lambda, requêtes et stockage DynamoDB à la demande, ingestion et stockage des journaux. Pour la centaine de requêtes du lab, la facture se compte en **fractions de centime**, et peut être nulle dans les limites de l'offre gratuite. Elle ne reste négligeable que si vous faites le **nettoyage** final. Pour un chiffrage précis, utilisez l'AWS Pricing Calculator. (Avec Terraform, le code est envoyé directement à Lambda : aucun artefact dans S3.)

## Étapes (correspondance avec la leçon)

```bash
git clone https://github.com/intelligence-partners/training-labs.git
cd training-labs/labs/m10-first-serverless-service/starter   # ou solution/ pour déployer le lab terminé
```

| Étape de la leçon | Dans ce dépôt |
| --- | --- |
| 1. Vérifier l'identité et la région | `export AWS_PROFILE=lab AWS_REGION=eu-west-3` puis `aws sts get-caller-identity` (jamais `root`) |
| 2. Créer le projet | `starter/` est le projet `registre-prompts` : complétez les TODO de `src/app.py`, `infra/main.tf` et `infra/outputs.tf` |
| 3. Valider et construire | `cd infra && terraform fmt -check && terraform init && terraform validate` |
| 4. Déployer | `terraform plan -out=tfplan`, lisez le plan (12 à ajouter), puis `terraform apply tfplan` |
| 5. Tester l'API | `API_URL=$(terraform output -raw api_url)`, puis les commandes `curl` de la leçon |
| 6. Lire les journaux | `aws logs tail /aws/lambda/registre-prompts-prompts --since 10m --region eu-west-3` |
| 7. Vérifier le moindre privilège | les commandes de la leçon, inchangées (fonction `registre-prompts-prompts`, policy `registre-prompts-minimal`) |
| 8. Suivre le coût par tag (facultative) | Cost Explorer, filtre `Projet = formation-m10` |
| Nettoyage | `bash cleanup.sh` (voir plus bas) |

## Déployer

Depuis le dossier `infra/` du projet à déployer (`starter/infra` une fois complété, ou `solution/infra`) :

```bash
export AWS_PROFILE=lab AWS_REGION=eu-west-3
aws sts get-caller-identity
terraform init
terraform validate
terraform plan -out=tfplan      # à lire : 12 ressources à ajouter, rien à modifier ni à détruire
terraform apply tfplan          # se termine par « Apply complete! Resources: 12 added, 0 changed, 0 destroyed. »
terraform output                # api_url, function_name, table_name
```

Le plan joue le rôle du jeu de modifications : lisez-le avant de l'appliquer. Il liste `aws_iam_role`, `aws_iam_role_policy`, `aws_lambda_function`, `aws_dynamodb_table`, `aws_cloudwatch_log_group`, `aws_apigatewayv2_api`, `aws_apigatewayv2_stage`, `aws_apigatewayv2_integration`, deux `aws_apigatewayv2_route` et deux `aws_lambda_permission` ; aucune passerelle NAT, aucun utilisateur IAM. Les routes déclarent `authorization_type = "NONE"` : l'API est publique, ce qui est acceptable pour ce lab limité en débit et supprimé dans l'heure, jamais pour un service réel (autorisation IAM, JWT ou Lambda).

Essayez-la :

```bash
API_URL=$(terraform output -raw api_url)
curl -s -X POST "$API_URL/prompts" -H "Content-Type: application/json" \
  -d '{"nom": "resume-contrat", "texte": "Résume le contrat ci-dessous en cinq points, en citant les articles."}'
curl -s "$API_URL/prompts/<identifiant renvoyé ci-dessus>"
curl -s -i -X POST "$API_URL/prompts" -H "Content-Type: application/json" -d '{"nom": "sans-texte"}'   # 400
aws logs tail /aws/lambda/registre-prompts-prompts --since 10m --region eu-west-3
```

## Tester (hors ligne)

```bash
bash test.sh                      # la solution
LAB_TARGET=starter bash test.sh   # votre travail dans starter/ (échoue tant qu'il reste des TODO)
```

`test.sh` ne demande aucun compte AWS et ne fait aucun appel à AWS. Il crée `.venv`, puis lance :

- `terraform fmt -check -recursive`, `terraform init -backend=false` et `terraform validate` sur `solution/infra` et `starter/infra` ;
- les tests unitaires du handler (`tests/test_handler.py`), avec DynamoDB simulé par moto : codes de statut, messages exacts en français, limites de longueur, corps en base64, ligne de journal `prompt_cree id=… taille=…` sans le texte du prompt, et le fait que le code n'appelle que `PutItem` et `GetItem` ;
- des vérifications sur un `terraform plan` hors ligne (`tests/test_infra.py`) : faux identifiants, chaque point de terminaison AWS dirigé vers un port local fermé. Elles vérifient le runtime, l'architecture, la mémoire, le délai, les journaux JSON, la rétention de 7 jours, la limite de débit, les routes, les actions exactes du rôle d'exécution, l'absence de policy gérée et les tags de coûts.

Ce que seul un vrai déploiement peut vérifier : l'invocation réelle par API Gateway, la propagation IAM, le contenu des journaux CloudWatch et les réponses `429` au-delà de la limite de débit.

## Nettoyer

```bash
bash cleanup.sh            # depuis le dossier du lab ; ou : bash cleanup.sh chemin/vers/registre-prompts
bash cleanup.sh --yes      # sans la confirmation de Terraform
```

Le script lance `terraform destroy` (table et données, fonction, API, rôle, groupe de journaux), vérifie que la fonction, la table et les groupes `/aws/lambda/registre-prompts` n'existent plus, puis supprime l'artefact local (`infra/.build`) et le plan enregistré. À la main, l'équivalent est `terraform destroy` dans `infra/`, puis :

```bash
aws lambda get-function --function-name registre-prompts-prompts --region eu-west-3          # ResourceNotFoundException
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/registre-prompts --region eu-west-3   # "logGroups": []
```
