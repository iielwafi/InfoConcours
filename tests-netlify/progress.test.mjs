import test from "node:test";
import assert from "node:assert/strict";
import {
  calculateXpSnapshot,
  buildPerformanceTimeline,
  summarizeDiagnosticDomains
} from "../netlify/functions/_shared/progress.ts";

test("new-student diagnostic awards participation XP and a correct-answer bonus", () => {
  const xp = calculateXpSnapshot(
    [{ scores: { Algorithmique: { correct: 2, count: 3, available: 3, percent: 67, weight: 20 } }, created_at: "2026-11-13T08:00:00Z" }],
    [],
    0,
    0
  );
  assert.equal(xp.diagnosticXp, 21);
  assert.equal(xp.totalXp, 21);
  assert.equal(xp.level, 1);
  assert.equal(xp.xpForNextLevel, 229);
});

test("practice XP is awarded only once per answered question and ignores diagnostic repeats", () => {
  const xp = calculateXpSnapshot(
    [{ scores: { Networks: { correct: 1, count: 2 } }, created_at: "2026-11-12T10:00:00Z" }],
    [
      { mode: "diagnostic", details: [{ question_id: 10, selected: 1 }, { question_id: 11, selected: 0 }], created_at: "2026-11-12T10:00:00Z" },
      { mode: "qcm", details: [{ question_id: 10, selected: 0, ok: true }, { question_id: 12, selected: 2, ok: false }], created_at: "2026-11-13T08:00:00Z" },
      { mode: "qcm", details: [{ question_id: 12, selected: 1, ok: true }, { question_id: 13, selected: 0, ok: true }], created_at: "2026-11-13T09:00:00Z" }
    ],
    30,
    2
  );
  assert.equal(xp.diagnosticXp, 13);
  assert.equal(xp.practiceXp, 7);
  assert.equal(xp.studyXp, 6);
  assert.equal(xp.lessonXp, 30);
  assert.equal(xp.totalXp, 56);
  assert.equal(xp.answeredQuestions, 4);
  assert.equal(xp.correctAnswers, 2);
});

test("diagnostic domains are classified without treating unanswered subjects as weak", () => {
  const rows = summarizeDiagnosticDomains({
    Algorithmique: { correct: 3, count: 3 },
    Réseaux: { correct: 1, count: 3 },
    Bases: { correct: 0, count: 0 }
  });
  assert.equal(rows.find(x => x.domain === "Algorithmique")?.category, "strength");
  assert.equal(rows.find(x => x.domain === "Réseaux")?.category, "priority");
  assert.equal(rows.find(x => x.domain === "Bases")?.category, "unassessed");
});

test("performance timeline combines diagnostic baseline and later QCM progress", () => {
  const rows = buildPerformanceTimeline(
    [
      { mode: "diagnostic", score: 12, total: 24, created_at: "2026-11-10T08:00:00Z" },
      { mode: "qcm", score: 8, total: 10, created_at: "2026-11-12T08:00:00Z" }
    ],
    [{ scores: { A: { correct: 12, count: 24 } }, created_at: "2026-11-10T08:00:00Z" }],
    14
  );
  assert.equal(rows.length, 2);
  assert.equal(rows[0].average, 50);
  assert.equal(rows[1].average, 80);
});
