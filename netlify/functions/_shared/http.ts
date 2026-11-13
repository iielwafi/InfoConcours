import { createHmac, randomBytes } from "node:crypto";
import type { UserSession } from "./session.ts";
import { csrfToken, sessionFromRequest, validCsrf } from "./session.ts";

export type User = { id: number; username: string; email: string; role: "student" | "admin" };

export function escapeHtml(value: unknown): string {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[ch] ?? ch);
}

export function getCookie(request: Request, name: string): string | undefined {
  const raw = request.headers.get("cookie") ?? "";
  const part = raw.split(";").map((item) => item.trim()).find((item) => item.startsWith(name + "="));
  return part ? decodeURIComponent(part.slice(name.length + 1)) : undefined;
}

function preAuthToken(seed: string): string {
  const secret = process.env.SECRET_KEY;
  if (!secret || secret.length < 32) throw new Error("SECRET_KEY must contain at least 32 characters");
  return createHmac("sha256", secret).update("preauth:" + seed).digest("base64url");
}

export function csrfForPage(request: Request, session?: UserSession | null): { token: string; cookie?: string } {
  if (session) return { token: csrfToken(session) };
  const seed = getCookie(request, "ic_csrf_seed") ?? randomBytes(24).toString("base64url");
  return {
    token: preAuthToken(seed),
    cookie: "ic_csrf_seed=" + encodeURIComponent(seed) + "; Path=/; SameSite=Lax; Secure; Max-Age=3600",
  };
}

export function csrfValid(request: Request, form: FormData, session?: UserSession | null): boolean {
  const supplied = String(form.get("csrf_token") ?? "");
  if (session) return validCsrf(session, supplied);
  const seed = getCookie(request, "ic_csrf_seed");
  if (!seed) return false;
  try { return preAuthToken(seed) === supplied; } catch { return false; }
}

export function response(html: string, status = 200, extraHeaders: Record<string, string> = {}): Response {
  return new Response(html, {
    status,
    headers: {
      "content-type": "text/html; charset=utf-8",
      "x-content-type-options": "nosniff",
      "referrer-policy": "strict-origin-when-cross-origin",
      "x-frame-options": "SAMEORIGIN",
      "permissions-policy": "camera=(), microphone=(), geolocation=()",
      "cache-control": "no-store",
      ...extraHeaders,
    },
  });
}

export function redirect(path: string, extraHeaders: Record<string, string> = {}, status = 303): Response {
  return new Response(null, { status, headers: { location: path, ...extraHeaders } });
}

export function sessionFor(request: Request): UserSession | null {
  try { return sessionFromRequest(request); } catch { return null; }
}

export function flashBox(message?: string, tone = "success"): string {
  if (!message) return "";
  return '<div class="flash ' + escapeHtml(tone) + '" role="status">' + escapeHtml(message) + "</div>";
}

export function page(user: User | null, title: string, body: string, csrf = ""): string {
  const nav = user
    ? '<nav class="primary-nav"><a href="/dashboard">Vue d’ensemble</a><a href="/courses">Académie</a><a href="/courses/continue">Continuer</a><a href="/qcm">Entraînement</a><a class="ai-tutor-link" href="/tutor">Professeur IA ✦</a><details class="nav-more"><summary>Explorer⌄</summary><div class="nav-popover"><a href="/videos">Vidéothèque</a><a href="/planner">Plan de révision</a><a href="/exam">Examens blancs</a><a href="/study">Temps d’étude</a><a href="/errors">Carnet d’erreurs</a><a href="/bookmarks">Questions sauvegardées</a>' +
      (user.role === "admin" ? '<span class="nav-divider">Administration</span><a href="/admin">Vue d’ensemble</a><a href="/admin/curriculum">Académie et exercices</a><a href="/admin/videos">Vidéos</a><a href="/admin/quality">Qualité pédagogique</a>' : "") +
      '</div></details></nav><div class="header-actions"><a class="user-chip" href="/profile"><span class="avatar">' + escapeHtml(user.username.slice(0, 1).toUpperCase()) + '</span><span>' + escapeHtml(user.username) + '</span></a><form method="post" action="/logout"><input type="hidden" name="csrf_token" value="' + escapeHtml(csrf) + '"><button class="icon-button" aria-label="Se déconnecter">↗</button></form></div>'
    : '<nav class="primary-nav public-nav"><a href="/">Accueil</a><a href="/login">Connexion</a><a class="nav-cta" href="/register">Créer un compte ↗</a></nav>';
  return '<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#111827"><meta name="csrf-token" content="' + escapeHtml(csrf) + '"><title>' + escapeHtml(title) + ' · InfoConcours</title><link rel="icon" type="image/svg+xml" href="/static/favicon.svg"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet"><link rel="stylesheet" href="/static/app.css"><link rel="stylesheet" href="/static/premium.css"></head><body data-user-id="' + (user ? String(user.id) : "") + (title === "Examen blanc" ? ' data-exam-mode="true"' : "") + '"><a class="skip-link" href="#main-content">Passer au contenu</a><header class="top site-header"><a class="logo" href="/" aria-label="InfoConcours, accueil"><span class="logo-mark">IC</span><span class="logo-word">INFO<span>CONCOURS</span></span></a>' + nav + '<div class="utility-actions"><button class="theme" id="themeToggle" type="button">☾</button><button class="lang" id="langToggle" type="button">العربية / Darija</button></div></header><main id="main-content">' + body + '</main><footer class="site-footer"><a class="footer-brand" href="/"><span class="logo-mark">IC</span> INFOCONCOURS</a><span>Une préparation structurée. Un progrès mesurable.</span><small>Plateforme indépendante · Contenus d’entraînement non officiels</small></footer><script src="/static/app.js"></script><script src="/static/premium.js"></script><script src="/static/tutor.js"></script></body></html>';
}

export async function currentUser(request: Request, sql: ReturnType<typeof import("@neondatabase/serverless").neon>): Promise<{ user: User | null; session: UserSession | null }> {
  const session = sessionFor(request);
  if (!session) return { user: null, session: null };
  const rows = await sql`SELECT id, username, email, role FROM "user" WHERE id = ${session.userId} LIMIT 1`;
  if (!rows.length) return { user: null, session: null };
  const raw = rows[0] as Record<string, unknown>;
  return {
    user: {
      id: Number(raw.id),
      username: String(raw.username),
      email: String(raw.email),
      role: raw.role === "admin" ? "admin" : "student",
    },
    session,
  };
}

export function withCookie(res: Response, cookie: string): Response {
  res.headers.append("set-cookie", cookie);
  return res;
}
