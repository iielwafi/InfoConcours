export type HttpMethod = "GET" | "POST";
export type AccessLevel = "public" | "authenticated" | "admin";

/** Canonical route inventory extracted from the existing Flask application. */
export const ROUTE_CONTRACT = [
  { name: "home", methods: ["GET"], paths: ["/"], access: "public" },
  { name: "register", methods: ["GET", "POST"], paths: ["/register"], access: "public" },
  { name: "login", methods: ["GET", "POST"], paths: ["/login"], access: "public" },
  { name: "logout", methods: ["POST"], paths: ["/logout"], access: "authenticated" },
  { name: "profile", methods: ["GET", "POST"], paths: ["/profile"], access: "authenticated" },
  { name: "dashboard", methods: ["GET"], paths: ["/dashboard"], access: "authenticated" },
  { name: "diagnostic", methods: ["GET", "POST"], paths: ["/diagnostic"], access: "authenticated" },
  { name: "diagnostic_result", methods: ["GET"], paths: ["/diagnostic/:id"], access: "authenticated" },
  { name: "courses", methods: ["GET"], paths: ["/courses"], access: "authenticated" },
  { name: "continue_course", methods: ["GET"], paths: ["/courses/continue"], access: "authenticated" },
  { name: "lesson", methods: ["GET", "POST"], paths: ["/courses/:slug", "/courses/:slug/lesson/:lesson_id"], access: "authenticated" },
  { name: "complete_lesson", methods: ["POST"], paths: ["/courses/:slug/lesson/:lesson_id/complete"], access: "authenticated" },
  { name: "submit_exercise_attempt", methods: ["POST"], paths: ["/exercise/:exercise_id/attempt"], access: "authenticated" },
  { name: "qcm", methods: ["GET", "POST"], paths: ["/qcm"], access: "authenticated" },
  { name: "planner", methods: ["GET"], paths: ["/planner"], access: "authenticated" },
  { name: "study", methods: ["GET", "POST"], paths: ["/study"], access: "authenticated" },
  { name: "errors", methods: ["GET"], paths: ["/errors"], access: "authenticated" },
  { name: "bookmark", methods: ["POST"], paths: ["/bookmark/:question_id"], access: "authenticated" },
  { name: "bookmarks", methods: ["GET"], paths: ["/bookmarks"], access: "authenticated" },
  { name: "set_language", methods: ["POST"], paths: ["/language"], access: "authenticated" },
  { name: "videos", methods: ["GET"], paths: ["/videos"], access: "authenticated" },
  { name: "mark_video_watched", methods: ["POST"], paths: ["/videos/:video_id/watched"], access: "authenticated" },
  { name: "admin_curriculum", methods: ["GET", "POST"], paths: ["/admin/curriculum"], access: "admin" },
  { name: "admin_exercise_attempts", methods: ["GET", "POST"], paths: ["/admin/exercise-attempts"], access: "admin" },
  { name: "admin_quality", methods: ["GET"], paths: ["/admin/quality"], access: "admin" },
  { name: "admin_videos", methods: ["GET", "POST"], paths: ["/admin/videos"], access: "admin" },
  { name: "exam", methods: ["GET", "POST"], paths: ["/exam"], access: "authenticated" },
  { name: "admin", methods: ["GET", "POST"], paths: ["/admin"], access: "admin" },
] as const satisfies ReadonlyArray<{
  name: string;
  methods: readonly HttpMethod[];
  paths: readonly string[];
  access: AccessLevel;
}>;

export const LEGACY_ROUTE_DECORATOR_COUNT = 29;
