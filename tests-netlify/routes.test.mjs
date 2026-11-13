import test from "node:test";
import assert from "node:assert/strict";
import { ROUTE_CONTRACT, LEGACY_ROUTE_DECORATOR_COUNT } from "../netlify/functions/_shared/route-contract.ts";

test("migration manifest covers every distinct Flask endpoint and route decorator", () => {
  assert.equal(ROUTE_CONTRACT.length, 28);
  assert.equal(ROUTE_CONTRACT.reduce((count, route) => count + route.paths.length, 0), LEGACY_ROUTE_DECORATOR_COUNT);
  assert.equal(LEGACY_ROUTE_DECORATOR_COUNT, 29);
});

test("every authenticated/admin route is marked with the correct access boundary", () => {
  const admin = ROUTE_CONTRACT.filter((route) => route.name.startsWith("admin"));
  assert.equal(admin.length, 5);
  assert.ok(admin.every((route) => route.access === "admin"));
  assert.ok(ROUTE_CONTRACT.filter((route) => route.name === "home" || route.name === "login" || route.name === "register")
    .every((route) => route.access === "public"));
});
