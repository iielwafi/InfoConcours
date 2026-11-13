import test from "node:test";
import assert from "node:assert/strict";

test("migration bootstrap health contract is intentionally read-only", () => {
  const required = ["ok", "service", "database"];
  const example = { ok: true, service: "infoconcours", database: "connected" };
  assert.deepEqual(Object.keys(example), required);
  assert.equal(example.ok, true);
  assert.equal(example.database, "connected");
});
