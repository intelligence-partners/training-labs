import { serveStdio } from "@modelcontextprotocol/server/stdio";
import { createServer } from "./crm.js";

void serveStdio(createServer);
console.error("orbis-crm: MCP server ready on stdio");
