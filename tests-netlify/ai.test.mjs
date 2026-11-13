import test from "node:test";
import assert from "node:assert/strict";
import { generateAiJson, hasAiProviderConfigured } from "../netlify/functions/_shared/ai.ts";

test("AI provider is reported unavailable when no API key exists", () => {
  const oldGemini = process.env.GEMINI_API_KEY;
  const oldOpenAI = process.env.OPENAI_API_KEY;
  delete process.env.GEMINI_API_KEY;
  delete process.env.OPENAI_API_KEY;
  assert.equal(hasAiProviderConfigured(), false);
  return Promise.resolve().then(() => {
    if (oldGemini === undefined) delete process.env.GEMINI_API_KEY;
    else process.env.GEMINI_API_KEY = oldGemini;
    if (oldOpenAI === undefined) delete process.env.OPENAI_API_KEY;
    else process.env.OPENAI_API_KEY = oldOpenAI;
  });
});

test("Gemini is preferred and receives a JSON-mode grading request", async () => {
  const oldGemini = process.env.GEMINI_API_KEY;
  const oldOpenAI = process.env.OPENAI_API_KEY;
  const oldModel = process.env.GEMINI_MODEL;
  const oldAiTutorModel = process.env.AI_TUTOR_MODEL;
  const oldFetch = globalThis.fetch;
  process.env.GEMINI_API_KEY = "test-gemini-key";
  process.env.OPENAI_API_KEY = "test-openai-key";
  process.env.GEMINI_MODEL = "gemini-3.8-flash";
  delete process.env.AI_TUTOR_MODEL;

  let requestedUrl = "";
  let requestInit;
  globalThis.fetch = async (input, init) => {
    requestedUrl = String(input);
    requestInit = init;
    return new Response(JSON.stringify({
      candidates: [{ content: { parts: [{ text: '{"score":90,"confidence":0.95}' }] } }],
    }), { status: 200, headers: { "content-type": "application/json" } });
  };

  try {
    assert.equal(hasAiProviderConfigured(), true);
    const output = await generateAiJson({
      instructions: "Return JSON only.",
      input: '{"student_answer":"test"}',
    });
    assert.equal(output, '{"score":90,"confidence":0.95}');
    assert.match(requestedUrl, /models\/gemini-3\.8-flash:generateContent$/);
    assert.equal(requestInit.headers["x-goog-api-key"], "test-gemini-key");
    assert.equal(requestInit.headers.authorization, undefined);
    const body = JSON.parse(requestInit.body);
    assert.equal(body.generationConfig.responseMimeType, "application/json");
    assert.equal(body.system_instruction.parts[0].text, "Return JSON only.");
  } finally {
    globalThis.fetch = oldFetch;
    if (oldGemini === undefined) delete process.env.GEMINI_API_KEY;
    else process.env.GEMINI_API_KEY = oldGemini;
    if (oldOpenAI === undefined) delete process.env.OPENAI_API_KEY;
    else process.env.OPENAI_API_KEY = oldOpenAI;
    if (oldModel === undefined) delete process.env.GEMINI_MODEL;
    else process.env.GEMINI_MODEL = oldModel;
    if (oldAiTutorModel === undefined) delete process.env.AI_TUTOR_MODEL;
    else process.env.AI_TUTOR_MODEL = oldAiTutorModel;
  }
});
