import { createMcpExpressApp } from "@modelcontextprotocol/express";
import { toNodeHandler } from "@modelcontextprotocol/node";
import { createMcpHandler } from "@modelcontextprotocol/server";
import type { NextFunction, Request, Response } from "express";
import { createServer } from "./crm.js";

const TOKEN = process.env.CRM_TOKEN;
const publicHost = new URL(process.env.CRM_PUBLIC_URL ?? "http://127.0.0.1:3000").hostname;
if (!TOKEN) throw new Error("Définissez CRM_TOKEN avant de lancer le serveur HTTP.");

// Réponses JSON simples : pas de flux SSE, compatible avec les tunnels qui ne le gèrent pas.
const handler = createMcpHandler(createServer, { responseMode: "json" });
const node = toNodeHandler(handler);
const app = createMcpExpressApp({ host: "0.0.0.0", allowedHosts: ["127.0.0.1", "localhost", publicHost] });

// Jeton statique de démonstration. En production : OAuth 2.1 et requireBearerAuth.
function exigerJeton(req: Request, res: Response, next: NextFunction) {
  if (req.headers.authorization !== `Bearer ${TOKEN}`) {
    res.status(401).json({ error: "invalid_token" });
    return;
  }
  next();
}

app.all("/mcp", exigerJeton, (req, res) => void node(req, res, req.body));
app.listen(3000, () => console.error("orbis-crm : http://127.0.0.1:3000/mcp"));
