import test from "node:test";
import assert from "node:assert/strict";
import { summarizeAttemptDetails } from "../netlify/functions/_shared/planner.ts";

test("planner aggregates subject scores from question details, not an attempt.domain column", () => {
  const rows = summarizeAttemptDetails([
    {
      id: 1,
      details: JSON.stringify([
        { domain: "Algorithmique", ok: true },
        { domain: "Algorithmique", ok: false },
        { domain: "Programmation", ok: true },
      ]),
    },
    {
      id: 2,
      details: [
        { domain: "Algorithmique", ok: false },
        { domain: "Programmation", ok: true },
        { domain: "Programmation", ok: true },
      ],
    },
  ]);

  assert.deepEqual(rows, [
    { domain: "Algorithmique", average: 33, attempts: 2, responses: 3 },
    { domain: "Programmation", average: 100, attempts: 2, responses: 3 },
  ]);
});

test("planner ignores malformed, empty and incomplete question details", () => {
  const rows = summarizeAttemptDetails([
    { id: 1, details: "not-json" },
    { id: 2, details: null },
    { id: 3, details: JSON.stringify([{ domain: "", ok: true }, { domain: "Réseaux" }]) },
    { id: 4, details: [{ domain: "Réseaux", ok: false }] },
  ]);

  assert.deepEqual(rows, [
    { domain: "Réseaux", average: 0, attempts: 1, responses: 1 },
  ]);
});

test("planner returns an empty list when a learner has no QCM history", () => {
  assert.deepEqual(summarizeAttemptDetails([]), []);
});


test("Pomodoro browser controller is safe to import without a browser DOM", async () => {
  await import("../public/assets/pomodoro.js");
});
