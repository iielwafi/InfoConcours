import test from "node:test";
import assert from "node:assert/strict";
import { hashPassword, verifyPassword } from "../netlify/functions/_shared/password.ts";
import { createSession, readSession, csrfToken, validCsrf } from "../netlify/functions/_shared/session.ts";

test("Werkzeug scrypt and PBKDF2 hashes remain compatible", () => {
  const werkzeugScrypt = "scrypt:32768:8:1$W1axPvZQVwB4MIzh$5013f627d3d20206e1fdbf112fb070337d78966a97209972387e6a69a5455e0753608a44e5a8f76db5c442033c905a26b6fd2fd397c6c4c5bce09f751e7beddf";
  const werkzeugPbkdf2 = "pbkdf2:sha256:600000$gNTSPq8AdfzDz6gi$34443aef7a109f9a1792662c1942753b077da61e81da1c41ad28875dd179df99";
  assert.equal(verifyPassword("password-test", werkzeugScrypt), true);
  assert.equal(verifyPassword("password-test", werkzeugPbkdf2), true);
  assert.equal(verifyPassword("wrong", werkzeugScrypt), false);
});

test("new password hashes verify and reject wrong passwords", () => {
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
