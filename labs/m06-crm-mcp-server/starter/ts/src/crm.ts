import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { McpServer, ResourceNotFoundError, ResourceTemplate } from "@modelcontextprotocol/server";
import * as z from "zod/v4";

const DATA_FILE = process.env.CRM_DATA ?? fileURLToPath(new URL("../crm_data.json", import.meta.url));

interface Note { date: string; auteur: string; texte: string }
interface Client { id: string; nom: string; secteur: string; ville: string; statut: string; ca_annuel_eur: number; interlocuteur: string; notes: Note[] }

const charger = (): { clients: Client[] } => JSON.parse(readFileSync(DATA_FILE, "utf8"));
const sauver = (data: { clients: Client[] }) => writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));

const SECTEURS = ["industrie", "assurance", "logistique", "sante", "finance", "agroalimentaire"] as const;

export function createServer(): McpServer {
  const server = new McpServer(
    { name: "orbis-crm", version: "1.0.0" },
    { instructions: "Outils du CRM Orbis : rechercher des clients, lire une fiche, ajouter une note de suivi." },
  );

  server.registerTool(
    "crm_search_clients",
    {
      description:
        "Cherche des clients et prospects dans le CRM Orbis. À utiliser dès que l'utilisateur évoque une entreprise, " +
        "une ville ou un interlocuteur, avant de lire une fiche ou d'ajouter une note. Renvoie l'identifiant (C-XXXX), " +
        "le nom, la ville, le secteur et le statut, sans les notes : lisez la ressource crm://clients/{id} pour le détail.",
      inputSchema: z.object({
        query: z.string().describe("Nom, ville ou interlocuteur à chercher, insensible à la casse. Chaîne vide pour tout lister."),
        secteur: z.enum(SECTEURS).optional().describe("Filtre facultatif sur le secteur d'activité."),
        limit: z.number().int().min(1).max(20).default(5).describe("Nombre maximal de résultats."),
      }),
      annotations: { readOnlyHint: true, openWorldHint: false },
    },
    async ({ query, secteur, limit }) => {
      // TODO: same search as server.py (case-insensitive on nom, ville, interlocuteur; optional
      // secteur filter; at most `limit` results with id, nom, ville, secteur, statut), returned as
      // { content: [{ type: "text", text: JSON.stringify(trouves, null, 2) }] }.
      void charger;
      return { content: [{ type: "text", text: `TODO: crm_search_clients(${query}, ${secteur}, ${limit})` }], isError: true };
    },
  );

  server.registerTool(
    "crm_add_note",
    {
      description:
        "Ajoute une note de suivi datée du jour sur la fiche d'un client. N'appelez cet outil que si l'utilisateur " +
        "demande explicitement d'enregistrer une note : l'écriture est définitive. Renvoie une confirmation.",
      inputSchema: z.object({
        client_id: z.string().describe("Identifiant du client, au format C-XXXX, obtenu avec crm_search_clients."),
        texte: z.string().describe("Contenu de la note, factuel, une à trois phrases."),
        auteur: z.string().describe("Prénom de la personne qui rédige la note."),
      }),
      annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: false },
    },
    async ({ client_id, texte, auteur }) => {
      // TODO: append { date, auteur, texte } to the client's notes and save with sauver(data);
      // unknown client: { content: [...], isError: true } with a message that says how to fix the call.
      void sauver;
      return { content: [{ type: "text", text: `TODO: crm_add_note(${client_id}, ${texte}, ${auteur})` }], isError: true };
    },
  );

  server.registerResource(
    "fiche_client",
    new ResourceTemplate("crm://clients/{client_id}", { list: undefined }),
    { description: "Fiche complète d'un client : coordonnées, chiffre d'affaires, interlocuteur et notes.", mimeType: "application/json" },
    async (uri, { client_id }) => {
      // TODO: return { contents: [{ uri: uri.href, mimeType: "application/json", text: JSON.stringify(client, null, 2) }] }
      // for the matching client; unknown id: throw new ResourceNotFoundError(...).
      throw new ResourceNotFoundError(`TODO: fiche_client(${String(client_id)}) for ${uri.href}`);
    },
  );

  return server;
}
