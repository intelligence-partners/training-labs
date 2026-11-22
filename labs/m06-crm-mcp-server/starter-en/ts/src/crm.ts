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
    { instructions: "Orbis CRM tools: search customers, read a record, add a follow-up note." },
  );

  server.registerTool(
    "crm_search_clients",
    {
      description:
        "Searches customers and prospects in the Orbis CRM. Use it as soon as the user mentions a company, " +
        "a city or a contact person, before reading a record or adding a note. Returns the identifier (C-XXXX), " +
        "name, city, sector and status, without the notes: read the crm://clients/{id} resource for details.",
      inputSchema: z.object({
        query: z.string().describe("Name, city or contact person to search for, case-insensitive. Empty string to list everything."),
        secteur: z.enum(SECTEURS).optional().describe("Optional filter on the business sector."),
        limit: z.number().int().min(1).max(20).default(5).describe("Maximum number of results."),
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
        "Adds a follow-up note dated today to a customer record. Only call this tool if the user " +
        "explicitly asks to save a note: the write is permanent. Returns a confirmation.",
      inputSchema: z.object({
        client_id: z.string().describe("Customer identifier, in the C-XXXX format, obtained with crm_search_clients."),
        texte: z.string().describe("Content of the note, factual, one to three sentences."),
        auteur: z.string().describe("First name of the person writing the note."),
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
    { description: "Full customer record: details, revenue, contact person and notes.", mimeType: "application/json" },
    async (uri, { client_id }) => {
      // TODO: return { contents: [{ uri: uri.href, mimeType: "application/json", text: JSON.stringify(client, null, 2) }] }
      // for the matching client; unknown id: throw new ResourceNotFoundError(...).
      throw new ResourceNotFoundError(`TODO: fiche_client(${String(client_id)}) for ${uri.href}`);
    },
  );

  return server;
}
