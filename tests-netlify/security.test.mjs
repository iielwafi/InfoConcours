import test from "node:test";
import assert from "node:assert/strict";
import { hashPassword, verifyPassword } from "../netlify/functions/_shared/password.ts";
import { createSession, readSession, csrfToken, validCsrf } from "../netlify/functions/_shared/session.ts";

test("Werkzeug-compatible password hashes verify and reject wrong passwords", () => {
  const encoded = hashPassword("correct horse battery staple");
  assert.match(encoded, /^scrypt:32768:8:1\\$/);
  assert.equal(verifyPassword("correct horse battery staple", encoded), true);
  assert.equal(verifyPassword("wrong password", encoded), false);
  assert.equal(verifyPassword("anything", "invalid"), false);
});

test("signed sessions round-trip and reject tampering", () => {
  process.env.SECRET_KEY = "test-secret-key-that-is-long-enough-for-hmac-32";
  const token = createSession({ userId: 42, role: "student", language: "fr" });
  const session = readSession(token);
  assert.equal(session?.userId, 42);
  assert.equal(session?.role, "student");
  assert.equal(validCsrf(session, csrfToken(session)), true);
  assert.equal(validCsrf(session, "invalid"), false);
  assert.equal(readSession(token + "tampered"), null);
});
