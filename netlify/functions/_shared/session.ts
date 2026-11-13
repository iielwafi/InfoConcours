import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";

export type UserSession = {
  userId: number;
  role: "student" | "admin";
  language: "fr" | "ar";
  nonce: string;
  expiresAt: number;
};

const COOKIE_NAME = "infoconcours_session";
const SESSION_TTL_SECONDS = 60 * 60 * 24 * 14;

function secret(): string {
  const value = process.env.SECRET_KEY;
  if (!value || value.length < 32) throw new Error("SECRET_KEY must contain at least 32 characters");
  return value;
}

function sign(value: string): string {
  return createHmac("sha256", secret()).update(value).digest("base64url");
}

export function createSession(user: Omit<UserSession, "nonce" | "expiresAt">): string {
  const payload: UserSession = {
    ...user,
    nonce: randomBytes(18).toString("base64url"),
    expiresAt: Math.floor(Date.now() / 1000) + SESSION_TTL_SECONDS,
  };
  const encoded = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return `${encoded}.${sign(encoded)}`;
}

export function readSession(token?: string): UserSession | null {
  if (!token) return null;
  try {
    const [encoded, providedSignature] = token.split(".");
    if (!encoded || !providedSignature) return null;
    const expected = Buffer.from(sign(encoded));
    const provided = Buffer.from(providedSignature);
    if (expected.length !== provided.length || !timingSafeEqual(expected, provided)) return null;
    const payload = JSON.parse(Buffer.from(encoded, "base64url").toString("utf8")) as UserSession;
    if (!Number.isInteger(payload.userId) || payload.userId <= 0) return null;
    if (payload.role !== "student" && payload.role !== "admin") return null;
    if (payload.language !== "fr" && payload.language !== "ar") return null;
    if (!payload.nonce || payload.expiresAt <= Math.floor(Date.now() / 1000)) return null;
    return payload;
  } catch {
    return null;
  }
}

export function cookieHeader(token: string, secure = true): string {
  const flags = [
    `${COOKIE_NAME}=${token}`,
    "Path=/",
    "HttpOnly",
    "SameSite=Lax",
    `Max-Age=${SESSION_TTL_SECONDS}`,
  ];
  if (secure) flags.push("Secure");
  return flags.join("; ");
}

export function expiredCookieHeader(secure = true): string {
  const flags = [`${COOKIE_NAME}=`, "Path=/", "HttpOnly", "SameSite=Lax", "Max-Age=0"];
  if (secure) flags.push("Secure");
  return flags.join("; ");
}

export function sessionFromRequest(request: Request): UserSession | null {
  const cookies = request.headers.get("cookie") ?? "";
  const token = cookies.split(";").map((part) => part.trim()).find((part) => part.startsWith(`${COOKIE_NAME}=`))?.slice(COOKIE_NAME.length + 1);
  return readSession(token);
}

export function csrfToken(session: UserSession): string {
  return createHmac("sha256", secret()).update(`csrf:${session.nonce}`).digest("base64url");
}

export function validCsrf(session: UserSession, token: string): boolean {
  const expected = Buffer.from(csrfToken(session));
  const actual = Buffer.from(token || "");
  return expected.length === actual.length && timingSafeEqual(expected, actual);
}
