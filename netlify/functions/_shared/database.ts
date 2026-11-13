import { neon } from "@neondatabase/serverless";

let cachedUrl: string | undefined;
let cachedClient: ReturnType<typeof neon> | undefined;

/** Reuses a Neon HTTP client on warm Netlify invocations. */
export function database() {
  const url = process.env.DATABASE_URL;
  if (!url) throw new Error("DATABASE_URL is not configured for Netlify Functions");
  if (!cachedClient || cachedUrl !== url) {
    cachedUrl = url;
    cachedClient = neon(url);
  }
  return cachedClient;
}
