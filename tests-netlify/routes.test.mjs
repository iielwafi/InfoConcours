import test from "node:test";
import assert from "node:assert/strict";
import { ROUTE_CONTRACT, LEGACY_ROUTE_DECORATOR_COUNT } from "../netlify/functions/_shared/route-contract.ts";

test("Netlify route inventory preserves legacy endpoints and adds AI tutor routes", () => {
  assert.equal(ROUTE_CONTRACT.length, 29);
  assert.equal(ROUTE_CONTRACT.reduce((count, route) => count + route.paths.length, 0), 30);
  assert.equal(LEGACY_ROUTE_DECORATOR_COUNT, 29);
  assert.ok(ROUTE_CONTRACT.some((route) => route.name === "ai_tutor" && route.paths.includes("/tutor")));
  assert.ok(ROUTE_CONTRACT.some((route) => route.name === "ai_tutor_api" && route.paths.includes("/api/tutor")));
});

test("every authenticated/admin route is marked with the correct access boundary", () => {
  const admin = ROUTE_CONTRACT.filter((route) => route.name.startsWith("admin"));
  assert.equal(admin.length, 4);
  assert.ok(admin.every((route) => route.access === "admin"));
  assert.ok(ROUTE_CONTRACT.filter((route) => route.name === "home" || route.name === "login" || route.name === "register")
    .every((route) => route.access === "public"));
});

test("the obsolete human exercise-correction route is not exposed", () => {
  assert.ok(!ROUTE_CONTRACT.some((route) => route.paths.includes("/admin/exercise-attempts")));
});
