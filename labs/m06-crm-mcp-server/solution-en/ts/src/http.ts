import { createMcpExpressApp } from "@modelcontextprotocol/express";
import { toNodeHandler } from "@modelcontextprotocol/node";
import { createMcpHandler } from "@modelcontextprotocol/server";
import type { NextFunction, Request, Response } from "express";
import { createServer } from "./crm.js";

const TOKEN = process.env.CRM_TOKEN;
const publicHost = new URL(process.env.CRM_PUBLIC_URL ?? "http://127.0.0.1:3000").hostname;
if (!TOKEN) throw new Error("Set CRM_TOKEN before starting the HTTP server.");

// Plain JSON responses: no SSE stream, compatible with tunnels that do not handle it.
const handler = createMcpHandler(createServer, { responseMode: "json" });
const node = toNodeHandler(handler);
const app = createMcpExpressApp({ host: "0.0.0.0", allowedHosts: ["127.0.0.1", "localhost", publicHost] });

// Static demo token. In production: OAuth 2.1 and requireBearerAuth.
function exigerJeton(req: Request, res: Response, next: NextFunction) {
  if (req.headers.authorization !== `Bearer ${TOKEN}`) {
    res.status(401).json({ error: "invalid_token" });
    return;
  }
  next();
}

app.all("/mcp", exigerJeton, (req, res) => void node(req, res, req.body));
app.listen(3000, () => console.error("orbis-crm: http://127.0.0.1:3000/mcp"));
