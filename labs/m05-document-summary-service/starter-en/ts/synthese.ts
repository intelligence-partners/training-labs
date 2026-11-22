// synthese.ts
// Step 8 (optional): the same service in TypeScript, in one file.
// Run with: npx tsx synthese.ts rapport.pdf direction
import fs from "node:fs";
import Anthropic, { toFile } from "@anthropic-ai/sdk";
import { z } from "zod";

const client = new Anthropic({ maxRetries: 4, timeout: 300_000 });
const MODELE = "claude-opus-5-5";

const SCHEMA_SYNTHESE = {
  type: "object",
  properties: {
    titre: { type: "string" },
    type_document: { type: "string", enum: ["contrat", "rapport", "appel_d_offres", "proces_verbal", "autre"] },
    resume: { type: "string" },
    points_cles: { type: "array", items: { type: "string" } },
    chiffres_cles: {
      type: "array",
      items: {
        type: "object",
        properties: {
          libelle: { type: "string" },
          valeur: { type: "string" },
          page: { type: ["integer", "null"] },
        },
        required: ["libelle", "valeur", "page"],
        additionalProperties: false,
      },
    },
    risques: { type: "array", items: { type: "string" } },
    questions_ouvertes: { type: "array", items: { type: "string" } },
  },
  required: ["titre", "type_document", "resume", "points_cles", "chiffres_cles", "risques", "questions_ouvertes"],
  additionalProperties: false,
};

const Synthese = z
  .object({
    titre: z.string(),
    type_document: z.enum(["contrat", "rapport", "appel_d_offres", "proces_verbal", "autre"]),
    resume: z.string().min(1),
    points_cles: z.array(z.string()).min(3).max(7),
    chiffres_cles: z.array(
      z.object({ libelle: z.string(), valeur: z.string(), page: z.number().int().min(1).nullable() }).strict(),
    ),
    risques: z.array(z.string()),
    questions_ouvertes: z.array(z.string()),
  })
  .strict();

const CONSIGNES =
  "You are an analyst at a consulting firm. Rely only on the document provided, " +
  "copy figures with their unit, set page to null if it cannot be identified, " +
  "and write in English, in short sentences.";

const PROFILS: Record<string, string> = {
  direction: "Reader profile: executive management. Focus on financial stakes and major risks.",
  juridique: "Reader profile: legal department. Focus on commitments, deadlines and sensitive clauses.",
  operationnel: "Reader profile: operations manager. Focus on actions, timelines and dependencies.",
};

async function synthetiser(
  fileId: string,
  profil: string,
): Promise<{ synthese: z.infer<typeof Synthese>; modele: string; usage: Anthropic.Beta.BetaUsage }> {
  // TODO(step 8): the same request as service.py, with client.beta.messages.create:
  // model MODELE, max_tokens 16000, system CONSIGNES,
  // output_config { effort: "medium", format: { type: "json_schema", schema: SCHEMA_SYNTHESE } },
  // a document block { type: "document", source: { type: "file", file_id: fileId },
  // cache_control: { type: "ephemeral" } } then { type: "text", text: PROFILS[profil] },
  // fallbacks: "default" and betas: ["server-side-fallback-2026-07-01"].
  //
  // TODO(step 8): check stop_reason first ("refusal", then anything else than "end_turn"),
  // join the text blocks, validate with Synthese.safeParse(JSON.parse(texte)) and return
  // { synthese: verdict.data, modele: reponse.model, usage: reponse.usage }.
  void client;
  void MODELE;
  void SCHEMA_SYNTHESE;
  void CONSIGNES;
  void PROFILS;
  throw new Error(`TODO(step 8): synthetiser(${fileId}, ${profil})`);
}

const [chemin, profil = "direction"] = process.argv.slice(2);
const fichier = await client.files.upload({
  file: await toFile(fs.createReadStream(chemin), undefined, { type: "application/pdf" }),
});
try {
  const { synthese, modele, usage } = await synthetiser(fichier.id, profil);
  console.log(JSON.stringify(synthese, null, 2));
  console.error(
    `model: ${modele} | usage: input=${usage.input_tokens} cache_write=${usage.cache_creation_input_tokens ?? 0} ` +
      `cache_read=${usage.cache_read_input_tokens ?? 0} output=${usage.output_tokens}`,
  );
} catch (err) {
  if (err instanceof Anthropic.APIError) console.error(`API error ${err.status}: ${err.message}`);
  else console.error(`Summary failed: ${(err as Error).message}`);
  process.exitCode = 3;
}
