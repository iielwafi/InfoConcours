import type { Config } from "@netlify/functions";
import { createHash, createHmac, timingSafeEqual } from "node:crypto";
import { database } from "./_shared/database.js";
import { createSession, readSession, cookieHeader, expiredCookieHeader } from "./_shared/session.js";
import {
  currentUser, csrfForPage, csrfValid, escapeHtml, flashBox, page, redirect, response, withCookie,
} from "./_shared/http.js";
import { hashPassword, verifyPassword } from "./_shared/password.js";

type Row = Record<string, any>;
const e = escapeHtml;
const val = (form: FormData, key: string) => String(form.get(key) ?? "").trim();
const hidden = (name: string, value: string) => '<input type="hidden" name="' + e(name) + '" value="' + e(value) + '">';
const field = (label: string, name: string, type = "text", value = "", required = false) =>
  '<label>' + e(label) + '</label><input class="field" name="' + e(name) + '" type="' + e(type) + '" value="' + e(value) + '"' + (required ? " required" : "") + '>';
const btn = (text: string) => '<button class="btn primary">' + e(text) + '</button>';
const card = (title: string, body: string, meta = "") =>
  '<article class="feature"><div class="eyebrow">' + e(meta) + '</div><h3>' + e(title) + '</h3><p>' + body + '</p></article>';
const section = (title: string, body: string, intro = "") =>
  '<section class="section"><div class="section-head"><div class="eyebrow">INFOCONCOURS</div><h2>' + e(title) + '</h2><p>' + e(intro) + '</p></div>' + body + '</section>';
const csrfField = (token: string) => hidden("csrf_token", token);
const postForm = (action: string, token: string, inner: string) =>
  '<form method="post" action="' + e(action) + '">' + csrfField(token) + inner + '</form>';
const formatDate = (value: unknown) => value ? new Date(String(value)).toLocaleDateString("fr-FR") : "";
const parseJson = (value: unknown, fallback: any = []) => {
  try { return JSON.parse(String(value ?? "")); } catch { return fallback; }
};
const safeNotice = (url: URL) => flashBox(url.searchParams.get("notice") ?? undefined, url.searchParams.get("tone") ?? "success");
const toNotice = (path: string, message: string, tone = "success") =>
  redirect(path + (path.includes("?") ? "&" : "?") + "notice=" + encodeURIComponent(message) + "&tone=" + encodeURIComponent(tone));
const authRequired = (url: URL) => redirect("/login?notice=" + encodeURIComponent("Connecte-toi pour accéder à ton espace.") + "&tone=error");
const adminRequired = () => response("<h1>403 · Accès refusé</h1><p>Cette page est réservée à l’administration.</p>", 403);
const questionBlock = (q: Row, token: string, prefix = "a") => {
  const options = parseJson(q.options_fr);
  const learning = q.learning_objective ? '<small>' + e(q.learning_objective) + '</small>' : "";
  return '<article class="feature q-card"><div class="eyebrow">' + e(q.domain) + ' · ' + e(q.level) + '</div><h3>' + e(q.prompt_fr) + '</h3>' + learning +
    options.map((option: string, i: number) => '<label class="option"><input type="radio" name="' + prefix + e(q.id) + '" value="' + i + '" required> ' + e(option) + '</label>').join("") + '</article>';
};
const questionSelect = "id, domain, topic, level, prompt_fr, prompt_ar, options_fr, options_ar, answer, explanation_fr, explanation_ar";
const cookieSecure = () => process.env.COOKIE_SECURE !== "0";

type AssessmentPayload = { purpose: "diagnostic" | "qcm" | "exam"; userId: number; ids: number[]; issuedAt: number; startedAt?: number };
function signAssessment(purpose: AssessmentPayload["purpose"], userId: number, ids: number[], startedAt?: number): string {
  const secret = process.env.SECRET_KEY;
  if (!secret || secret.length < 32) throw new Error("SECRET_KEY must contain at least 32 characters");
  const payload: AssessmentPayload = { purpose, userId, ids, issuedAt: Date.now(), ...(startedAt ? { startedAt } : {}) };
  const encoded = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const signature = createHmac("sha256", secret).update(encoded).digest("base64url");
  return encoded + "." + signature;
}
function readAssessment(token: string, purpose: AssessmentPayload["purpose"], userId: number, maxAgeMs = 30 * 60 * 1000): AssessmentPayload | null {
  try {
    const secret = process.env.SECRET_KEY;
    if (!secret || secret.length < 32) return null;
    const [encoded, provided] = token.split(".");
    if (!encoded || !provided) return null;
    const expected = Buffer.from(createHmac("sha256", secret).update(encoded).digest("base64url"));
    const actual = Buffer.from(provided);
    if (expected.length !== actual.length || !timingSafeEqual(expected, actual)) return null;
    const payload = JSON.parse(Buffer.from(encoded, "base64url").toString("utf8")) as AssessmentPayload;
    if (payload.purpose !== purpose || payload.userId !== userId || !Array.isArray(payload.ids) || !payload.ids.length || payload.ids.length > 100) return null;
    if (!payload.ids.every((id) => Number.isInteger(id) && id > 0) || !Number.isInteger(payload.issuedAt)) return null;
    if (Date.now() - payload.issuedAt > maxAgeMs || payload.issuedAt > Date.now() + 60_000) return null;
    return payload;
  } catch { return null; }
}
function normalizeAnswer(value: string): string {
  const chars = Array.from(value.normalize("NFKD").toLocaleLowerCase("fr")).filter((ch) => {
    const code = ch.codePointAt(0) ?? 0;
    return !(code >= 0x300 && code <= 0x36f);
  });
  const cleaned = chars.map((ch) => {
    const code = ch.codePointAt(0) ?? 0;
    const asciiAlphaNumeric = (code >= 48 && code <= 57) || (code >= 97 && code <= 122);
    if (code <= 127 && !asciiAlphaNumeric) return " ";
    return ch;
  }).join("");
  return cleaned.trim().replace(/ +/g, " ");
}
function shortAnswerMatches(submitted: string, accepted: string[]): boolean {
  const normalized = normalizeAnswer(submitted);
  const numeric = Number(submitted.replace(",", "."));
  return accepted.some((candidate) => {
    if (normalized === normalizeAnswer(candidate)) return true;
    const other = Number(String(candidate).replace(",", "."));
    return submitted.trim() !== "" && Number.isFinite(numeric) && Number.isFinite(other) && numeric === other;
  });
}
async function evaluateOpenAnswer(exercise: Row, answer: string): Promise<Row> {
  const apiKey = process.env.OPENAI_API_KEY?.trim();
  if (!apiKey) throw new Error("not_configured");
  const model = (process.env.EXERCISE_GRADING_MODEL || "gpt-4o-mini").trim();
  const controller = AbortSignal.timeout(20_000);
  const prompt = {
    title: exercise.title,
    question: exercise.prompt_fr,
    expected_solution: exercise.solution_fr,
    rubric: exercise.grading_guide_fr || "",
    learning_objective: exercise.learning_objective_fr || "",
    student_answer: answer,
  };
  const response = await fetch("https://api.openai.com/v1/responses", {
    method: "POST",
    signal: controller,
    headers: { authorization: "Bearer " + apiKey, "content-type": "application/json" },
    body: JSON.stringify({
      model,
      instructions: "Tu es un correcteur pédagogique prudent pour des exercices d’informatique. Évalue le sens, les concepts essentiels, le raisonnement et l’objectif pédagogique. N’invente pas de critères. Si la réponse ne permet pas une évaluation fiable, choisis une confiance basse. Réponds uniquement avec un objet JSON contenant score (0..100), classification (correct|partially_correct|incorrect), explanation_fr, missing_concepts (tableau), expected_answer_fr et confidence (0..1).",
      input: JSON.stringify(prompt),
      text: { format: { type: "json_object" } },
      max_output_tokens: 700,
    }),
  });
  if (!response.ok) throw new Error("provider_unavailable");
  const payload = await response.json() as Row;
  let text = "";
  for (const item of payload.output ?? []) for (const part of item.content ?? []) if (part.type === "output_text") text = part.text;
  const result = JSON.parse(text) as Row;
  if (!Number.isFinite(result.score) || result.score < 0 || result.score > 100 || !Number.isFinite(result.confidence) || result.confidence < 0 || result.confidence > 1 || !["correct","partially_correct","incorrect"].includes(result.classification) || typeof result.explanation_fr !== "string") throw new Error("invalid_grading_result");
  return result;
}

const authHash = (scope: string, identity: string) =>
  createHash("sha256").update(scope + "|" + identity).digest("hex");
async function authBlocked(sql: any, key: string): Promise<boolean> {
  const rows = await sql`SELECT window_started,attempts FROM auth_throttle WHERE key=${key} LIMIT 1`;
  if (!rows.length) return false;
  if (Date.now() - new Date(String(rows[0].window_started)).getTime() > 15 * 60 * 1000) {
    await sql`DELETE FROM auth_throttle WHERE key=${key}`;
    return false;
  }
  return Number(rows[0].attempts) >= 10;
}
async function authFailure(sql: any, key: string): Promise<void> {
  await sql`INSERT INTO auth_throttle (key,window_started,attempts) VALUES (${key},NOW(),1) ON CONFLICT (key) DO UPDATE SET attempts=CASE WHEN auth_throttle.window_started < NOW()-INTERVAL '15 minutes' THEN 1 ELSE auth_throttle.attempts+1 END,window_started=CASE WHEN auth_throttle.window_started < NOW()-INTERVAL '15 minutes' THEN NOW() ELSE auth_throttle.window_started END`;
}
async function clearAuthFailure(sql: any, keys: string[]): Promise<void> {
  for (const key of keys) await sql`DELETE FROM auth_throttle WHERE key=${key}`;
}


async function pageResponse(request: Request, user: any, session: any, title: string, body: string, status = 200): Promise<Response> {
  const csrf = csrfForPage(request, session);
  const res = response(page(user, title, safeNotice(new URL(request.url)) + body, csrf.token), status, csrf.cookie ? { "set-cookie": csrf.cookie } : {});
  return res;
}
async function requirePostCsrf(request: Request, form: FormData, session: any): Promise<boolean> {
  return csrfValid(request, form, session);
}
async function getQuestions(sql: any, ids: number[]): Promise<Row[]> {
  if (!ids.length) return [];
  const rows = await sql`SELECT id, domain, topic, level, prompt_fr, prompt_ar, options_fr, options_ar, answer, explanation_fr, explanation_ar FROM question WHERE active = TRUE AND id = ANY(${ids}::int[])`;
  const byId = new Map(rows.map((row: Row) => [Number(row.id), row]));
  return ids.map((id) => byId.get(id)).filter(Boolean) as Row[];
}
async function recordAttempt(sql: any, userId: number, mode: string, details: Row[], duration = 0) {
  const score = details.filter((d) => d.ok).length;
  const rows = await sql`INSERT INTO attempt (user_id, mode, score, total, details, duration_minutes) VALUES (${userId}, ${mode}, ${score}, ${details.length}, ${JSON.stringify(details)}, ${duration}) RETURNING id, score, total, created_at, duration_minutes`;
  return rows[0] as Row;
}
function detailsFor(q: Row, selected: string | null): Row {
  const options = parseJson(q.options_fr);
  const valid = selected !== null && /^\d+$/.test(selected) && Number(selected) >= 0 && Number(selected) < options.length;
  const ok = valid && Number(selected) === Number(q.answer);
  return {
    question_id: Number(q.id), topic: q.topic, domain: q.domain, level: q.level,
    prompt: q.prompt_fr, prompt_ar: q.prompt_ar, ok, explanation: q.explanation_fr,
    explanation_ar: q.explanation_ar, answer: Number(q.answer), options,
    options_ar: parseJson(q.options_ar), selected: valid ? Number(selected) : null,
  };
}

export default async function handler(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const path = decodeURIComponent(url.pathname);
  const method = request.method.toUpperCase();
  try {
    const sql = database();
    const auth = await currentUser(request, sql);
    const user = auth.user;
    const session = auth.session;
    const form = method === "POST" ? await request.formData() : new FormData();
    if (method === "POST" && !await requirePostCsrf(request, form, session)) {
      return response("<h1>419 · Formulaire expiré</h1><p>Recharge la page et réessaie.</p>", 419);
    }

    if (path === "/" && method === "GET") {
      if (user) return redirect("/dashboard");
      const body = '<section class="hero landing-hero"><div class="hero-copy"><div class="eyebrow">PLATEFORME DE PRÉPARATION · INFORMATIQUE</div><h1>Prépare ton concours.<br><em>Maîtrise chaque notion.</em></h1><p>Une méthode claire pour progresser en algorithmique, programmation, systèmes, réseaux et outils numériques. Cours ciblés, entraînement intelligent et examens blancs.</p><div class="actions"><a class="btn primary" href="/register">Commencer gratuitement ↗</a><a class="btn ghost" href="#programme">Découvrir le programme</a></div><div class="hero-note"><span>✦</span> Français + Darija · Suivi personnel · Entraînement progressif</div></div><div class="landing-art" aria-hidden="true"><div class="landing-ring ring-one"></div><div class="landing-ring ring-two"></div><div class="landing-grid"></div><div class="floating-card card-code"><b>&lt;/&gt;</b><span>ALGORITHMIQUE</span></div><div class="floating-card card-data"><b>∑</b><span>DONNÉES</span></div><div class="landing-book"><div class="landing-book-cover"><span>IC</span><i>Informatique<br>et concours</i></div><div class="landing-book-pages"></div></div><div class="landing-cap"><div class="cap-top"></div><div class="cap-base"></div><span></span></div><div class="landing-spark spark-a">✦</div><div class="landing-spark spark-b">✧</div></div></section><section class="stats"><div><b>8</b><span>Domaines évalués</span></div><div><b>45%</b><span>Développement</span></div><div><b>30%</b><span>Systèmes & réseaux</span></div><div><b>25%</b><span>Logiciels</span></div></section><section id="programme" class="section"><div class="section-head"><div class="eyebrow">TON ESPACE DE TRAVAIL</div><h2>Tout ton parcours, au même endroit.</h2></div><div class="feature-grid">' +
        card("Diagnostic personnalisé", "Identifie tes acquis et les notions à renforcer dans les huit domaines.", "01") +
        card("Académie de cours", "Des fiches structurées, des explications et des exemples en français et Darija.", "02") +
        card("Entraînement QCM", "Questions par domaine et niveau, correction et explication après chaque test.", "03") +
        card("Plan de progression", "Une feuille de route construite à partir des résultats du diagnostic.", "04") +
        card("Examens blancs", "Une simulation chronométrée pour travailler la gestion du temps.", "05") +
        card("Suivi des efforts", "Historique des séances, temps de travail et évolution des résultats.", "06") +
        '</div></section><section class="cta"><h2>Commence par connaître ton niveau.</h2><p>Crée ton espace et lance ton premier diagnostic.</p><a class="btn primary" href="/register">Créer mon espace ↗</a></section>';
      return pageResponse(request, null, null, "Accueil", body);
    }

    if ((path === "/register" || path === "/login") && method === "GET") {
      if (user) return redirect("/dashboard");
      const isRegister = path === "/register";
      const csrf = csrfForPage(request, null);
      const formHtml = isRegister
        ? field("Nom d’utilisateur", "username", "text", "", true) + field("Adresse email", "email", "email", "", true) + field("Mot de passe", "password", "password", "", true) + field("Confirmer le mot de passe", "confirm", "password", "", true)
        : field("Nom d’utilisateur", "username", "text", "", true) + field("Mot de passe", "password", "password", "", true);
      const body = '<section class="auth-wrap"><div class="auth-aside"><div class="eyebrow">INFOCONCOURS · TON ESPACE</div><h1>' + (isRegister ? 'Construis ton<br><em>plan de réussite.</em>' : 'Content de te<br><em>revoir.</em>') + '</h1><p>Un espace de préparation organisé autour de tes objectifs et de ton niveau.</p></div><div class="auth-card"><h2>' + (isRegister ? "Créer un compte" : "Connexion") + '</h2><p class="muted">Accède à ton espace personnel.</p><form method="post" action="' + path + '">' + csrfField(csrf.token) + formHtml + btn(isRegister ? "Créer mon compte" : "Se connecter") + '</form><p class="switch">' + (isRegister ? 'Déjà inscrit ? <a href="/login">Se connecter</a>' : 'Pas encore de compte ? <a href="/register">Créer un compte</a>') + '</p></div></section>';
      return response(page(null, isRegister ? "Créer un compte" : "Connexion", safeNotice(url) + body, csrf.token), 200, csrf.cookie ? { "set-cookie": csrf.cookie } : {});
    }

    if (path === "/register" && method === "POST") {
      if (user) return redirect("/dashboard");
      const ip = request.headers.get("x-nf-client-connection-ip") ?? (request.headers.get("x-forwarded-for") ?? "unknown").split(",")[0].trim();
      const registerKey = authHash("register", ip);
      if (await authBlocked(sql, registerKey)) return response("<h1>429 · Trop de tentatives</h1><p>Réessaie dans 15 minutes.</p>", 429);
      const username = val(form, "username"), email = val(form, "email").toLowerCase();
      const password = String(form.get("password") ?? ""), confirm = String(form.get("confirm") ?? "");
      if (username.length < 3 || username.length > 40 || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email) || password.length < 8 || password !== confirm) {
        await authFailure(sql, registerKey);
        return toNotice("/register", "Vérifie les champs : nom (3 caractères), email valide et mot de passe de 8 caractères minimum.", "error");
      }
      const found = await sql`SELECT id FROM "user" WHERE username = ${username} OR email = ${email} LIMIT 1`;
      if (found.length) { await authFailure(sql, registerKey); return toNotice("/register", "Nom d’utilisateur ou email déjà utilisé.", "error"); }
      const rows = await sql`INSERT INTO "user" (username,email,password_hash,role) VALUES (${username},${email},${hashPassword(password)},${"student"}) RETURNING id,username,email,role`;
      const created = rows[0] as Row;
      const token = createSession({ userId: Number(created.id), role: "student", language: "fr" });
      await sql`INSERT INTO user_preference (user_id,language) VALUES (${Number(created.id)},${"fr"}) ON CONFLICT (user_id) DO NOTHING`;
      return redirect("/dashboard", { "set-cookie": cookieHeader(token, cookieSecure()) });
    }

    if (path === "/login" && method === "POST") {
      if (user) return redirect("/dashboard");
      const username = val(form, "username"), password = String(form.get("password") ?? "");
      const ip = request.headers.get("x-nf-client-connection-ip") ?? (request.headers.get("x-forwarded-for") ?? "unknown").split(",")[0].trim();
      const userKey = authHash("login-user", username.toLowerCase() + "|" + ip);
      const ipKey = authHash("login-ip", ip);
      if (await authBlocked(sql, userKey) || await authBlocked(sql, ipKey)) return response("<h1>429 · Trop de tentatives</h1><p>Réessaie dans 15 minutes.</p>", 429);
      const rows = await sql`SELECT id,username,email,password_hash,role FROM "user" WHERE username = ${username} LIMIT 1`;
      const found = rows[0] as Row | undefined;
      if (!found || !verifyPassword(password, String(found.password_hash))) {
        await authFailure(sql, userKey); await authFailure(sql, ipKey);
        return toNotice("/login", "Identifiants incorrects.", "error");
      }
      await clearAuthFailure(sql, [userKey, ipKey]);
      const pref = await sql`SELECT language FROM user_preference WHERE user_id = ${Number(found.id)} LIMIT 1`;
      const token = createSession({ userId: Number(found.id), role: found.role === "admin" ? "admin" : "student", language: pref[0]?.language === "ar" ? "ar" : "fr" });
      return redirect("/dashboard", { "set-cookie": cookieHeader(token, cookieSecure()) });
    }

    if (path === "/logout" && method === "POST") {
      if (!user) return redirect("/");
      return redirect("/", { "set-cookie": expiredCookieHeader(cookieSecure()) });
    }

    if (!user) return authRequired(url);

    if (path === "/profile" && (method === "GET" || method === "POST")) {
      if (method === "POST") {
        const action = val(form, "action");
        if (action === "email") {
          const email = val(form, "email").toLowerCase();
          if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return toNotice("/profile", "Adresse email invalide.", "error");
          const clash = await sql`SELECT id FROM "user" WHERE email = ${email} AND id <> ${user.id} LIMIT 1`;
          if (clash.length) return toNotice("/profile", "Cette adresse est déjà utilisée.", "error");
          await sql`UPDATE "user" SET email = ${email} WHERE id = ${user.id}`;
          return toNotice("/profile", "Adresse mise à jour.");
        }
        if (action === "password") {
          const rows = await sql`SELECT password_hash FROM "user" WHERE id = ${user.id}`;
          if (!rows.length || !verifyPassword(String(form.get("current_password") ?? ""), String(rows[0].password_hash))) return toNotice("/profile", "Le mot de passe actuel est incorrect.", "error");
          const next = String(form.get("new_password") ?? ""), confirm = String(form.get("confirm_password") ?? "");
          if (next.length < 8 || next !== confirm) return toNotice("/profile", "Le nouveau mot de passe doit contenir 8 caractères et correspondre à la confirmation.", "error");
          await sql`UPDATE "user" SET password_hash = ${hashPassword(next)} WHERE id = ${user.id}`;
          return toNotice("/profile", "Mot de passe mis à jour.");
        }
        return response("<h1>400 · Action invalide</h1>", 400);
      }
      const body = '<section class="auth-wrap"><div class="auth-aside"><div class="eyebrow">MON COMPTE</div><h1>Gère ton<br><em>espace personnel.</em></h1><p>Modifie ton adresse email ou ton mot de passe.</p></div><div class="auth-card"><h2>Profil</h2><p class="muted">' + e(user.username) + '</p>' +
        postForm("/profile", csrfForPage(request, session).token, '<input type="hidden" name="action" value="email">' + field("Adresse email", "email", "email", user.email, true) + btn("Mettre à jour l’email")) +
        '<hr><h3>Changer le mot de passe</h3>' +
        postForm("/profile", csrfForPage(request, session).token, '<input type="hidden" name="action" value="password">' + field("Mot de passe actuel", "current_password", "password", "", true) + field("Nouveau mot de passe", "new_password", "password", "", true) + field("Confirmer", "confirm_password", "password", "", true) + btn("Changer le mot de passe")) +
        '</div></section>';
      return pageResponse(request, user, session, "Profil", body);
    }

    if (path === "/dashboard" && method === "GET") {
      const [latest, today, goal, attempts, totals, lessons] = await Promise.all([
        sql`SELECT id,total,created_at,scores FROM diagnostic WHERE user_id = ${user.id} ORDER BY created_at DESC LIMIT 1`,
        sql`SELECT COALESCE(SUM(minutes),0) AS minutes FROM study_session WHERE user_id = ${user.id} AND studied_on = CURRENT_DATE`,
        sql`SELECT daily_minutes FROM study_goal WHERE user_id = ${user.id} LIMIT 1`,
        sql`SELECT id,mode,score,total,created_at,duration_minutes FROM attempt WHERE user_id = ${user.id} ORDER BY created_at DESC LIMIT 8`,
        sql`SELECT COUNT(*) AS attempts, COALESCE(AVG(score*100.0/NULLIF(total,0)),0) AS average FROM attempt WHERE user_id = ${user.id} AND mode = 'qcm'`,
        sql`SELECT (SELECT COUNT(*) FROM curriculum_lesson WHERE published=TRUE) AS published, (SELECT COUNT(*) FROM lesson_completion WHERE user_id = ${user.id}) AS completed`,
      ]);
      const mins = Number(today[0]?.minutes ?? 0), dailyGoal = goal[0]?.daily_minutes ? Number(goal[0].daily_minutes) : null;
      const body = '<section class="section"><div class="section-head"><div class="eyebrow">TON ESPACE PERSONNEL</div><h2>Bonjour, ' + e(user.username) + ' 👋</h2><p>Voici ton évolution sur InfoConcours.</p></div><div class="feature-grid">' +
        card("Temps étudié aujourd’hui", mins + " minutes", "SUIVI") +
        card("Objectif quotidien", dailyGoal ? dailyGoal + " minutes · " + Math.min(100, Math.round(mins * 100 / dailyGoal)) + " %" : "Non défini", "OBJECTIF") +
        card("QCM réalisés", String(totals[0]?.attempts ?? 0), "ENTRAÎNEMENT") +
        card("Moyenne QCM", Math.round(Number(totals[0]?.average ?? 0)) + " %", "PROGRESSION") +
        card("Leçons terminées", Number(lessons[0]?.completed ?? 0) + " / " + Number(lessons[0]?.published ?? 0), "ACADÉMIE") +
        card("Dernier diagnostic", latest[0] ? formatDate(latest[0].created_at) + " · " + e(latest[0].total) + " bonnes réponses" : "Pas encore réalisé", "DIAGNOSTIC") +
        '</div><div class="actions"><a class="btn primary" href="/diagnostic">Faire mon diagnostic</a><a class="btn ghost" href="/courses">Voir les cours</a><a class="btn ghost" href="/study">Enregistrer une séance</a></div></section>' +
        '<section class="section"><div class="section-head"><h2>Activité récente</h2></div><div class="table-wrap"><table><thead><tr><th>Type</th><th>Score</th><th>Date</th></tr></thead><tbody>' +
        attempts.map((a: Row) => '<tr><td>' + e(a.mode) + '</td><td>' + e(a.score) + ' / ' + e(a.total) + '</td><td>' + e(formatDate(a.created_at)) + '</td></tr>').join("") + '</tbody></table></div></section>';
      return pageResponse(request, user, session, "Vue d’ensemble", body);
    }

    if (path === "/diagnostic" && (method === "GET" || method === "POST")) {
      if (method === "GET") {
        const domains = await sql`SELECT name FROM curriculum_subject WHERE published=TRUE ORDER BY position,name`;
        const selected: Row[] = [];
        for (const d of domains) {
          const rows = await sql`SELECT id, domain, topic, level, prompt_fr, prompt_ar, options_fr, options_ar, answer, explanation_fr, explanation_ar FROM question WHERE active=TRUE AND domain=${String(d.name)} ORDER BY random() LIMIT 3`;
          selected.push(...rows as Row[]);
        }
        const token = csrfForPage(request, session).token;
        const body = '<section class="section"><div class="section-head"><div class="eyebrow">DIAGNOSTIC INITIAL</div><h2>Évalue ton niveau.</h2><p>Trois questions par domaine. Les résultats seront enregistrés dans ton compte.</p></div>' +
          postForm("/diagnostic", token, hidden("assessment_token", signAssessment("diagnostic", user.id, selected.map(q => Number(q.id)))) + selected.map(q => questionBlock(q, token)).join("") + btn("Terminer le diagnostic")) + '</section>';
        return pageResponse(request, user, session, "Diagnostic", body);
      }
      const signed = readAssessment(val(form, "assessment_token"), "diagnostic", user.id);
      if (!signed) return toNotice("/diagnostic", "Ce diagnostic a expiré. Relance une nouvelle série.", "error");
      const ids = signed.ids;
      const qs = await getQuestions(sql, ids);
      const domains = await sql`SELECT name,weight FROM curriculum_subject WHERE published=TRUE ORDER BY position,name`;
      const scores: Row = {}; let total = 0;
      for (const d of domains) {
        const group = qs.filter((q) => q.domain === d.name);
        const answered = group.filter((q) => form.has("a" + q.id));
        const correct = answered.filter((q) => val(form, "a" + q.id) === String(q.answer)).length;
        total += correct;
        scores[String(d.name)] = { correct, count: answered.length, available: group.length, percent: answered.length ? Math.round(correct * 100 / answered.length) : 0, weight: Number(d.weight) };
      }
      const rows = await sql`INSERT INTO diagnostic (user_id,scores,total) VALUES (${user.id},${JSON.stringify(scores)},${total}) RETURNING id`;
      return redirect("/diagnostic/" + rows[0].id);
    }

    const diagnosticMatch = path.match(/^\/diagnostic\/(\d+)$/);
    if (diagnosticMatch && method === "GET") {
      const rows = await sql`SELECT id,scores,total,created_at FROM diagnostic WHERE id=${Number(diagnosticMatch[1])} AND user_id=${user.id} LIMIT 1`;
      if (!rows.length) return response("<h1>404 · Diagnostic introuvable</h1>", 404);
      const scores = parseJson(rows[0].scores, {});
      const body = '<section class="section"><div class="section-head"><div class="eyebrow">RÉSULTAT DU DIAGNOSTIC</div><h2>Ton bilan</h2><p>' + e(formatDate(rows[0].created_at)) + '</p></div><div class="feature-grid">' +
        Object.entries(scores).map(([name, entry]: [string, any]) => card(name, entry.count ? entry.percent + " % · " + entry.correct + "/" + entry.count : "Pas assez de réponses", "MATIÈRE")).join("") +
        '</div><div class="actions"><a class="btn primary" href="/courses">Commencer les cours</a><a class="btn ghost" href="/dashboard">Retour au tableau de bord</a></div></section>';
      return pageResponse(request, user, session, "Résultat du diagnostic", body);
    }

    if (path === "/courses" && method === "GET") {
      const subjects = await sql`SELECT s.id,s.slug,s.name,s.category,s.weight,COUNT(l.id) AS lesson_count FROM curriculum_subject s LEFT JOIN curriculum_module m ON m.subject_id=s.id AND m.published=TRUE LEFT JOIN curriculum_chapter c ON c.module_id=m.id AND c.published=TRUE LEFT JOIN curriculum_lesson l ON l.chapter_id=c.id AND l.published=TRUE WHERE s.published=TRUE GROUP BY s.id ORDER BY s.position,s.name`;
      const completed = await sql`SELECT COUNT(*) AS total FROM lesson_completion WHERE user_id=${user.id}`;
      const body = '<section class="section"><div class="section-head"><div class="eyebrow">ACADÉMIE</div><h2>Choisis une matière.</h2><p>' + e(completed[0]?.total ?? 0) + ' leçons terminées au total.</p></div><div class="feature-grid">' +
        subjects.map((s: Row) => '<a class="feature" href="/courses/' + encodeURIComponent(s.slug) + '"><div class="eyebrow">' + e(s.category) + ' · ' + e(s.weight) + ' %</div><h3>' + e(s.name) + '</h3><p>' + e(s.lesson_count) + ' leçons disponibles</p><span class="btn ghost">Ouvrir ↗</span></a>').join("") +
        '</div></section>';
      return pageResponse(request, user, session, "Académie", body);
    }

    if (path === "/courses/continue" && method === "GET") {
      const rows = await sql`SELECT s.slug,l.id FROM lesson_progress p JOIN curriculum_lesson l ON l.id=CAST(SPLIT_PART(p.lesson_key,':',2) AS INTEGER) JOIN curriculum_chapter c ON c.id=l.chapter_id JOIN curriculum_module m ON m.id=c.module_id JOIN curriculum_subject s ON s.id=m.subject_id LEFT JOIN lesson_completion done ON done.lesson_id=l.id AND done.user_id=p.user_id WHERE p.user_id=${user.id} AND p.lesson_key LIKE 'lesson:%' AND l.published=TRUE AND done.id IS NULL ORDER BY p.updated_at DESC LIMIT 1`;
      if (rows.length) return redirect("/courses/" + encodeURIComponent(rows[0].slug) + "/lesson/" + rows[0].id);
      const first = await sql`SELECT s.slug,l.id FROM curriculum_lesson l JOIN curriculum_chapter c ON c.id=l.chapter_id JOIN curriculum_module m ON m.id=c.module_id JOIN curriculum_subject s ON s.id=m.subject_id LEFT JOIN lesson_completion done ON done.lesson_id=l.id AND done.user_id=${user.id} WHERE l.published=TRUE AND c.published=TRUE AND m.published=TRUE AND s.published=TRUE AND done.id IS NULL ORDER BY s.position,m.position,c.position,l.id LIMIT 1`;
      return first.length ? redirect("/courses/" + encodeURIComponent(first[0].slug) + "/lesson/" + first[0].id) : redirect("/courses");
    }

    const lessonMatch = path.match(/^\/courses\/([^/]+)\/lesson\/(\d+)$/);
    const subjectMatch = path.match(/^\/courses\/([^/]+)$/);
    if (subjectMatch && method === "GET") {
      const slug = subjectMatch[1];
      const subjects = await sql`SELECT id,name,slug FROM curriculum_subject WHERE slug=${slug} AND published=TRUE LIMIT 1`;
      if (!subjects.length) return response("<h1>404 · Matière introuvable</h1>", 404);
      const lessons = await sql`SELECT l.id,l.title,l.chapter_id,c.title AS chapter_title,m.title AS module_title FROM curriculum_lesson l JOIN curriculum_chapter c ON c.id=l.chapter_id JOIN curriculum_module m ON m.id=c.module_id WHERE m.subject_id=${Number(subjects[0].id)} AND l.published=TRUE AND c.published=TRUE AND m.published=TRUE ORDER BY m.position,c.position,l.id`;
      const done = await sql`SELECT lesson_id FROM lesson_completion WHERE user_id=${user.id}`;
      const doneIds = new Set(done.map((r: Row) => Number(r.lesson_id)));
      const list = lessons.map((l: Row) => '<a class="feature" href="/courses/' + encodeURIComponent(slug) + '/lesson/' + l.id + '"><div class="eyebrow">' + e(l.module_title) + ' · ' + e(l.chapter_title) + '</div><h3>' + e(l.title) + '</h3><p>' + (doneIds.has(Number(l.id)) ? "✓ Leçon terminée" : "Ouvrir la leçon") + '</p></a>').join("");
      return pageResponse(request, user, session, String(subjects[0].name), section(String(subjects[0].name), '<div class="feature-grid">' + list + '</div>'));
    }

    if (lessonMatch && (method === "GET" || method === "POST")) {
      const slug = lessonMatch[1], lessonId = Number(lessonMatch[2]);
      const lessons = await sql`SELECT l.*,c.title AS chapter_title,m.title AS module_title,s.id AS subject_id,s.slug,s.name AS subject_name FROM curriculum_lesson l JOIN curriculum_chapter c ON c.id=l.chapter_id JOIN curriculum_module m ON m.id=c.module_id JOIN curriculum_subject s ON s.id=m.subject_id WHERE s.slug=${slug} AND l.id=${lessonId} AND s.published=TRUE AND m.published=TRUE AND c.published=TRUE AND l.published=TRUE LIMIT 1`;
      if (!lessons.length) return response("<h1>404 · Leçon introuvable</h1>", 404);
      const lesson = lessons[0] as Row;
      if (method === "POST") {
        const meta = await sql`SELECT q.id, q.domain, q.topic, q.level, q.prompt_fr, q.prompt_ar, q.options_fr, q.options_ar, q.answer, q.explanation_fr, q.explanation_ar FROM question q JOIN question_metadata qm ON qm.question_id=q.id WHERE qm.chapter_id=${Number(lesson.chapter_id)} AND q.active=TRUE ORDER BY q.id`;
        const details = (meta as Row[]).map((q) => detailsFor(q, form.has("a" + q.id) ? val(form, "a" + q.id) : null));
        if (!details.length) return toNotice("/courses/" + slug + "/lesson/" + lessonId, "Aucun QCM publié n’est associé à ce chapitre.", "error");
        const attempt = await recordAttempt(sql, user.id, "qcm", details);
        await sql`INSERT INTO lesson_progress (user_id,lesson_key,evidence_count) VALUES (${user.id},${"lesson:" + lessonId},0) ON CONFLICT (user_id,lesson_key) DO UPDATE SET updated_at=NOW()`;
        if (details.length >= 3 && Number(attempt.score) / Number(attempt.total) >= 0.7) {
          await sql`UPDATE lesson_progress SET evidence_count=evidence_count+${details.length},updated_at=NOW() WHERE user_id=${user.id} AND lesson_key=${"lesson:" + lessonId}`;
        }
        return redirect("/courses/" + slug + "/lesson/" + lessonId);
      }
      await sql`INSERT INTO lesson_progress (user_id,lesson_key,evidence_count) VALUES (${user.id},${"lesson:" + lessonId},0) ON CONFLICT (user_id,lesson_key) DO UPDATE SET updated_at=NOW()`;
      const exercises = await sql`SELECT id,title,prompt_fr,prompt_ar,solution_fr,solution_ar,exercise_type,options_json,correct_answer,accepted_answers_json,feedback_fr,level FROM course_exercise WHERE lesson_id=${lessonId} AND published=TRUE ORDER BY id`;
      const exerciseIds = exercises.map((x: Row) => {
          const kind = String(x.exercise_type), options = parseJson(x.options_json, []);
          let answer = kind === "qcm"
            ? options.map((option: string, index: number) => '<label class="option"><input type="radio" name="answer" value="' + index + '" required> ' + e(option) + '</label>').join("")
            : kind === "true_false"
              ? '<label class="option"><input type="radio" name="answer" value="true" required> Vrai</label><label class="option"><input type="radio" name="answer" value="false" required> Faux</label>'
              : kind === "open"
                ? '<label>Ta réponse</label><textarea class="field" name="answer" rows="5" maxlength="12000" required></textarea><p class="notice">' + (process.env.OPENAI_API_KEY ? "Évaluation IA; les réponses incertaines restent en correction manuelle." : "Pas de correcteur IA configuré : la réponse sera corrigée par un enseignant.") + '</p>'
                : field("Ta réponse", "answer", "text", "", true);
          const history = (attemptsByExercise.get(Number(x.id)) ?? []).map((a: Row) => {
            const state = a.status === "pending_manual" ? "En attente de correction" : a.status === "ai_graded" ? "Évaluée par l’IA" : a.status === "auto_graded" ? "Correction automatique" : "Corrigée par un enseignant";
            const tone = a.status === "pending_manual" ? "exercise-result-pending" : Number(a.score) >= 100 ? "exercise-result-correct" : Number(a.score) > 0 ? "exercise-result-pending" : "exercise-result-incorrect";
            return '<div class="exercise-feedback"><div class="qmeta"><span>' + e(formatDate(a.created_at)) + '</span><span>' + state + (a.score !== null ? ' · ' + Math.round(Number(a.score)) + ' %' : '') + '</span></div><p><b>Ta réponse :</b> ' + e(a.submitted_answer) + '</p>' + (a.feedback ? '<div class="exercise-result ' + tone + '">' + e(a.feedback) + '</div>' : '') + (a.status !== "pending_manual" && x.solution_fr ? '<details><summary>Voir la correction complète</summary><div class="theory-body">' + e(x.solution_fr) + '</div></details>' : '') + '</div>';
          }).join("");
          return '<article class="feature exercise-card" id="exercise-' + e(x.id) + '"><div class="eyebrow">' + e(kind === "qcm" ? "QCM" : kind === "true_false" ? "Vrai / faux" : kind === "short_answer" ? "Réponse courte" : "Réponse ouverte") + ' · ' + e(x.level) + '</div><h3>' + e(x.title) + '</h3><p>' + e(x.prompt_fr) + '</p>' + (x.prompt_ar ? '<div class="darija" lang="ar" dir="rtl">' + e(x.prompt_ar) + '</div>' : '') + postForm("/exercise/" + x.id + "/attempt", csrf, answer + btn("Envoyer ma réponse")) + history + '</article>';
        }).join("")) + '</div>' : '<p class="muted">Aucune vidéo vérifiée pour cette leçon.</p>') +
        '<h3>Exercices</h3><div class="feature-grid">' + exercises.map((x: Row) => '<article class="feature"><div class="eyebrow">' + e(x.level) + ' · ' + e(x.exercise_type) + '</div><h3>' + e(x.title) + '</h3><p>' + e(x.prompt_fr) + '</p>' + postForm("/exercise/" + x.id + "/attempt", csrf, field("Ta réponse", "answer", "text", "", true) + hidden("exercise_id", String(x.id)) + btn("Envoyer ma réponse")) + '</article>').join("") + '</div>' +
        (qs.length ? '<h3>Vérifie tes acquis</h3>' + postForm("/courses/" + slug + "/lesson/" + lessonId, csrf, qs.map((q: Row) => questionBlock(q, csrf)).join("") + btn("Envoyer le QCM")) : "") +
        '<div class="actions"><a class="btn ghost" href="/courses/' + encodeURIComponent(slug) + '">Retour à la matière</a>' + postForm("/courses/" + slug + "/lesson/" + lessonId + "/complete", csrf, btn("Marquer comme terminée")) + '</div></section>';
      return pageResponse(request, user, session, String(lesson.title), body);
    }

    const completeMatch = path.match(/^\/courses\/([^/]+)\/lesson\/(\d+)\/complete$/);
    if (completeMatch && method === "POST") {
      const lessonId = Number(completeMatch[2]);
      const valid = await sql`SELECT l.id FROM curriculum_lesson l JOIN curriculum_chapter c ON c.id=l.chapter_id JOIN curriculum_module m ON m.id=c.module_id JOIN curriculum_subject s ON s.id=m.subject_id WHERE l.id=${lessonId} AND s.slug=${completeMatch[1]} AND l.published=TRUE LIMIT 1`;
      if (!valid.length) return response("<h1>404 · Leçon introuvable</h1>", 404);
      await sql`INSERT INTO lesson_completion (user_id,lesson_id) VALUES (${user.id},${lessonId}) ON CONFLICT (user_id,lesson_id) DO NOTHING`;
      return toNotice("/courses/" + completeMatch[1] + "/lesson/" + lessonId, "Leçon marquée comme terminée.");
    }

    const exerciseMatch = path.match(/^\/exercise\/(\d+)\/attempt$/);
    if (exerciseMatch && method === "POST") {
      const exerciseId = Number(exerciseMatch[1]), answer = String(form.get("answer") ?? "").trim();
      if (!answer || answer.length > 12000) return toNotice("/courses/continue", "Saisis une réponse de 1 à 12 000 caractères.", "error");
      const rows = await sql`SELECT x.id,x.lesson_id,x.title,x.exercise_type,x.correct_answer,x.accepted_answers_json,x.feedback_fr,x.solution_fr,x.grading_guide_fr,x.learning_objective_fr,l.published AS lesson_published,c.published AS chapter_published,m.published AS module_published,s.published AS subject_published,s.slug FROM course_exercise x JOIN curriculum_lesson l ON l.id=x.lesson_id JOIN curriculum_chapter c ON c.id=l.chapter_id JOIN curriculum_module m ON m.id=c.module_id JOIN curriculum_subject s ON s.id=m.subject_id WHERE x.id=${exerciseId} AND x.published=TRUE LIMIT 1`;
      if (!rows.length) return response("<h1>404 · Exercice introuvable</h1>", 404);
      const x = rows[0] as Row;
      if (!x.lesson_published || !x.chapter_published || !x.module_published || !x.subject_published) return response("<h1>404 · Exercice indisponible</h1>", 404);
      const kind = String(x.exercise_type);
      let score: number | null = null, status = "pending_manual", feedback = "Réponse transmise à un enseignant pour correction.";
      if (kind === "qcm") {
        const correct = answer === String(x.correct_answer);
        score = correct ? 100 : 0; status = "auto_graded"; feedback = String(x.feedback_fr || x.solution_fr || (correct ? "Bonne réponse." : "Réponse incorrecte."));
      } else if (kind === "true_false") {
        const correct = answer.toLowerCase() === String(x.correct_answer ?? "").toLowerCase();
        score = correct ? 100 : 0; status = "auto_graded"; feedback = String(x.feedback_fr || x.solution_fr || (correct ? "Bonne réponse." : "Réponse incorrecte."));
      } else if (kind === "short_answer") {
        const accepted = parseJson(x.accepted_answers_json, []).map((value: unknown) => String(value));
        if (x.correct_answer !== null && x.correct_answer !== undefined) accepted.push(String(x.correct_answer));
        const correct = shortAnswerMatches(answer, accepted);
        score = correct ? 100 : 0; status = "auto_graded"; feedback = String(x.feedback_fr || x.solution_fr || (correct ? "Bonne réponse." : "Réponse incorrecte."));
      } else if (kind === "open") {
        try {
          const result = await evaluateOpenAnswer(x, answer);
          if (result.confidence >= 0.70) {
            score = Number(result.score); status = "ai_graded";
            const labels: Record<string,string> = { correct: "Réponse correcte", partially_correct: "Réponse partiellement correcte", incorrect: "Réponse incorrecte" };
            const parts = [labels[String(result.classification)] + " — " + String(result.explanation_fr)];
            if (Array.isArray(result.missing_concepts) && result.missing_concepts.length) parts.push("Notions à compléter : " + result.missing_concepts.map(String).join(", "));
            if (result.expected_answer_fr) parts.push("Correction attendue : " + String(result.expected_answer_fr));
            feedback = parts.join("\\n\\n").slice(0, 8000);
          } else {
            feedback = "Évaluation automatique incertaine; réponse transmise à un enseignant pour correction.";
          }
        } catch (error) {
          const reason = error instanceof Error ? error.message : "provider_unavailable";
          feedback = reason === "not_configured"
            ? "Aucun évaluateur IA n’est configuré. Ta réponse est en attente de correction manuelle."
            : "L’évaluateur IA est indisponible ou sa réponse n’a pas pu être validée. Ta réponse est en attente de correction manuelle.";
        }
      } else {
        return response("<h1>400 · Type d’exercice invalide</h1>", 400);
      }
      await sql`INSERT INTO exercise_attempt (user_id,exercise_id,submitted_answer,score,feedback,status) VALUES (${user.id},${exerciseId},${answer},${score},${feedback},${status})`;
      return redirect("/courses/" + encodeURIComponent(String(x.slug)) + "/lesson/" + Number(x.lesson_id) + "#exercise-" + exerciseId);
    }

    if (path === "/qcm" && (method === "GET" || method === "POST")) {
      if (method === "GET") {
        const domain = url.searchParams.get("domain") ?? "", level = url.searchParams.get("level") ?? "";
        const qs = await sql`SELECT id, domain, topic, level, prompt_fr, prompt_ar, options_fr, options_ar, answer, explanation_fr, explanation_ar FROM question WHERE active=TRUE AND (${domain}='' OR domain=${domain}) AND (${level}='' OR level=${level}) ORDER BY random() LIMIT 15`;
        const token = csrfForPage(request, session).token;
        const body = '<section class="section"><div class="section-head"><div class="eyebrow">ENTRAÎNEMENT</div><h2>Teste tes connaissances.</h2><p>Une série de 15 questions corrigées après soumission.</p></div>' +
          '<form method="get" action="/qcm">' + field("Matière (optionnel)", "domain") + field("Niveau (optionnel)", "level") + '<button class="btn ghost">Filtrer</button></form>' +
          postForm("/qcm", token, hidden("assessment_token", signAssessment("qcm", user.id, qs.map((q: Row) => Number(q.id)))) + qs.map((q: Row) => questionBlock(q, token)).join("") + btn("Corriger mes réponses")) +
          '</section>';
        return pageResponse(request, user, session, "Entraînement QCM", body);
      }
      const signed = readAssessment(val(form, "assessment_token"), "qcm", user.id);
      if (!signed) return toNotice("/qcm", "Cette série de QCM a expiré. Lance un nouvel entraînement.", "error");
      const ids = signed.ids;
      const qs = await getQuestions(sql, ids);
      const details = qs.map((q) => detailsFor(q, form.has("a" + q.id) ? val(form, "a" + q.id) : null));
      if (!details.length) return toNotice("/qcm", "Aucune question valide n’a été soumise.", "error");
      const attempt = await recordAttempt(sql, user.id, "qcm", details);
      const body = '<section class="section"><div class="section-head"><div class="eyebrow">RÉSULTAT DU QCM</div><h2>' + e(attempt.score) + ' / ' + e(attempt.total) + '</h2><p>' + Math.round(Number(attempt.score) * 100 / Number(attempt.total)) + ' %</p></div><div class="feature-grid">' +
        details.map((d) => card(d.prompt, (d.ok ? "✓ Bonne réponse" : "✗ Réponse incorrecte") + "<br>" + e(d.explanation), d.domain)).join("") +
        '</div><div class="actions"><a class="btn primary" href="/qcm">Nouvel entraînement</a><a class="btn ghost" href="/dashboard">Tableau de bord</a></div></section>';
      return pageResponse(request, user, session, "Résultat du QCM", body);
    }

    if (path === "/exam" && (method === "GET" || method === "POST")) {
      if (method === "GET") {
        const qs = await sql`SELECT id, domain, topic, level, prompt_fr, prompt_ar, options_fr, options_ar, answer, explanation_fr, explanation_ar FROM question WHERE active=TRUE ORDER BY random() LIMIT 30`;
        const token = csrfForPage(request, session).token, started = Date.now();
        const assessmentToken = signAssessment("exam", user.id, qs.map((q: Row) => Number(q.id)), started);
        const body = '<section class="section"><div class="section-head"><div class="eyebrow">EXAMEN BLANC</div><h2>Simulation de concours.</h2><p>30 questions · ' + Math.max(5, Math.min(240, Number(process.env.EXAM_DURATION_MINUTES ?? 240))) + ' minutes.</p></div>' +
          postForm("/exam", token, hidden("assessment_token", assessmentToken) + qs.map((q: Row) => questionBlock(q, token)).join("") + btn("Terminer l’examen")) + '</section>';
        return pageResponse(request, user, session, "Examen blanc", body);
      }
      const signed = readAssessment(val(form, "assessment_token"), "exam", user.id, 6 * 60 * 60 * 1000);
      if (!signed?.startedAt || Date.now() - signed.startedAt > 6 * 60 * 60 * 1000 || signed.startedAt > Date.now() + 60_000) return toNotice("/exam", "Cette session d’examen a expiré. Lance un nouvel examen.", "error");
      const start = signed.startedAt;
      const qs = await getQuestions(sql, signed.ids);
      if (!qs.length) return toNotice("/exam", "Aucune question valide n’a été soumise.", "error");
      const elapsed = Math.max(0, Math.floor((Date.now() - start) / 60000));
      const limit = Math.max(5, Math.min(240, Number(process.env.EXAM_DURATION_MINUTES ?? 240)));
      const details = qs.map((q) => detailsFor(q, elapsed <= limit ? (form.has("a" + q.id) ? val(form, "a" + q.id) : null) : null));
      const attempt = await recordAttempt(sql, user.id, "exam", details, Math.min(limit, elapsed));
      const body = '<section class="section"><div class="section-head"><div class="eyebrow">RÉSULTAT DE L’EXAMEN BLANC</div><h2>' + e(attempt.score) + ' / ' + e(attempt.total) + '</h2><p>' + Math.round(Number(attempt.score) * 100 / Number(attempt.total)) + ' % · ' + e(attempt.duration_minutes) + ' min</p></div><div class="actions"><a class="btn primary" href="/exam">Nouvel examen</a><a class="btn ghost" href="/dashboard">Tableau de bord</a></div></section>';
      return pageResponse(request, user, session, "Résultat de l’examen", body);
    }

    if (path === "/study" && (method === "GET" || method === "POST")) {
      if (method === "POST") {
        if (val(form, "action") === "goal") {
          const mins = Number(form.get("daily_goal"));
          if (!Number.isInteger(mins) || mins < 15 || mins > 720) return toNotice("/study", "L’objectif doit être compris entre 15 et 720 minutes.", "error");
          await sql`INSERT INTO study_goal (user_id,daily_minutes) VALUES (${user.id},${mins}) ON CONFLICT (user_id) DO UPDATE SET daily_minutes=${mins},updated_at=NOW()`;
          return toNotice("/study", "Objectif quotidien enregistré.");
        }
        const domain = val(form, "domain"), minutes = Number(form.get("minutes"));
        if (!domain || !Number.isInteger(minutes) || minutes < 1 || minutes > 720) return toNotice("/study", "Vérifie la matière et la durée (1 à 720 minutes).", "error");
        await sql`INSERT INTO study_session (user_id,domain,minutes,studied_on) VALUES (${user.id},${domain},${minutes},CURRENT_DATE)`;
        return redirect("/dashboard");
      }
      const [goal, sessions, weekly, totals, domains] = await Promise.all([
        sql`SELECT daily_minutes FROM study_goal WHERE user_id=${user.id} LIMIT 1`,
        sql`SELECT domain,minutes,studied_on FROM study_session WHERE user_id=${user.id} ORDER BY studied_on DESC,id DESC LIMIT 20`,
        sql`SELECT COALESCE(SUM(minutes),0) AS total FROM study_session WHERE user_id=${user.id} AND studied_on>=CURRENT_DATE-6`,
        sql`SELECT domain,SUM(minutes) AS total FROM study_session WHERE user_id=${user.id} GROUP BY domain ORDER BY total DESC`,
        sql`SELECT name FROM curriculum_subject WHERE published=TRUE ORDER BY position`,
      ]);
      const token = csrfForPage(request, session).token;
      const body = '<section class="section"><div class="section-head"><div class="eyebrow">TEMPS D’ÉTUDE</div><h2>Mes séances et mon objectif.</h2><p>Cette semaine : ' + e(weekly[0]?.total ?? 0) + ' minutes.</p></div><div class="feature-grid">' +
        card("Objectif quotidien", goal[0] ? goal[0].daily_minutes + " minutes" : "Non défini", "OBJECTIF") +
        card("Temps étudié cette semaine", String(weekly[0]?.total ?? 0) + " min", "SUIVI") +
        '</div><div class="feature-grid"><article class="feature"><h3>Enregistrer une séance</h3>' +
        postForm("/study", token, '<label>Matière</label><select class="field" name="domain">' + domains.map((d: Row) => '<option value="' + e(d.name) + '">' + e(d.name) + '</option>').join("") + '</select>' + field("Durée (minutes)", "minutes", "number", "60", true) + btn("Enregistrer")) +
        '</article><article class="feature"><h3>Mon objectif par jour</h3>' +
        postForm("/study", token, hidden("action", "goal") + field("Minutes par jour", "daily_goal", "number", goal[0] ? String(goal[0].daily_minutes) : "60", true) + btn("Enregistrer l’objectif")) +
        '</article></div><h3>Répartition par matière</h3><div class="feature-grid">' + totals.map((t: Row) => card(String(t.domain), t.total + " minutes", "TEMPS CUMULÉ")).join("") + '</div><h3>Historique récent</h3><div class="table-wrap"><table><thead><tr><th>Matière</th><th>Durée</th><th>Date</th></tr></thead><tbody>' + sessions.map((s: Row) => '<tr><td>' + e(s.domain) + '</td><td>' + e(s.minutes) + ' min</td><td>' + e(formatDate(s.studied_on)) + '</td></tr>').join("") + '</tbody></table></div></section>';
      return pageResponse(request, user, session, "Temps d’étude", body);
    }

    if (path === "/planner" && method === "GET") {
      const rows = await sql`SELECT domain,ROUND(AVG(score*100.0/NULLIF(total,0))) AS average,COUNT(*) AS attempts FROM attempt WHERE user_id=${user.id} AND mode='qcm' GROUP BY domain ORDER BY average ASC NULLS FIRST`;
      const body = section("Ton plan de révision", '<div class="feature-grid">' + rows.map((r: Row) => card(String(r.domain), r.average == null ? "Aucun résultat pour le moment" : r.average + " % · " + r.attempts + " séries", "PRIORITÉ DE RÉVISION")).join("") + '</div><div class="actions"><a class="btn primary" href="/qcm">Lancer un QCM</a><a class="btn ghost" href="/courses">Revoir les cours</a></div>', "Les matières sans résultats apparaissent en premier.");
      return pageResponse(request, user, session, "Plan de révision", body);
    }

    if (path === "/errors" && method === "GET") {
      const rows = await sql`SELECT details,mode,created_at FROM attempt WHERE user_id=${user.id} ORDER BY created_at DESC`;
      const errors: Row[] = [];
      for (const a of rows) for (const d of parseJson(a.details, [])) if (!d.ok) errors.push({ ...d, mode: a.mode, date: a.created_at });
      const bookmarks = await sql`SELECT question_id FROM bookmark WHERE user_id=${user.id}`;
      const saved = new Set(bookmarks.map((b: Row) => Number(b.question_id)));
      const token = csrfForPage(request, session).token;
      const body = section("Carnet d’erreurs", errors.length ? '<div class="feature-grid">' + errors.map((d) => '<article class="feature"><div class="eyebrow">' + e(d.domain) + ' · ' + e(d.mode) + ' · ' + e(formatDate(d.date)) + '</div><h3>' + e(d.prompt) + '</h3><p>' + e(d.explanation) + '</p>' + postForm("/bookmark/" + d.question_id, token, btn(saved.has(Number(d.question_id)) ? "Retirer des favoris" : "Sauvegarder")) + '</article>').join("") + '</div>' : '<p>Aucune erreur enregistrée pour le moment. Continue les entraînements !</p>', "Les réponses incorrectes de tes QCM et examens sont regroupées ici.");
      return pageResponse(request, user, session, "Carnet d’erreurs", body);
    }

    const bookmarkMatch = path.match(/^\/bookmark\/(\d+)$/);
    if (bookmarkMatch && method === "POST") {
      const qid = Number(bookmarkMatch[1]);
      const found = await sql`SELECT id FROM question WHERE id=${qid} AND active=TRUE LIMIT 1`;
      if (!found.length) return response("<h1>404 · Question introuvable</h1>", 404);
      const exists = await sql`SELECT id FROM bookmark WHERE user_id=${user.id} AND question_id=${qid} LIMIT 1`;
      if (exists.length) await sql`DELETE FROM bookmark WHERE user_id=${user.id} AND question_id=${qid}`;
      else await sql`INSERT INTO bookmark (user_id,question_id) VALUES (${user.id},${qid}) ON CONFLICT (user_id,question_id) DO NOTHING`;
      return redirect("/errors");
    }

    if (path === "/bookmarks" && method === "GET") {
      const rows = await sql`SELECT q.id,q.domain,q.topic,q.level,q.prompt_fr,q.explanation_fr FROM bookmark b JOIN question q ON q.id=b.question_id WHERE b.user_id=${user.id} AND q.active=TRUE ORDER BY b.created_at DESC`;
      const body = section("Questions sauvegardées", '<div class="feature-grid">' + rows.map((q: Row) => card(q.prompt_fr, e(q.explanation_fr), q.domain + " · " + q.level)).join("") + '</div>', "Garde ici les questions à revoir.");
      return pageResponse(request, user, session, "Questions sauvegardées", body);
    }

    if (path === "/language" && method === "POST") {
      const language = val(form, "language");
      if (language !== "fr" && language !== "ar") return response("<h1>400 · Langue invalide</h1>", 400);
      await sql`INSERT INTO user_preference (user_id,language) VALUES (${user.id},${language}) ON CONFLICT (user_id) DO UPDATE SET language=${language}`;
      return new Response(JSON.stringify({ language }), { headers: { "content-type": "application/json" } });
    }

    if (path === "/videos" && method === "GET") {
      const rows = await sql`SELECT v.id,v.title,v.channel,v.video_id,v.language,v.duration_minutes,vm.description,vm.lesson_id,vm.chapter_id FROM video_resource v LEFT JOIN video_metadata vm ON vm.video_id=v.id WHERE v.active=TRUE AND v.verified=TRUE AND v.verification_status='verified' ORDER BY v.lesson_key,v.title`;
      const watched = await sql`SELECT video_id FROM video_watch WHERE user_id=${user.id}`;
      const watchedIds = new Set(watched.map((r: Row) => Number(r.video_id)));
      const token = csrfForPage(request, session).token;
      const body = section("Vidéothèque", '<div class="feature-grid">' + rows.map((v: Row) => '<article class="feature"><h3>' + e(v.title) + '</h3><p>' + e(v.channel) + ' · ' + e(v.language) + '</p><iframe title="' + e(v.title) + '" src="https://www.youtube-nocookie.com/embed/' + e(v.video_id) + '" loading="lazy" allowfullscreen></iframe><p>' + e(v.description) + '</p>' + postForm("/videos/" + v.id + "/watched", token, hidden("next", "/videos") + btn(watchedIds.has(Number(v.id)) ? "Déjà visionnée" : "Marquer comme visionnée")) + '</article>').join("") + '</div>', rows.length ? "Ressources validées par l’administration." : "Aucune vidéo vérifiée pour le moment.");
      return pageResponse(request, user, session, "Vidéothèque", body);
    }

    const watchedMatch = path.match(/^\/videos\/(\d+)\/watched$/);
    if (watchedMatch && method === "POST") {
      const videoId = Number(watchedMatch[1]);
      const exists = await sql`SELECT id FROM video_watch WHERE user_id=${user.id} AND video_id=${videoId} LIMIT 1`;
      if (exists.length) await sql`DELETE FROM video_watch WHERE user_id=${user.id} AND video_id=${videoId}`;
      else await sql`INSERT INTO video_watch (user_id,video_id) VALUES (${user.id},${videoId}) ON CONFLICT (user_id,video_id) DO NOTHING`;
      const next = val(form, "next");
      return redirect(next.startsWith("/") && !next.startsWith("//") ? next : "/videos");
    }

    if (path.startsWith("/admin")) {
      if (user.role !== "admin") return adminRequired();
      if (path === "/admin" && method === "POST") {
        const action = val(form, "action");
        if (action === "toggle_question") {
          const questionId = Number(form.get("question_id"));
          await sql`UPDATE question SET active=NOT active WHERE id=${questionId}`;
          return redirect("/admin");
        }
        if (action === "set_role") {
          const targetId = Number(form.get("user_id")), role = val(form, "role");
          if (!Number.isInteger(targetId) || !["student", "admin"].includes(role) || targetId === user.id) {
            return toNotice("/admin", "Modification de rôle invalide.", "error");
          }
          await sql`UPDATE "user" SET role=${role} WHERE id=${targetId}`;
          return redirect("/admin");
        }
        if (action === "create_question") {
          const domain = val(form, "domain"), topic = val(form, "topic"), level = val(form, "level"), prompt = val(form, "prompt_fr"), explanation = val(form, "explanation_fr");
          const options = [0,1,2,3].map(i => val(form, "option_" + i));
          const answer = Number(form.get("answer")), chapterId = Number(form.get("chapter_id"));
          const objective = val(form, "learning_objective").slice(0,400), timeLimitRaw = val(form, "time_limit_seconds");
          const timeLimit = timeLimitRaw ? Number(timeLimitRaw) : null;
          if (!domain || !topic || !prompt || !explanation || !objective || new Set(options).size !== 4 || options.some(x => !x) || !Number.isInteger(answer) || answer < 0 || answer > 3 || !Number.isInteger(chapterId) || (timeLimit !== null && (!Number.isInteger(timeLimit) || timeLimit < 5 || timeLimit > 7200))) {
            return toNotice("/admin", "Question invalide : complète la matière, le chapitre, les quatre choix et la correction.", "error");
          }
          const chapters = await sql`SELECT c.id,s.name AS domain FROM curriculum_chapter c JOIN curriculum_module m ON m.id=c.module_id JOIN curriculum_subject s ON s.id=m.subject_id WHERE c.id=${chapterId} LIMIT 1`;
          if (!chapters.length || chapters[0].domain !== domain) return toNotice("/admin", "Le chapitre ne correspond pas à la matière sélectionnée.", "error");
          const duplicates = await sql`SELECT id FROM question WHERE domain=${domain} AND prompt_fr=${prompt} LIMIT 1`;
          if (duplicates.length) return toNotice("/admin", "Cette question existe déjà.", "error");
          const created = await sql`INSERT INTO question (domain,topic,level,prompt_fr,prompt_ar,options_fr,options_ar,answer,explanation_fr,explanation_ar,active) VALUES (${domain},${topic.slice(0,120)},${level},${prompt},${val(form,"prompt_ar")},${JSON.stringify(options)},${JSON.stringify(options)},${answer},${explanation},${val(form,"explanation_ar")},FALSE) RETURNING id`;
          const lesson = await sql`SELECT id FROM curriculum_lesson WHERE chapter_id=${chapterId} ORDER BY id LIMIT 1`;
          await sql`INSERT INTO question_metadata (question_id,chapter_id,lesson_id,time_limit_seconds,learning_objective) VALUES (${Number(created[0].id)},${chapterId},${lesson[0]?.id ?? null},${timeLimit},${objective})`;
          return toNotice("/admin", "Question créée en brouillon. Active-la après relecture.");
        }
        return response("<h1>400 · Action invalide</h1>", 400);
      }

      if (path === "/admin" && method === "GET") {
        const [counts, recent, questions, subjects, chapters] = await Promise.all([
          sql`SELECT (SELECT COUNT(*) FROM "user") AS users,(SELECT COUNT(*) FROM question WHERE active=TRUE) AS questions,(SELECT COUNT(*) FROM attempt) AS attempts,(SELECT COUNT(*) FROM curriculum_lesson WHERE published=TRUE) AS lessons`,
          sql`SELECT id,username,email,role,created_at FROM "user" ORDER BY created_at DESC LIMIT 20`,
          sql`SELECT id,domain,topic,level,prompt_fr,active FROM question ORDER BY id DESC LIMIT 20`,
          sql`SELECT name FROM curriculum_subject WHERE published=TRUE ORDER BY position`,
          sql`SELECT c.id,c.title,s.name AS domain FROM curriculum_chapter c JOIN curriculum_module m ON m.id=c.module_id JOIN curriculum_subject s ON s.id=m.subject_id WHERE c.published=TRUE AND m.published=TRUE AND s.published=TRUE ORDER BY s.position,m.position,c.position`,
        ]);
        const token = csrfForPage(request, session).token;
        const body = section("Administration", '<div class="feature-grid">' + card("Comptes", counts[0].users, "PLATEFORME") + card("Questions actives", counts[0].questions, "BANQUE") + card("Tentatives", counts[0].attempts, "ACTIVITÉ") + card("Leçons publiées", counts[0].lessons, "ACADÉMIE") + '</div><h3>Comptes récents</h3><div class="table-wrap"><table><thead><tr><th>Utilisateur</th><th>Email</th><th>Rôle et gestion</th></tr></thead><tbody>' + recent.map((u: Row) => '<tr><td>' + e(u.username) + '</td><td>' + e(u.email) + '</td><td>' + e(u.role) + (Number(u.id) === user.id ? ' · Ton compte' : postForm("/admin", token, hidden("action", "set_role") + hidden("user_id", String(u.id)) + '<select class="field" name="role"><option value="student"' + (u.role === "student" ? " selected" : "") + '>Étudiant</option><option value="admin"' + (u.role === "admin" ? " selected" : "") + '>Admin</option></select>' + btn("Changer le rôle"))) + '</td></tr>').join("") + '</tbody></table></div><h3>Questions récentes</h3><div class="feature-grid">' + questions.map((q: Row) => '<article class="feature"><div class="eyebrow">' + e(q.domain) + ' · ' + e(q.level) + '</div><h3>' + e(q.prompt_fr) + '</h3><p>' + e(q.topic) + ' · ' + (q.active ? "Active" : "Inactive") + '</p>' + postForm("/admin", token, hidden("action", "toggle_question") + hidden("question_id", String(q.id)) + btn(q.active ? "Désactiver" : "Activer")) + '</article>').join("") + '</div><h3>Créer une question (brouillon)</h3>' +
          postForm("/admin", token, hidden("action", "create_question") + '<label>Matière</label><select class="field" name="domain">' + subjects.map((s: Row) => '<option value="' + e(s.name) + '">' + e(s.name) + '</option>').join("") + '</select><label>Chapitre</label><select class="field" name="chapter_id">' + chapters.map((ch: Row) => '<option value="' + ch.id + '">' + e(ch.domain + " · " + ch.title) + '</option>').join("") + '</select>' + field("Sujet", "topic", "text", "", true) + field("Niveau", "level", "text", "Moyen", true) + '<label>Énoncé</label><textarea class="field" name="prompt_fr" required rows="3"></textarea>' + [0,1,2,3].map(i => field("Choix " + (i+1), "option_" + i, "text", "", true)).join("") + field("Index de la bonne réponse (0–3)", "answer", "number", "0", true) + '<label>Correction</label><textarea class="field" name="explanation_fr" required rows="3"></textarea>' + field("Objectif pédagogique", "learning_objective", "text", "", true) + field("Durée (secondes, facultative)", "time_limit_seconds", "number") + btn("Créer en brouillon")) + '</section>');
        return pageResponse(request, user, session, "Administration", body);
      }

      if (path === "/admin/curriculum" && method === "GET") {
        const [subjects, modules, chapters, lessons, exercises] = await Promise.all([
          sql`SELECT id,name,slug,published FROM curriculum_subject ORDER BY position,name`,
          sql`SELECT m.id,m.title,m.published,s.name AS subject_name FROM curriculum_module m JOIN curriculum_subject s ON s.id=m.subject_id ORDER BY s.position,m.position`,
          sql`SELECT c.id,c.title,c.published,m.title AS module_title FROM curriculum_chapter c JOIN curriculum_module m ON m.id=c.module_id ORDER BY m.position,c.position`,
          sql`SELECT l.id,l.title,l.published,c.title AS chapter_title FROM curriculum_lesson l JOIN curriculum_chapter c ON c.id=l.chapter_id ORDER BY l.id DESC LIMIT 100`,
          sql`SELECT x.id,x.title,x.published,x.exercise_type,l.title AS lesson_title FROM course_exercise x JOIN curriculum_lesson l ON l.id=x.lesson_id ORDER BY x.id DESC LIMIT 100`,
        ]);
        const token = csrfForPage(request, session).token;
        const toggle = (action: string, id: number, published: boolean, label: string) =>
          postForm("/admin/curriculum", token, hidden("action", action) + hidden("id", String(id)) + btn((published ? "Dépublier " : "Publier ") + label));
        const body = section("Académie et programme", '<div class="feature-grid">' +
          subjects.map((s: Row) => '<article class="feature"><div class="eyebrow">' + e(s.slug) + '</div><h3>' + e(s.name) + '</h3><p>' + (s.published ? "Publiée" : "Brouillon") + '</p>' + toggle("toggle_subject", Number(s.id), Boolean(s.published), "la matière") + '</article>').join("") +
          modules.map((m: Row) => '<article class="feature"><div class="eyebrow">' + e(m.subject_name) + '</div><h3>' + e(m.title) + '</h3><p>' + (m.published ? "Publié" : "Brouillon") + '</p>' + toggle("toggle_module", Number(m.id), Boolean(m.published), "le module") + '</article>').join("") +
          chapters.map((ch: Row) => '<article class="feature"><div class="eyebrow">' + e(ch.module_title) + '</div><h3>' + e(ch.title) + '</h3><p>' + (ch.published ? "Publié" : "Brouillon") + '</p>' + toggle("toggle_chapter", Number(ch.id), Boolean(ch.published), "le chapitre") + '</article>').join("") +
          lessons.map((l: Row) => '<article class="feature"><div class="eyebrow">' + e(l.chapter_title) + '</div><h3>' + e(l.title) + '</h3><p>' + (l.published ? "Publiée" : "Brouillon") + '</p>' + toggle("toggle_lesson", Number(l.id), Boolean(l.published), "la leçon") + '</article>').join("") +
          exercises.map((x: Row) => '<article class="feature"><div class="eyebrow">' + e(x.lesson_title) + ' · ' + e(x.exercise_type) + '</div><h3>' + e(x.title) + '</h3><p>' + (x.published ? "Publié" : "Brouillon") + '</p>' + toggle("toggle_exercise", Number(x.id), Boolean(x.published), "l’exercice") + '</article>').join("") +
          '</div><h3>Créer un module</h3>' + postForm("/admin/curriculum", token, hidden("action", "create_module") + '<label>Matière</label><select name="subject_id" class="field">' + subjects.map((s: Row) => '<option value="' + s.id + '">' + e(s.name) + '</option>').join("") + '</select>' + field("Titre du module", "title", "text", "", true) + field("Position", "position", "number", "0") + btn("Créer le module")) +
          '<h3>Créer un chapitre</h3>' + postForm("/admin/curriculum", token, hidden("action", "create_chapter") + '<label>Module</label><select name="module_id" class="field">' + modules.map((m: Row) => '<option value="' + m.id + '">' + e(m.subject_name + " · " + m.title) + '</option>').join("") + '</select>' + field("Titre", "title", "text", "", true) + field("Position", "position", "number", "0") + btn("Créer le chapitre")) +
          '<h3>Créer une leçon (brouillon)</h3>' + postForm("/admin/curriculum", token, hidden("action", "create_lesson") + '<label>Chapitre</label><select name="chapter_id" class="field">' + chapters.map((ch: Row) => '<option value="' + ch.id + '">' + e(ch.module_title + " · " + ch.title) + '</option>').join("") + '</select>' + field("Titre", "title", "text", "", true) + '<label>Objectifs (un par ligne)</label><textarea name="objectives_fr" class="field" rows="3"></textarea>' + '<label>Prérequis</label><textarea name="prerequisites_fr" class="field" rows="2"></textarea>' + '<label>Cours en français</label><textarea name="theory_fr" class="field" rows="6" required></textarea><label>Cours en Darija</label><textarea name="theory_ar" class="field" rows="6" required></textarea>' + field("Exemple", "example_fr", "text") + '<label>Code exemple</label><textarea name="code_example" class="field" rows="3"></textarea>' + '<label>Exercice</label><textarea name="exercise_fr" class="field" rows="2"></textarea><label>Solution</label><textarea name="solution_fr" class="field" rows="2"></textarea><label>Résumé</label><textarea name="summary_fr" class="field" rows="2"></textarea><label>Révision</label><textarea name="revision_fr" class="field" rows="2"></textarea>' + btn("Créer en brouillon")) +
          '</section>';
        return pageResponse(request, user, session, "Académie et programme", body);
      }

      if (path === "/admin/curriculum" && method === "POST") {
        const action = val(form, "action");
        const id = Number(form.get("id"));
        if (action === "toggle_subject") await sql`UPDATE curriculum_subject SET published=NOT published WHERE id=${id}`;
        else if (action === "toggle_module") await sql`UPDATE curriculum_module SET published=NOT published WHERE id=${id}`;
        else if (action === "toggle_chapter") await sql`UPDATE curriculum_chapter SET published=NOT published WHERE id=${id}`;
        else if (action === "toggle_lesson") await sql`UPDATE curriculum_lesson SET published=NOT published WHERE id=${id}`;
        else if (action === "toggle_exercise") await sql`UPDATE course_exercise SET published=NOT published WHERE id=${id}`;
        else if (action === "create_module") {
          const subjectId = Number(form.get("subject_id")), title = val(form, "title"), position = Math.max(0, Math.min(10000, Number(form.get("position") ?? 0)));
          if (!subjectId || !title || !Number.isInteger(position)) return toNotice("/admin/curriculum", "Informations du module invalides.", "error");
          await sql`INSERT INTO curriculum_module (subject_id,title,position,published) VALUES (${subjectId},${title.slice(0,160)},${position},FALSE)`;
        } else if (action === "create_chapter") {
          const moduleId = Number(form.get("module_id")), title = val(form, "title"), position = Math.max(0, Math.min(10000, Number(form.get("position") ?? 0)));
          if (!moduleId || !title || !Number.isInteger(position)) return toNotice("/admin/curriculum", "Informations du chapitre invalides.", "error");
          await sql`INSERT INTO curriculum_chapter (module_id,title,position,published) VALUES (${moduleId},${title.slice(0,160)},${position},FALSE)`;
        } else if (action === "create_lesson") {
          const chapterId = Number(form.get("chapter_id")), title = val(form, "title"), theory = val(form, "theory_fr"), darija = val(form, "theory_ar");
          if (!chapterId || !title || !theory || !darija) return toNotice("/admin/curriculum", "La leçon doit avoir un titre et un cours en français et Darija.", "error");
          const objectives = val(form, "objectives_fr").split("\n").map((x) => x.trim()).filter(Boolean);
          await sql`INSERT INTO curriculum_lesson (chapter_id,title,objectives_fr,prerequisites_fr,theory_fr,theory_ar,example_fr,code_example,exercise_fr,solution_fr,summary_fr,revision_fr,published) VALUES (${chapterId},${title.slice(0,200)},${JSON.stringify(objectives)},${val(form, "prerequisites_fr")},${theory.slice(0,12000)},${darija.slice(0,12000)},${val(form, "example_fr")},${val(form, "code_example")},${val(form, "exercise_fr")},${val(form, "solution_fr")},${val(form, "summary_fr")},${val(form, "revision_fr")},FALSE)`;
        } else {
          return response("<h1>400 · Action invalide</h1>", 400);
        }
        return redirect("/admin/curriculum");
      }

      if (path === "/admin/exercise-attempts" && (method === "GET" || method === "POST")) {
        if (method === "POST") {
          const id = Number(form.get("attempt_id")), score = Number(form.get("score")), feedback = val(form, "feedback");
          if (!Number.isInteger(id) || !Number.isFinite(score) || score < 0 || score > 100) return toNotice("/admin/exercise-attempts", "Note invalide.", "error");
          await sql`UPDATE exercise_attempt SET score=${score},feedback=${feedback},status='evaluated',evaluated_by=${user.id},evaluated_at=NOW() WHERE id=${id} AND status='pending_manual'`;
          return redirect("/admin/exercise-attempts");
        }
        const attempts = await sql`SELECT ea.id,ea.submitted_answer,ea.created_at,ea.status,x.title,x.prompt_fr,u.username FROM exercise_attempt ea JOIN course_exercise x ON x.id=ea.exercise_id JOIN "user" u ON u.id=ea.user_id WHERE ea.status='pending_manual' ORDER BY ea.created_at ASC LIMIT 100`;
        const token = csrfForPage(request, session).token;
        const body = section("Réponses à corriger", '<div class="feature-grid">' + attempts.map((a: Row) => '<article class="feature"><div class="eyebrow">' + e(a.username) + ' · ' + e(formatDate(a.created_at)) + '</div><h3>' + e(a.title) + '</h3><p>' + e(a.prompt_fr) + '</p><blockquote>' + e(a.submitted_answer) + '</blockquote>' + postForm("/admin/exercise-attempts", token, hidden("attempt_id", String(a.id)) + field("Note (%)", "score", "number", "0", true) + field("Feedback", "feedback", "text") + btn("Valider la correction")) + '</article>').join("") + '</div>', attempts.length ? "Réponses ouvertes en attente d’évaluation." : "Aucune réponse en attente.");
        return pageResponse(request, user, session, "Réponses à corriger", body);
      }

      if (path === "/admin/quality" && method === "GET") {
        const [subjects, videos, pending] = await Promise.all([
          sql`SELECT COUNT(*) AS total FROM curriculum_lesson WHERE published=TRUE`,
          sql`SELECT COUNT(*) AS total FROM video_resource WHERE active=TRUE AND verified=TRUE AND verification_status='verified'`,
          sql`SELECT COUNT(*) AS total FROM exercise_attempt WHERE status='pending'`,
        ]);
        const body = section("Qualité pédagogique", '<div class="feature-grid">' + card("Leçons publiées", subjects[0].total, "CURRICULUM") + card("Vidéos vérifiées", videos[0].total, "RESSOURCES") + card("Réponses en attente", pending[0].total, "CORRECTION") + '</div>', "Indicateurs calculés à partir de la base actuelle.");
        return pageResponse(request, user, session, "Qualité pédagogique", body);
      }

      if (path === "/admin/videos" && method === "GET") {
        const rows = await sql`SELECT id,title,channel,video_id,language,lesson_key,verified,verification_status,active FROM video_resource ORDER BY created_at DESC LIMIT 100`;
        const token = csrfForPage(request, session).token;
        const body = section("Gestion des vidéos", '<div class="feature-grid">' + rows.map((v: Row) => '<article class="feature"><h3>' + e(v.title) + '</h3><p>' + e(v.channel) + ' · ' + e(v.lesson_key) + '</p><p>' + e(v.verification_status) + ' · ' + (v.active ? "Active" : "Inactive") + '</p>' +
          postForm("/admin/videos", token, hidden("video_id", String(v.id)) + hidden("action", v.verification_status === "verified" ? "pending" : "verify") + btn(v.verification_status === "verified" ? "Retirer la vérification" : "Vérifier")) +
          postForm("/admin/videos", token, hidden("video_id", String(v.id)) + hidden("action", v.active ? "toggle" : "toggle") + btn(v.active ? "Désactiver" : "Activer")) +
          postForm("/admin/videos", token, hidden("video_id", String(v.id)) + hidden("action", "reject") + btn("Rejeter")) +
          '</article>').join("") + '</div><h3>Ajouter une ressource</h3>' +
          postForm("/admin/videos", token, field("Titre", "title", "text", "", true) + field("Chaîne", "channel", "text", "", true) + field("URL YouTube", "url", "url", "", true) + field("Matière / clé de leçon", "lesson_key", "text", "", true) + field("Langue", "language", "text", "Français", true) + btn("Ajouter en attente")) + '</section>');
        return pageResponse(request, user, session, "Gestion des vidéos", body);
      }

      if (path === "/admin/videos" && method === "POST") {
        const action = val(form, "action") || "create";
        const videoId = Number(form.get("video_id"));
        if (["verify", "reject", "unavailable", "pending"].includes(action)) {
          const status = action === "verify" ? "verified" : action === "reject" ? "rejected" : action === "unavailable" ? "unavailable" : "pending";
          await sql`UPDATE video_resource SET verification_status=${status},verified=${action === "verify"},verified_at=CASE WHEN ${action === "verify"} THEN NOW() ELSE NULL END WHERE id=${videoId}`;
          return redirect("/admin/videos");
        }
        if (action === "toggle") {
          await sql`UPDATE video_resource SET active=NOT active WHERE id=${videoId}`;
          return redirect("/admin/videos");
        }
        if (action === "delete") {
          const watches = await sql`SELECT id FROM video_watch WHERE video_id=${videoId} LIMIT 1`;
          if (watches.length) return toNotice("/admin/videos", "Cette vidéo a déjà des suivis; désactive-la pour conserver l’historique.", "error");
          await sql`DELETE FROM video_metadata WHERE video_id=${videoId}`;
          await sql`DELETE FROM video_resource WHERE id=${videoId}`;
          return redirect("/admin/videos");
        }
        if (action !== "create") return response("<h1>400 · Action invalide</h1>", 400);
        const title = val(form, "title"), channel = val(form, "channel"), raw = val(form, "url"), lessonKey = val(form, "lesson_key"), language = val(form, "language") || "Français";
        const match = raw.match(/(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|embed\/|shorts\/))([A-Za-z0-9_-]{11})/);
        if (!title || !channel || !match || !lessonKey) return toNotice("/admin/videos", "Vérifie le titre, la chaîne, l’URL YouTube et la clé de leçon.", "error");
        await sql`INSERT INTO video_resource (title,channel,video_id,language,lesson_key,verified,verification_status,active,created_by) VALUES (${title.slice(0,200)},${channel.slice(0,160)},${match[1]},${language.slice(0,20)},${lessonKey.slice(0,100)},FALSE,'pending',TRUE,${user.id}) ON CONFLICT (video_id) DO NOTHING`;
        return toNotice("/admin/videos", "Ressource ajoutée en attente de vérification.");
      }
      return response("<h1>404 · Administration</h1>", 404);
    }

    return response("<h1>404 · Page introuvable</h1><p><a href='/dashboard'>Retour au tableau de bord</a></p>", 404);
  } catch (error) {
    // Log only a compact message; never expose DB credentials or SQL details to visitors.
    console.error("InfoConcours function error:", error instanceof Error ? error.message : "unknown");
    return response("<h1>Service temporairement indisponible</h1><p>Réessaie dans quelques instants.</p>", 503);
  }
}

export const config: Config = { path: "/*", preferStatic: true };
