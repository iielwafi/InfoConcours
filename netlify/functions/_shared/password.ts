import { randomBytes, scryptSync, pbkdf2Sync, timingSafeEqual } from "node:crypto";

/**
 * Werkzeug-compatible password hashing.
 * Existing hashes remain verifiable after migration; new hashes use Werkzeug's
 * scrypt format so Flask can still verify them if rollback is ever required.
 */
export function verifyPassword(password: string, encoded: string): boolean {
  try {
    const [method, salt, expectedHex] = encoded.split("$");
    if (!method || !salt || !expectedHex || !/^[a-f0-9]+$/i.test(expectedHex)) return false;
    const expected = Buffer.from(expectedHex, "hex");
    let actual: Buffer;
    if (method.startsWith("scrypt:")) {
      const [, n, r, p] = method.split(":");
      actual = scryptSync(password, salt, expected.length, {
        N: Number(n), r: Number(r), p: Number(p), maxmem: 128 * 1024 * 1024,
      });
    } else if (method.startsWith("pbkdf2:")) {
      const [, digest, iterations] = method.split(":");
      actual = pbkdf2Sync(password, salt, Number(iterations), expected.length, digest);
    } else {
      return false;
    }
    return actual.length === expected.length && timingSafeEqual(actual, expected);
  } catch {
    return false;
  }
}

export function hashPassword(password: string): string {
  const salt = randomBytes(16).toString("hex");
  const hash = scryptSync(password, salt, 64, {
    N: 32768, r: 8, p: 1, maxmem: 128 * 1024 * 1024,
  }).toString("hex");
  return `scrypt:32768:8:1$${salt}$${hash}`;
}
