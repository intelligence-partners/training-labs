# Lab m06 : un serveur MCP pour votre CRM

Code d'accompagnement du lab qui clôt le module **M06, Tool use et Model Context Protocol**, du parcours Intelligence Training (leçon « Lab : un serveur MCP pour votre CRM »). Version anglaise : [README.md](README.md).

## Objectif

Construire **orbis-crm**, le serveur MCP d'un CRM fictif, et le faire servir trois clients différents : MCP Inspector, Claude Code, et la Messages API par le MCP connector. Le serveur expose deux outils (`crm_search_clients`, `crm_add_note`), une ressource paramétrée (`crm://clients/{client_id}`) et un prompt (`preparer_rendez_vous`).

Le Model Context Protocol est un standard ouvert : le même serveur fonctionne avec n'importe quel hôte MCP, pas seulement ceux d'Anthropic. Dans ce lab, il sert MCP Inspector, Claude Code et le connecteur de l'API Claude ; le script facultatif `bedrock_mcp_client.py` montre un quatrième hôte, un petit client MCP à vous qui permet à un modèle d'Amazon Bedrock d'appeler les mêmes outils, et les tests pilotent les serveurs Python et TypeScript avec un même client MCP générique.

## Architecture

| Élément | Rôle |
| --- | --- |
| `crm_data.json` | Six clients fictifs, avec leurs notes |
| `server.py` | Le serveur MCP (SDK MCP Python v2, `MCPServer`) : stdio par défaut, Streamable HTTP avec `--http`, protégé par un jeton statique lu dans `CRM_TOKEN` |
| MCP Inspector | Client de test, en stdio puis en HTTP |
| Claude Code | Hôte local, en stdio |
| Tunnel cloudflared | Expose le serveur local sur une URL HTTPS publique temporaire |
| `appel_connecteur.py` | La Messages API se connecte elle-même au serveur (MCP connector), outil d'écriture désactivé |
| `ts/` | La variante TypeScript du serveur (SDK MCP TypeScript v2 : point d'entrée stdio et point d'entrée HTTP sur Express) et de l'appel au connecteur |

Le serveur lit et écrit `crm_data.json` (chemin calculé depuis le fichier, ou `CRM_DATA`). En HTTP, une requête sans jeton reçoit `401` avec un en-tête `WWW-Authenticate` qui pointe vers les métadonnées de ressource protégée (RFC 9728) publiées par le SDK ; l'hôte public du tunnel est ajouté aux hôtes autorisés, sinon la protection contre le DNS rebinding répond `421`. Les réponses sont en JSON simple (`json_response=True`) parce que les tunnels rapides ne prennent pas en charge le SSE.

## Deux éditions du code

Les noms des outils, de la ressource et du prompt, les noms de fonctions et les clés des données sont ceux des deux éditions de la leçon. Les descriptions, les messages et les données fictives suivent la langue de la leçon que vous lisez :

| Dossiers | Leçon | Descriptions, messages, données |
| --- | --- | --- |
| `starter/`, `solution/` | Leçon française | Français (`[appel] orbis.crm_search_clients ...`) |
| `starter-en/`, `solution-en/` | Leçon anglaise (`content-en`) | Anglais (`[call] orbis.crm_search_clients ...`) |

```text
m06-crm-mcp-server/
├── README.md, README.fr.md
├── .env.example              variables lues par le lab (CRM_TOKEN, CRM_PUBLIC_URL, ...)
├── requirements.txt          mcp[cli], anthropic (étape 1)
├── requirements-bedrock.txt  + boto3, pour le client Bedrock facultatif
├── requirements-dev.txt      + pytest, pour les tests
├── test.sh                   contrôles hors ligne (lancés aussi par la CI)
├── cleanup.sh                retire les serveurs du lab de Claude Code
├── starter/ starter-en/      server.py et appel_connecteur.py avec des marqueurs TODO(step N), ts/ avec ses TODO
├── solution/ solution-en/
│   ├── crm_data.json server.py appel_connecteur.py
│   ├── bedrock_mcp_client.py facultatif : Bedrock Converse + votre propre client MCP (hors leçon)
│   └── ts/                   src/crm.ts, src/stdio.ts, src/http.ts, src/appel_connecteur.ts
└── tests/                    tests hors ligne
```

## Prérequis

Ceux de la leçon :

- Python 3.11 ou plus récent ;
- Node.js 22.19 ou plus récent, pour MCP Inspector (la version actuelle de l'Inspector, 2.16.0, déclare Node `^22.23.4 || ^24.22.1 || >=26.12.1`) ;
- Claude Code installé et connecté, ou un autre hôte MCP local en adaptant l'étape 4 ;
- une clé d'API Anthropic dans `ANTHROPIC_API_KEY`, pour l'étape 7 (accès au modèle : `claude-opus-5-5`, bêta du MCP connector `mcp-client-2025-11-20`) ;
- `cloudflared` pour l'étape 7 (`brew install cloudflared` sur macOS, ou le paquet de votre système) ; aucun compte Cloudflare n'est nécessaire pour un tunnel rapide.

Client Bedrock facultatif : un compte AWS avec accès à un modèle Bedrock qui sait appeler des outils, et des identifiants AWS sur votre poste.

Testé avec Python 3.12, Node.js 20 (serveurs et vérification de types ; l'Inspector lui-même exige Node 22), `mcp` 2.3.0, `anthropic` 2.12.0, `@modelcontextprotocol/server` 2.4.0, `@modelcontextprotocol/express` 2.0.2, `@modelcontextprotocol/node` 2.1.2, `express` 5.3.0, `zod` 4.6.7, `@anthropic-ai/sdk` 1.12.0, `boto3` 1.44.9.

## Coût estimé

Tel que la leçon l'indique : les étapes 1 à 6 ne coûtent rien d'autre que votre usage habituel de Claude Code. L'étape 7 envoie quelques requêtes à `claude-opus-5-5` : avec les définitions d'outils et les résultats, comptez quelques milliers de tokens d'entrée et quelques centaines de tokens de sortie par requête, soit quelques centimes de dollar chacune. **Le lab complet reste sous un dollar.** Aucune ressource cloud n'est créée.

Les tests de ce dépôt ne coûtent rien : ils n'appellent jamais de modèle.

## Lancer le lab

```bash
git clone https://github.com/intelligence-partners/training-labs.git
cd training-labs/labs/m06-crm-mcp-server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd starter             # complétez les TODO ; ou cd solution pour le serveur terminé
```

Les commandes de la leçon utilisent `$(pwd)/.venv/bin/python`. Dans ce dépôt, l'environnement virtuel est un niveau au-dessus : utilisez `$(pwd)/../.venv/bin/python`, ou plus simplement `"$(which python)"` une fois l'environnement activé :

| Étape de la leçon | Où | Commande |
| --- | --- | --- |
| 1. Préparer le projet | les commandes ci-dessus | `crm_data.json` est déjà là |
| 2. Écrire le serveur | `server.py`, `TODO(step 2)` | `python server.py` (reste silencieux, Ctrl+C pour arrêter) |
| 3. Tester avec MCP Inspector, en stdio | | `npx @modelcontextprotocol/inspector "$(which python)" "$(pwd)/server.py"`, puis `--cli ... --method tools/list`, `--method tools/call --tool-name crm_search_clients --tool-arg query=lyon`, `--method resources/read --uri crm://clients/C-1003` |
| 4. Brancher le serveur dans Claude Code | | `claude mcp add orbis -- "$(which python)" "$(pwd)/server.py"`, puis `claude mcp list` |
| 5. Servir en HTTP derrière un jeton | `server.py`, `TODO(step 5)` | `export CRM_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"`, `python server.py --http`, puis `curl -s -i -X POST http://127.0.0.1:8000/mcp -H 'Content-Type: application/json' -d '{}'` |
| 6. Tester en HTTP avec l'Inspector | | `npx @modelcontextprotocol/inspector --cli http://127.0.0.1:8000/mcp --transport http --header "Authorization: Bearer $CRM_TOKEN" --method tools/list` |
| 7. Exposer le serveur et l'appeler par le MCP connector | `appel_connecteur.py`, `TODO(step 7)` | `cloudflared tunnel --url http://localhost:8000`, `export CRM_PUBLIC_URL="https://<mots-aléatoires>.trycloudflare.com"`, `python server.py --http`, puis `python appel_connecteur.py` |
| Variante TypeScript | `ts/` | `cd ts && npm ci`, puis `npx @modelcontextprotocol/inspector npx tsx src/stdio.ts`, `claude mcp add orbis-ts -- "$(pwd)/node_modules/.bin/tsx" "$(pwd)/src/stdio.ts"`, `npx tsx src/http.ts` (port 3000), `npx tsx src/appel_connecteur.ts` |

## Tester

```bash
bash test.sh
```

`test.sh` crée `.venv`, installe `requirements-dev.txt`, lance `npm ci` et la vérification de types TypeScript dans chaque dossier `ts/`, compile les deux starters et importe leur serveur, puis lance les tests sur `solution/` et `solution-en/`. Ni clé d'API, ni identifiants AWS, ni tunnel, ni Claude Code.

Ce que couvrent les tests :

- chaque primitive par le client MCP en mémoire : schémas et annotations des outils (recherche en lecture seule, `limit` borné, énumération des secteurs), la recherche avec chaque filtre, l'erreur de validation de `limit=99` rendue en `isError` (sans trace), la note écrite dans le fichier JSON à la date du jour, la `ToolError` qui dit comment corriger l'appel, le modèle de ressource et sa `ResourceNotFoundError`, le prompt et les instructions du serveur (étapes 2 et 3) ;
- le serveur Python en stdio, lancé en sous-processus comme le lancent l'Inspector et Claude Code (étape 3) ;
- le serveur Python en Streamable HTTP : `401` sans jeton ou avec un mauvais jeton, l'en-tête `WWW-Authenticate` exact, les métadonnées de ressource protégée, `421` pour un hôte inconnu et `200` pour l'hôte public du tunnel, des réponses en JSON simple, et une session MCP complète avec le jeton (étapes 5 et 6) ;
- `appel_connecteur.py` avec le vrai SDK contre une Messages API simulée : `mcp_servers` avec le jeton, la liste noire du toolset, l'en-tête bêta, et les lignes de sortie de la leçon (étape 7) ;
- le serveur TypeScript, vérifié par le compilateur et piloté en stdio et en HTTP par le client MCP Python ;
- le client Bedrock facultatif (boucle d'outils, liste noire, erreurs renvoyées au modèle) avec le `Stubber` de botocore ;
- `cleanup.sh`, avec une commande `claude` de substitution.

Non couverts hors ligne : MCP Inspector lui-même (Node 22 et un navigateur pour l'interface), Claude Code, le tunnel cloudflared, et le vrai appel par le MCP connector, qui exige une clé d'API et une URL HTTPS publique.

Pour vérifier votre propre travail au fil des TODO :

```bash
LAB_TARGET=starter .venv/bin/python -m pytest tests      # ou LAB_TARGET=starter-en
```

## Nettoyer

Rien n'est créé dans le cloud. Trois éléments restent ouverts sur votre poste :

```bash
# 1. Arrêter le tunnel et le serveur : Ctrl+C dans leurs terminaux
# 2. Retirer les serveurs de Claude Code (orbis, orbis-http, orbis-ts) :
bash ../cleanup.sh
# 3. Oublier le jeton de lab :
unset CRM_TOKEN CRM_PUBLIC_URL
```

L'URL du tunnel rapide cesse d'exister dès l'arrêt de `cloudflared`. Retirez aussi les serveurs des autres hôtes MCP où vous les avez déclarés.

## Changer de modèle

- **Un autre modèle Claude pour l'étape 7** : modifiez `model=` dans `appel_connecteur.py` (ou `ts/src/appel_connecteur.ts`). Le serveur ne dépend d'aucun modèle.
- **Amazon Bedrock (facultatif, hors leçon)** : l'API Converse de Bedrock n'a pas de MCP connector, donc `bedrock_mcp_client.py` est lui-même le client MCP. Il lance `server.py` en stdio (ni tunnel, ni jeton), liste ses outils, les confie au modèle comme outils Converse sauf `crm_add_note` (la même liste noire que le connecteur), exécute chaque appel d'outil sur le serveur et renvoie le résultat jusqu'à la réponse du modèle.

  ```bash
  pip install -r ../requirements-bedrock.txt
  export BEDROCK_MODEL_ID="<identifiant d'un modèle activé dans votre compte, qui sait appeler des outils>"
  export AWS_REGION=eu-west-3
  MODEL_PROVIDER=bedrock python appel_connecteur.py     # ou : python bedrock_mcp_client.py
  ```

  La sortie a la même forme qu'à l'étape 7 : une ligne `[appel]` par appel d'outil, une ligne `[résultat]`, la réponse et le motif de fin. Aucun identifiant de modèle n'est écrit en dur.
