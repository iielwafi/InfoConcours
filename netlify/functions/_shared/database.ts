import { neon } from "@neondatabase/serverless";

type QueryRows = Record<string, any>[];
export type NeonSqlTag = (strings: TemplateStringsArray, ...values: any[]) => Promise<QueryRows>;

let cachedUrl: string | undefined;
let cachedClient: NeonSqlTag | undefined;

/** Reuses a Neon HTTP client on warm Netlify invocations. */
export function database(): NeonSqlTag {
  const url = process.env.DATABASE_URL;
  if (!url) throw new Error("DATABASE_URL is not configured for Netlify Functions");
  if (!cachedClient || cachedUrl !== url) {
    cachedUrl = url;
    // The app uses Neon's default object-row mode (fullResults=false, arrayMode=false).
    // Narrow the library's overload union to the rows shape actually returned at runtime.
    cachedClient = neon(url) as unknown as NeonSqlTag;
  }
  return cachedClient;
}
