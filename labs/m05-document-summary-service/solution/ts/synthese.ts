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
  "Tu es analyste dans un cabinet de conseil. Tu t'appuies uniquement sur le document fourni, " +
  "tu recopies les chiffres avec leur unité, tu mets page à null si elle n'est pas identifiable, " +
  "et tu écris en français, phrases courtes.";

const PROFILS: Record<string, string> = {
  direction: "Profil de lecteur : direction générale. Priorité aux enjeux financiers et aux risques majeurs.",
  juridique: "Profil de lecteur : direction juridique. Priorité aux engagements, échéances et clauses sensibles.",
  operationnel: "Profil de lecteur : responsable opérationnel. Priorité aux actions, délais et dépendances.",
};

async function synthetiser(fileId: string, profil: string) {
  const reponse = await client.beta.messages.create({
    model: MODELE,
    max_tokens: 16000,
    system: CONSIGNES,
    output_config: { effort: "medium", format: { type: "json_schema", schema: SCHEMA_SYNTHESE } },
    messages: [
      {
        role: "user",
        content: [
          { type: "document", source: { type: "file", file_id: fileId }, cache_control: { type: "ephemeral" } },
          { type: "text", text: PROFILS[profil] },
        ],
      },
    ],
    fallbacks: "default",
    betas: ["server-side-fallback-2026-07-01"],
  });

  if (reponse.stop_reason === "refusal") {
    throw new Error(`demande déclinée (catégorie : ${reponse.stop_details?.category ?? "aucune"})`);
  }
  if (reponse.stop_reason !== "end_turn") {
    throw new Error(`sortie inexploitable (stop_reason : ${reponse.stop_reason})`);
  }

  const texte = reponse.content
    .filter((b): b is Anthropic.Beta.BetaTextBlock => b.type === "text")
    .map((b) => b.text)
    .join("");
  const verdict = Synthese.safeParse(JSON.parse(texte));
  if (!verdict.success) throw new Error(`sortie non conforme (${verdict.error.issues.length} erreur(s))`);
  return { synthese: verdict.data, modele: reponse.model, usage: reponse.usage };
}

const [chemin, profil = "direction"] = process.argv.slice(2);
const fichier = await client.files.upload({
  file: await toFile(fs.createReadStream(chemin), undefined, { type: "application/pdf" }),
});
try {
  const { synthese, modele, usage } = await synthetiser(fichier.id, profil);
  console.log(JSON.stringify(synthese, null, 2));
  console.error(
    `modèle : ${modele} | usage : input=${usage.input_tokens} cache_write=${usage.cache_creation_input_tokens ?? 0} ` +
      `cache_read=${usage.cache_read_input_tokens ?? 0} output=${usage.output_tokens}`,
  );
} catch (err) {
  if (err instanceof Anthropic.APIError) console.error(`Erreur API ${err.status} : ${err.message}`);
  else console.error(`Synthèse impossible : ${(err as Error).message}`);
  process.exitCode = 3;
}
