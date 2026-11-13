import type { Config } from "@netlify/functions";
import { neon } from "@neondatabase/serverless";

/** Read-only deployment probe. It never creates tables or changes Neon data. */
export default async function health(): Promise<Response> {
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) {
    return Response.json(
      { ok: false, service: "infoconcours", status: "missing_database_configuration" },
      { status: 503 },
    );
  }

  try {
    const sql = neon(databaseUrl);
    await sql`SELECT 1 AS ok`;
    return Response.json({ ok: true, service: "infoconcours", database: "connected" });
  } catch {
    // Do not reveal connection strings, hostnames, or database error details.
    return Response.json(
      { ok: false, service: "infoconcours", status: "database_unavailable" },
      { status: 503 },
    );
  }
}

export const config: Config = { path: "/api/health" };
