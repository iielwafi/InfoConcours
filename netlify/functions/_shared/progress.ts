export type DiagnosticProgressRecord = {
  scores?: string | Record<string, unknown> | null;
  created_at?: string | Date | null;
};

export type ProgressAttemptRecord = {
  mode?: string | null;
  score?: number | string | null;
  total?: number | string | null;
  created_at?: string | Date | null;
  details?: string | unknown[] | null;
};

export type XpSnapshot = {
  totalXp: number;
  level: number;
  levelProgress: number;
  xpForNextLevel: number;
  diagnosticXp: number;
  practiceXp: number;
  studyXp: number;
  lessonXp: number;
  answeredQuestions: number;
  correctAnswers: number;
};

export type TimelinePoint = {
  day: string;
  label: string;
  average: number;
  assessments: number;
};

function parseJson(value: unknown): unknown {
  if (typeof value !== "string") return value;
  try { return JSON.parse(value); } catch { return null; }
}

function dateKey(value: unknown): string {
  if (!value) return "";
  const raw = value instanceof Date ? value.toISOString() : String(value);
  const match = raw.match(/^(\d{4}-\d{2}-\d{2})/);
  if (match) return match[1];
  const parsed = new Date(raw);
  return Number.isNaN(parsed.getTime()) ? "" : parsed.toISOString().slice(0, 10);
}

function diagnosticTotals(value: unknown): { answered: number; correct: number } {
  const parsed = parseJson(value);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return { answered: 0, correct: 0 };
  let answered = 0;
  let correct = 0;
  for (const raw of Object.values(parsed as Record<string, unknown>)) {
    if (!raw || typeof raw !== "object") continue;
    const entry = raw as Record<string, unknown>;
    const count = Number(entry.count);
    const right = Number(entry.correct);
    if (!Number.isFinite(count) || !Number.isFinite(right)) continue;
    answered += Math.max(0, Math.floor(count));
    correct += Math.max(0, Math.min(Math.floor(count), Math.floor(right)));
  }
  return { answered, correct };
}

function parseDetails(value: unknown): Record<string, unknown>[] {
  const parsed = parseJson(value);
  if (!Array.isArray(parsed)) return [];
  return parsed.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object" && !Array.isArray(item));
}

/**
 * XP is derived from completed learning activity, not stored as an editable
 * balance. This prevents client-side point manipulation and avoids a schema
 * change to the production database.
 *
 * Initial diagnostic: 5 XP per answered question + 3 XP per correct answer.
 * Practice/exam: 2 XP for the first answered occurrence of a question and
 * 3 extra XP when correct. Questions already answered in the diagnostic and
 * repeated questions do not farm extra XP.
 * Study time: 1 XP per 5 recorded focus minutes. Lessons: 15 XP each.
 */
export function calculateXpSnapshot(
  diagnostics: readonly DiagnosticProgressRecord[],
  attempts: readonly ProgressAttemptRecord[],
  totalStudyMinutes: number,
  completedLessons: number,
): XpSnapshot {
  const orderedDiagnostics = [...diagnostics].sort((a, b) =>
    dateKey(a.created_at).localeCompare(dateKey(b.created_at))
  );
  const baseline = orderedDiagnostics.length ? diagnosticTotals(orderedDiagnostics[0].scores) : { answered: 0, correct: 0 };
  const diagnosticXp = baseline.answered * 5 + baseline.correct * 3;

  const orderedAttempts = [...attempts].sort((a, b) =>
    String(a.created_at ?? "").localeCompare(String(b.created_at ?? ""))
  );
  const seenQuestions = new Set<number>();
  let hasSeenInitialDiagnostic = false;
  let practiceXp = 0;
  let answeredQuestions = baseline.answered;
  let correctAnswers = baseline.correct;

  for (const attempt of orderedAttempts) {
    if (attempt.mode === "diagnostic") {
      // The diagnostic itself earns the one-time baseline XP above. Its
      // question IDs are then marked as seen so they cannot be farmed later.
      // A later diagnostic retake does not retroactively remove XP already
      // earned through practice; it only prevents future repeat rewards.
      if (!hasSeenInitialDiagnostic) hasSeenInitialDiagnostic = true;
      for (const detail of parseDetails(attempt.details)) {
        const id = Number(detail.question_id);
        if (Number.isInteger(id) && id > 0 && detail.selected !== null && detail.selected !== undefined) {
          seenQuestions.add(id);
        }
      }
      continue;
    }
    if (attempt.mode !== "qcm" && attempt.mode !== "exam") continue;
    for (const detail of parseDetails(attempt.details)) {
      const id = Number(detail.question_id);
      const selected = detail.selected;
      if (!Number.isInteger(id) || id <= 0 || selected === null || selected === undefined) continue;
      if (seenQuestions.has(id)) continue;
      seenQuestions.add(id);
      answeredQuestions += 1;
      practiceXp += 2;
      if (detail.ok === true) {
        correctAnswers += 1;
        practiceXp += 3;
      }
    }
  }

  const safeStudyMinutes = Number.isFinite(Number(totalStudyMinutes)) ? Math.max(0, Number(totalStudyMinutes)) : 0;
  const safeLessons = Number.isFinite(Number(completedLessons)) ? Math.max(0, Number(completedLessons)) : 0;
  const studyXp = Math.floor(safeStudyMinutes / 5);
  const lessonXp = Math.floor(safeLessons) * 15;
  const totalXp = diagnosticXp + practiceXp + studyXp + lessonXp;
  const levelSize = 250;

  return {
    totalXp,
    level: Math.floor(totalXp / levelSize) + 1,
    levelProgress: totalXp % levelSize,
    xpForNextLevel: levelSize - (totalXp % levelSize),
    diagnosticXp,
    practiceXp,
    studyXp,
    lessonXp,
    answeredQuestions,
    correctAnswers,
  };
}

/** Combine daily QCM/exam attempts into a real score timeline. */
export function buildPerformanceTimeline(
  attempts: readonly ProgressAttemptRecord[],
  diagnostics: readonly DiagnosticProgressRecord[],
  maxDays = 14,
): TimelinePoint[] {
  const byDay = new Map<string, { total: number; count: number }>();
  const diagnosticAttemptDays = new Set<string>();

  for (const attempt of attempts) {
    if (!["diagnostic", "qcm", "exam"].includes(String(attempt.mode))) continue;
    const day = dateKey(attempt.created_at);
    const score = Number(attempt.score);
    const total = Number(attempt.total);
    if (!day || !Number.isFinite(score) || !Number.isFinite(total) || total <= 0) continue;
    const bucket = byDay.get(day) ?? { total: 0, count: 0 };
    bucket.total += Math.max(0, Math.min(100, (score / total) * 100));
    bucket.count += 1;
    byDay.set(day, bucket);
    if (attempt.mode === "diagnostic") diagnosticAttemptDays.add(day);
  }

  for (const diagnostic of diagnostics) {
    const day = dateKey(diagnostic.created_at);
    if (!day || diagnosticAttemptDays.has(day)) continue;
    const totals = diagnosticTotals(diagnostic.scores);
    if (!totals.answered) continue;
    const bucket = byDay.get(day) ?? { total: 0, count: 0 };
    bucket.total += (totals.correct / totals.answered) * 100;
    bucket.count += 1;
    byDay.set(day, bucket);
  }

  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - Math.max(1, maxDays) + 1);
  const cutoffKey = cutoff.toISOString().slice(0, 10);

  return Array.from(byDay.entries())
    .filter(([day]) => day >= cutoffKey)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([day, bucket]) => ({
      day,
      label: day.slice(8, 10) + "/" + day.slice(5, 7),
      average: Math.round(bucket.total / bucket.count),
      assessments: bucket.count,
    }));
}

export function summarizeDiagnosticDomains(scores: unknown): Array<{
  domain: string;
  correct: number;
  answered: number;
  percent: number | null;
  category: "strength" | "priority" | "developing" | "unassessed";
}> {
  const parsed = parseJson(scores);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return [];
  return Object.entries(parsed as Record<string, unknown>).map(([domain, raw]) => {
    const entry = raw && typeof raw === "object" ? raw as Record<string, unknown> : {};
    const answered = Math.max(0, Number(entry.count) || 0);
    const correct = Math.max(0, Math.min(answered, Number(entry.correct) || 0));
    const percent = answered ? Math.round(correct * 100 / answered) : null;
    return {
      domain,
      correct,
      answered,
      percent,
      category: percent === null ? "unassessed" : percent >= 70 ? "strength" : percent < 50 ? "priority" : "developing",
    };
  });
}
