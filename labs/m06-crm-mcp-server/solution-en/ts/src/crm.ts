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
      const q = query.trim().toLowerCase();
      const trouves = charger()
        .clients.filter(
          (c) => (!q || [c.nom, c.ville, c.interlocuteur].some((v) => v.toLowerCase().includes(q))) && (!secteur || c.secteur === secteur),
        )
        .slice(0, limit)
        .map(({ id, nom, ville, secteur, statut }) => ({ id, nom, ville, secteur, statut }));
      return { content: [{ type: "text", text: JSON.stringify(trouves, null, 2) }] };
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
      const data = charger();
      const client = data.clients.find((c) => c.id === client_id);
      if (!client) {
        return {
          content: [{ type: "text", text: `No customer "${client_id}". First look up the identifier with crm_search_clients.` }],
          isError: true,
        };
      }
      client.notes.push({ date: new Date().toISOString().slice(0, 10), auteur, texte });
      sauver(data);
      return { content: [{ type: "text", text: `Note added to ${client.nom} (${client_id}). The record has ${client.notes.length} note(s).` }] };
    },
  );

  server.registerResource(
    "fiche_client",
    new ResourceTemplate("crm://clients/{client_id}", { list: undefined }),
    { description: "Full customer record: details, revenue, contact person and notes.", mimeType: "application/json" },
    async (uri, { client_id }) => {
      const client = charger().clients.find((c) => c.id === String(client_id));
      if (!client) throw new ResourceNotFoundError(`No customer "${client_id}" in the CRM.`);
      return { contents: [{ uri: uri.href, mimeType: "application/json", text: JSON.stringify(client, null, 2) }] };
    },
  );

  return server;
}
