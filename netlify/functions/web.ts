import type { Config } from "@netlify/functions";
import { database } from "./_shared/database.js";
import { createSession, cookieHeader, expiredCookieHeader } from "./_shared/session.js";
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
  const rows = await sql`SELECT ${sql(questionSelect)} FROM question WHERE active = TRUE AND id = ANY(${ids}::int[])`;
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
      const username = val(form, "username"), email = val(form, "email").toLowerCase();
      const password = String(form.get("password") ?? ""), confirm = String(form.get("confirm") ?? "");
      if (username.length < 3 || username.length > 40 || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email) || password.length < 8 || password !== confirm) {
        return toNotice("/register", "Vérifie les champs : nom (3 caractères), email valide et mot de passe de 8 caractères minimum.", "error");
      }
      const found = await sql`SELECT id FROM "user" WHERE username = ${username} OR email = ${email} LIMIT 1`;
      if (found.length) return toNotice("/register", "Nom d’utilisateur ou email déjà utilisé.", "error");
      const rows = await sql`INSERT INTO "user" (username,email,password_hash,role) VALUES (${username},${email},${hashPassword(password)},"student") RETURNING id,username,email,role`;
      const created = rows[0] as Row;
      const token = createSession({ userId: Number(created.id), role: "student", language: "fr" });
      await sql`INSERT INTO user_preference (user_id,language) VALUES (${Number(created.id)},"fr") ON CONFLICT (user_id) DO NOTHING`;
      return redirect("/dashboard", { "set-cookie": cookieHeader(token, cookieSecure()) });
    }

    if (path === "/login" && method === "POST") {
      if (user) return redirect("/dashboard");
      const username = val(form, "username"), password = String(form.get("password") ?? "");
      const rows = await sql`SELECT id,username,email,password_hash,role FROM "user" WHERE username = ${username} LIMIT 1`;
      const found = rows[0] as Row | undefined;
      if (!found || !verifyPassword(password, String(found.password_hash))) return toNotice("/login", "Identifiants incorrects.", "error");
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
          const rows = await sql`SELECT ${sql(questionSelect)} FROM question WHERE active=TRUE AND domain=${String(d.name)} ORDER BY random() LIMIT 3`;
          selected.push(...rows as Row[]);
        }
        const token = csrfForPage(request, session).token;
        const body = '<section class="section"><div class="section-head"><div class="eyebrow">DIAGNOSTIC INITIAL</div><h2>Évalue ton niveau.</h2><p>Trois questions par domaine. Les résultats seront enregistrés dans ton compte.</p></div>' +
          postForm("/diagnostic", token, hidden("question_ids", selected.map(q => q.id).join(",")) + selected.map(q => questionBlock(q, token)).join("") + btn("Terminer le diagnostic")) + '</section>';
        return pageResponse(request, user, session, "Diagnostic", body);
      }
      const ids = val(form, "question_ids").split(",").map(Number).filter((n) => Number.isInteger(n) && n > 0);
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
        const meta = await sql`SELECT q.${sql(questionSelect)} FROM question q JOIN question_metadata qm ON qm.question_id=q.id WHERE qm.chapter_id=${Number(lesson.chapter_id)} AND q.active=TRUE ORDER BY q.id`;
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
      const videos = await sql`SELECT v.id,v.title,v.channel,v.video_id,v.language,v.duration_minutes,vm.description FROM video_metadata vm JOIN video_resource v ON v.id=vm.video_id WHERE (vm.lesson_id=${lessonId} OR (vm.lesson_id IS NULL AND vm.chapter_id=${Number(lesson.chapter_id)})) AND v.active=TRUE AND v.verified=TRUE AND v.verification_status='verified' ORDER BY v.title`;
      const qs = await sql`SELECT q.${sql(questionSelect)},qm.learning_objective FROM question q JOIN question_metadata qm ON qm.question_id=q.id WHERE qm.chapter_id=${Number(lesson.chapter_id)} AND q.active=TRUE ORDER BY q.id`;
      const csrf = csrfForPage(request, session).token;
      const body = '<section class="section"><div class="eyebrow">' + e(lesson.subject_name) + ' · ' + e(lesson.module_title) + '</div><h2>' + e(lesson.title) + '</h2><p>' + e(lesson.chapter_title) + '</p><div class="lesson-content">' +
        '<h3>Objectifs</h3><p>' + e(parseJson(lesson.objectives_fr, []).join(" · ")) + '</p><h3>Prérequis</h3><p>' + e(lesson.prerequisites_fr) + '</p><h3>Cours</h3><div>' + String(lesson.theory_fr ?? "").replace(/\n/g, "<br>") + '</div><h3>Exemple</h3><p>' + e(lesson.example_fr) + '</p><pre><code>' + e(lesson.code_example) + '</code></pre><h3>À retenir</h3><p>' + e(lesson.summary_fr) + '</p><h3>Révision</h3><p>' + e(lesson.revision_fr) + '</p></div>' +
        (videos.length ? '<h3>Vidéos vérifiées</h3><div class="feature-grid">' + videos.map((v: Row) => '<article class="feature"><h3>' + e(v.title) + '</h3><p>' + e(v.channel) + '</p><iframe title="' + e(v.title) + '" src="https://www.youtube-nocookie.com/embed/' + e(v.video_id) + '" loading="lazy" allowfullscreen></iframe></article>').join("") + '</div>' : '<p class="muted">Aucune vidéo vérifiée pour cette leçon.</p>') +
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
      const exerciseId = Number(exerciseMatch[1]), answer = val(form, "answer");
      const rows = await sql`SELECT id,exercise_type,correct_answer,accepted_answers_json,feedback_fr,solution_fr FROM course_exercise WHERE id=${exerciseId} AND published=TRUE LIMIT 1`;
      if (!rows.length) return response("<h1>404 · Exercice introuvable</h1>", 404);
      const x = rows[0] as Row;
      const kind = String(x.exercise_type);
      let score: number | null = null, status = "pending", feedback = "Ta réponse a été envoyée pour correction.";
      if (kind === "qcm" || kind === "true_false" || kind === "short") {
        const accepted = [String(x.correct_answer ?? ""), ...parseJson(x.accepted_answers_json, [])].map((v: any) => String(v).trim().toLowerCase()).filter(Boolean);
        const ok = accepted.includes(answer.toLowerCase());
        score = ok ? 100 : 0; status = "evaluated"; feedback = ok ? String(x.feedback_fr || "Bonne réponse.") : String(x.solution_fr || "Réponse incorrecte.");
      }
      await sql`INSERT INTO exercise_attempt (user_id,exercise_id,submitted_answer,score,feedback,status) VALUES (${user.id},${exerciseId},${answer},${score},${feedback},${status})`;
      return toNotice("/courses/continue", status === "pending" ? "Réponse envoyée à l’enseignant pour correction." : feedback);
    }

    if (path === "/qcm" && (method === "GET" || method === "POST")) {
      if (method === "GET") {
        const domain = url.searchParams.get("domain") ?? "", level = url.searchParams.get("level") ?? "";
        const qs = await sql`SELECT ${sql(questionSelect)} FROM question WHERE active=TRUE AND (${domain}='' OR domain=${domain}) AND (${level}='' OR level=${level}) ORDER BY random() LIMIT 15`;
        const token = csrfForPage(request, session).token;
        const body = '<section class="section"><div class="section-head"><div class="eyebrow">ENTRAÎNEMENT</div><h2>Teste tes connaissances.</h2><p>Une série de 15 questions corrigées après soumission.</p></div>' +
          '<form method="get" action="/qcm">' + field("Matière (optionnel)", "domain") + field("Niveau (optionnel)", "level") + '<button class="btn ghost">Filtrer</button></form>' +
          postForm("/qcm", token, hidden("question_ids", qs.map((q: Row) => q.id).join(",")) + qs.map((q: Row) => questionBlock(q, token)).join("") + btn("Corriger mes réponses")) +
          '</section>';
        return pageResponse(request, user, session, "Entraînement QCM", body);
      }
      const ids = val(form, "question_ids").split(",").map(Number).filter((n) => Number.isInteger(n) && n > 0);
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
        const qs = await sql`SELECT ${sql(questionSelect)} FROM question WHERE active=TRUE ORDER BY random() LIMIT 30`;
        const token = csrfForPage(request, session).token, started = Date.now();
        const runId = createSession({ userId: user.id, role: user.role, language: session?.language ?? "fr" });
        const body = '<section class="section"><div class="section-head"><div class="eyebrow">EXAMEN BLANC</div><h2>Simulation de concours.</h2><p>30 questions · ' + Math.max(5, Math.min(240, Number(process.env.EXAM_DURATION_MINUTES ?? 240))) + ' minutes.</p></div>' +
          postForm("/exam", token, hidden("question_ids", qs.map((q: Row) => q.id).join(",")) + hidden("started_at", String(started)) + hidden("run_id", runId) + qs.map((q: Row) => questionBlock(q, token)).join("") + btn("Terminer l’examen")) + '</section>';
        return pageResponse(request, user, session, "Examen blanc", body);
      }
      const start = Number(form.get("started_at"));
      if (!Number.isFinite(start) || Date.now() - start > 6 * 60 * 60 * 1000 || !val(form, "run_id")) return toNotice("/exam", "Cette session d’examen a expiré. Lance un nouvel examen.", "error");
      const ids = val(form, "question_ids").split(",").map(Number).filter((n) => Number.isInteger(n) && n > 0);
      const qs = await getQuestions(sql, ids);
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
      if (path === "/admin" && method === "GET") {
        const [counts, recent, questions] = await Promise.all([
          sql`SELECT (SELECT COUNT(*) FROM "user") AS users,(SELECT COUNT(*) FROM question WHERE active=TRUE) AS questions,(SELECT COUNT(*) FROM attempt) AS attempts,(SELECT COUNT(*) FROM curriculum_lesson WHERE published=TRUE) AS lessons`,
          sql`SELECT username,email,role,created_at FROM "user" ORDER BY created_at DESC LIMIT 20`,
          sql`SELECT id,domain,topic,level,prompt_fr,active FROM question ORDER BY id DESC LIMIT 20`,
        ]);
        const body = section("Administration", '<div class="feature-grid">' + card("Comptes", counts[0].users, "PLATEFORME") + card("Questions actives", counts[0].questions, "BANQUE") + card("Tentatives", counts[0].attempts, "ACTIVITÉ") + card("Leçons publiées", counts[0].lessons, "ACADÉMIE") + '</div><h3>Comptes récents</h3><div class="table-wrap"><table><thead><tr><th>Utilisateur</th><th>Email</th><th>Rôle</th></tr></thead><tbody>' + recent.map((u: Row) => '<tr><td>' + e(u.username) + '</td><td>' + e(u.email) + '</td><td>' + e(u.role) + '</td></tr>').join("") + '</tbody></table></div><h3>Questions récentes</h3><div class="table-wrap"><table><thead><tr><th>Matière</th><th>Sujet</th><th>Niveau</th><th>Statut</th></tr></thead><tbody>' + questions.map((q: Row) => '<tr><td>' + e(q.domain) + '</td><td>' + e(q.topic) + '</td><td>' + e(q.level) + '</td><td>' + (q.active ? "Active" : "Inactive") + '</td></tr>').join("") + '</tbody></table></div>');
        return pageResponse(request, user, session, "Administration", body);
      }

      if (path === "/admin/curriculum" && method === "GET") {
        const subjects = await sql`SELECT s.id,s.name,s.slug,s.published,COUNT(l.id) AS lessons FROM curriculum_subject s LEFT JOIN curriculum_module m ON m.subject_id=s.id LEFT JOIN curriculum_chapter c ON c.module_id=m.id LEFT JOIN curriculum_lesson l ON l.chapter_id=c.id GROUP BY s.id ORDER BY s.position,s.name`;
        const body = section("Académie et programme", '<div class="feature-grid">' + subjects.map((s: Row) => card(s.name, e(s.lessons) + " leçons · " + (s.published ? "publiée" : "masquée"), s.slug)).join("") + '</div>', "Consultation du curriculum. Les modifications détaillées restent disponibles dans la version Flask pendant la migration.");
        return pageResponse(request, user, session, "Académie et programme", body);
      }

      if (path === "/admin/exercise-attempts" && (method === "GET" || method === "POST")) {
        if (method === "POST") {
          const id = Number(form.get("attempt_id")), score = Number(form.get("score")), feedback = val(form, "feedback");
          if (!Number.isInteger(id) || !Number.isFinite(score) || score < 0 || score > 100) return toNotice("/admin/exercise-attempts", "Note invalide.", "error");
          await sql`UPDATE exercise_attempt SET score=${score},feedback=${feedback},status='evaluated',evaluated_by=${user.id},evaluated_at=NOW() WHERE id=${id} AND status='pending'`;
          return redirect("/admin/exercise-attempts");
        }
        const attempts = await sql`SELECT ea.id,ea.submitted_answer,ea.created_at,ea.status,x.title,x.prompt_fr,u.username FROM exercise_attempt ea JOIN course_exercise x ON x.id=ea.exercise_id JOIN "user" u ON u.id=ea.user_id WHERE ea.status='pending' ORDER BY ea.created_at ASC LIMIT 100`;
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
        const body = section("Gestion des vidéos", '<div class="feature-grid">' + rows.map((v: Row) => '<article class="feature"><h3>' + e(v.title) + '</h3><p>' + e(v.channel) + ' · ' + e(v.lesson_key) + '</p><p>' + e(v.verification_status) + ' · ' + (v.active ? "Active" : "Inactive") + '</p></article>').join("") + '</div><h3>Ajouter une ressource</h3>' +
          postForm("/admin/videos", token, field("Titre", "title", "text", "", true) + field("Chaîne", "channel", "text", "", true) + field("URL YouTube", "url", "url", "", true) + field("Matière / clé de leçon", "lesson_key", "text", "", true) + field("Langue", "language", "text", "Français", true) + btn("Ajouter en attente")) + '</section>');
        return pageResponse(request, user, session, "Gestion des vidéos", body);
      }

      if (path === "/admin/videos" && method === "POST") {
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

export const config: Config = { path: "/*" };
