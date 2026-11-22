<p align="left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/ip-monogram-white.png">
    <img src="assets/ip-monogram-black.png" alt="Intelligence Partners" width="72">
  </picture>
</p>

# Labs d'Intelligence Training

Code d'accompagnement des labs pratiques d'**Intelligence Training**, le parcours en ligne *Expert AI Platform Engineering sur AWS* d'[Intelligence Partners](https://the-intelligence-partners.com/training).

Chaque lab suit pas à pas une leçon du parcours. La leçon explique le pourquoi ; ce dépôt vous donne le code, pour passer votre temps à construire et à comprendre plutôt qu'à recopier.

[English version](README.md)

## Les labs

| Module | Lab | Dossier |
| --- | --- | --- |
| M05 | Un service de synthèse de documents sur l'API d'un LLM | [`labs/m05-document-summary-service`](labs/m05-document-summary-service) |
| M06 | Un serveur MCP pour votre CRM | [`labs/m06-crm-mcp-server`](labs/m06-crm-mcp-server) |
| M07 | Un agent documentaire avec citations (RAG) | [`labs/m07-rag-assistant-citations`](labs/m07-rag-assistant-citations) |
| M08 | Un agent d'analyse de tickets de bout en bout | [`labs/m08-ticket-analysis-agent`](labs/m08-ticket-analysis-agent) |
| M10 | Votre premier service serverless | [`labs/m10-first-serverless-service`](labs/m10-first-serverless-service) |
| M11 | Une landing zone et un golden path en Terraform | [`labs/m11-landing-zone-golden-path`](labs/m11-landing-zone-golden-path) |
| M12 | Un agent RAG sur Amazon Bedrock, Knowledge Bases et Guardrails | [`labs/m12-bedrock-rag-guardrails`](labs/m12-bedrock-rag-guardrails) |
| M13 | Un agent de support complet sur Amazon Bedrock AgentCore | [`labs/m13-agentcore-support-agent`](labs/m13-agentcore-support-agent) |
| M14 | Un tableau de bord coût et qualité d'un agent | [`labs/m14-llmops-cost-quality-dashboard`](labs/m14-llmops-cost-quality-dashboard) |
| M15 | La red team de votre propre agent | [`labs/m15-agent-red-team`](labs/m15-agent-red-team) |

Les ateliers de M03 (prompt engineering), M16 (projet final) et M17 (la Méthode IP) se passent de code : ils se font dans le parcours.

## Organisation d'un lab

```
labs/<lab>/
  README.md, README.fr.md   objectif, prérequis, coût, étapes, nettoyage
  starter/                  votre point de départ, avec des TODO calés sur la leçon
  solution/                 le code complet, pour comparer ou vous débloquer
  infra/                    l'infrastructure en code Terraform, quand le lab déploie des ressources AWS
  tests/                    des contrôles qui tournent hors ligne, appels au modèle et à AWS simulés
  test.sh                   installe les dépendances et lance les contrôles
  cleanup.sh                supprime tout ce que le lab a créé, quand il crée des ressources
  .env.example              les variables d'environnement à renseigner
```

## Démarrer

```bash
git clone https://github.com/intelligence-partners/training-labs.git
cd training-labs/labs/<lab>
cp .env.example .env   # puis complétez-le
bash test.sh           # contrôles hors ligne, sans aucun compte
```

Suivez ensuite la leçon et le README du lab.

## Le modèle de votre choix

Le parcours est multimodèle. Comme les leçons, les labs prennent un fournisseur de modèles comme exemple, et la plupart permettent d'en changer par une variable d'environnement : l'API d'Anthropic ou Amazon Bedrock par exemple, qui donne accès à plusieurs familles de modèles par la même API Converse. Le README de chaque lab explique comment.

## Coûts et sécurité

- Les labs AWS tournent sur **votre propre compte AWS**. Chaque README reprend le coût estimé indiqué dans la leçon. Lancez toujours le nettoyage à la fin.
- Les appels aux modèles sont facturés par votre fournisseur. Posez une alerte de budget avant de commencer.
- Ne versionnez jamais votre fichier `.env` ni aucun identifiant. Le `.gitignore` les exclut.

## Contrôles

Chaque lab fournit un `test.sh` qui tourne sans compte ni clé d'API : tests unitaires avec appels au modèle et à AWS simulés, vérification des types, `terraform validate` sur l'infrastructure. Les mêmes contrôles tournent à chaque push dans GitHub Actions. Ils ne remplacent pas un vrai déploiement, qui fait partie du lab.

---

Le code de ce dépôt est publié sous [licence MIT](LICENSE). Le parcours lui-même (leçons, exercices, examens, vidéos) reste la propriété d'Intelligence Partners.

Intelligence Training est édité par Intelligence Partners. Il n'est affilié ni à Amazon Web Services ni à aucun fournisseur de modèles.
