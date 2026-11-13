export type TutorMessage = { role: "user" | "assistant"; content: string };

function openAiOutputText(payload: any): string {
  const parts: string[] = [];
  for (const item of payload?.output ?? []) {
    if (item?.type !== "message") continue;
    for (const part of item?.content ?? []) {
      if (part?.type === "output_text" && typeof part.text === "string") parts.push(part.text);
    }
  }
  const result = parts.join("\n").trim();
  if (!result) throw new Error("empty_ai_response");
  return result;
}

function geminiOutputText(payload: any): string {
  const parts: string[] = [];
  for (const part of payload?.candidates?.[0]?.content?.parts ?? []) {
    if (typeof part?.text === "string") parts.push(part.text);
  }
  const result = parts.join("\n").trim();
  if (!result) throw new Error("empty_ai_response");
  return result;
}

/** True when one supported server-side AI provider key is configured. */
export function hasAiProviderConfigured(): boolean {
  return Boolean(process.env.GEMINI_API_KEY?.trim() || process.env.OPENAI_API_KEY?.trim());
}

/**
 * Gemini Free Tier is preferred when configured, so the app never spends OpenAI
 * credits when both providers are present. OpenAI remains an optional fallback.
 */
async function requestText(
  instructions: string,
  input: TutorMessage[],
  maxOutputTokens = 900,
  jsonMode = false,
): Promise<string> {
  const geminiKey = process.env.GEMINI_API_KEY?.trim();
  const openAiKey = process.env.OPENAI_API_KEY?.trim();
  if (!geminiKey && !openAiKey) throw new Error("ai_not_configured");

  const controller = AbortSignal.timeout(22_000);

  if (geminiKey) {
    const model = (process.env.GEMINI_MODEL || "gemini-3.8-flash").trim();
    if (!model || model.length > 100) throw new Error("invalid_ai_model");
    const result = await fetch(
      "https://generativelanguage.googleapis.com/v1beta/models/" + encodeURIComponent(model) + ":generateContent",
      {
        method: "POST",
        signal: controller,
        headers: {
          "x-goog-api-key": geminiKey,
          "content-type": "application/json",
        },
        body: JSON.stringify({
          system_instruction: { parts: [{ text: instructions }] },
          contents: input.map((message) => ({
            role: message.role === "assistant" ? "model" : "user",
            parts: [{ text: message.content }],
          })),
          generationConfig: {
            maxOutputTokens,
            ...(jsonMode ? { responseMimeType: "application/json" } : {}),
          },
        }),
      },
    );
    if (!result.ok) {
      if (result.status === 429) throw new Error("ai_rate_limited");
      if (result.status === 401 || result.status === 403) throw new Error("ai_provider_auth");
      throw new Error("ai_provider_unavailable");
    }
    return geminiOutputText(await result.json());
  }

  const model = (process.env.OPENAI_MODEL || process.env.AI_TUTOR_MODEL || "gpt-4o-mini").trim();
  if (!model || model.length > 100) throw new Error("invalid_ai_model");
  const result = await fetch("https://api.openai.com/v1/responses", {
    method: "POST",
    signal: controller,
    headers: {
      authorization: "Bearer " + openAiKey,
      "content-type": "application/json",
    },
    body: JSON.stringify({
      model,
      instructions,
      input: input.map((message) => ({ role: message.role, content: message.content })),
      max_output_tokens: maxOutputTokens,
      ...(jsonMode ? { text: { format: { type: "json_object" } } } : {}),
    }),
  });
  if (!result.ok) {
    if (result.status === 429) throw new Error("ai_rate_limited");
    if (result.status === 401 || result.status === 403) throw new Error("ai_provider_auth");
    throw new Error("ai_provider_unavailable");
  }
  return openAiOutputText(await result.json());
}

/** Generate structured JSON through the configured provider (Gemini preferred). */
export async function generateAiJson(args: {
  instructions: string;
  input: string;
  maxOutputTokens?: number;
}): Promise<string> {
  return requestText(
    args.instructions,
    [{ role: "user", content: args.input }],
    args.maxOutputTokens ?? 700,
    true,
  );
}

const TEACHER_INSTRUCTIONS = `Tu es le Professeur IA officiel de la plateforme INFOCONCOURS, spécialisé dans la préparation aux concours d'informatique.

RÈGLES PÉDAGOGIQUES :
- Réponds dans la langue utilisée par l'étudiant : français, arabe ou darija marocaine. Tu peux mélanger français technique et darija si c'est plus clair.
- Quand l'étudiant donne une réponse fausse, dis clairement et gentiment qu'elle est incorrecte. Identifie précisément l'erreur, explique pourquoi, puis montre le raisonnement correct étape par étape.
- Quand une réponse est partiellement correcte, reconnais ce qui est juste et explique ce qui manque.
- Ne donne pas seulement la solution : enseigne la méthode, puis propose une mini-question pour vérifier la compréhension.
- Explique les termes techniques simplement, avec un exemple concret adapté au niveau débutant/intermédiaire.
- Pour le code, explique l'erreur, la ligne ou la logique fautive et une correction minimale.
- Utilise le contenu pédagogique fourni comme référence principale. Si le contenu manque ou est ambigu, dis-le clairement au lieu d'inventer une règle ou une réponse.
- Ne prétends jamais avoir corrigé, enregistré ou modifié une donnée si le serveur ne l'a pas fait.
- N'invente pas les notes officielles, le programme officiel ou les règles du concours.

EXAMENS :
- Pendant un examen actif, ne donne ni réponse, ni correction, ni indice, ni explication liée aux questions. Dis simplement que le Professeur IA est désactivé pendant l'examen. Le serveur bloque normalement cette route également.
- En entraînement et en révision hors examen, tu peux corriger et expliquer librement.`;

export async function askAiTeacher(args: {
  messages: TutorMessage[];
  curriculumContext?: string;
}): Promise<string> {
  const context = args.curriculumContext?.trim()
    ? "\n\nCONTEXTE DU COURS ET DE L'EXERCICE (source prioritaire) :\n" + args.curriculumContext.slice(0, 12_000)
    : "\n\nAucun cours précis n'est attaché à cette conversation. Pose une question de clarification si nécessaire.";
  const messages = args.messages
    .filter((message) => (message.role === "user" || message.role === "assistant") && typeof message.content === "string")
    .slice(-12)
    .map((message) => ({ role: message.role, content: message.content.trim().slice(0, 3_000) }))
    .filter((message) => message.content.length > 0);
  if (!messages.length || messages[messages.length - 1].role !== "user") throw new Error("invalid_tutor_messages");
  return requestText(TEACHER_INSTRUCTIONS + context, messages, 1_000);
}

export async function explainWrongAnswer(args: {
  title: string;
  prompt: string;
  studentAnswer: string;
  correctAnswer: string;
  referenceExplanation?: string;
  language?: string;
}): Promise<string> {
  const language = args.language || "français";
  const input = [{
    role: "user" as const,
    content: [
      "Exercice : " + args.title,
      "Énoncé : " + args.prompt,
      "Réponse de l'étudiant : " + args.studentAnswer,
      "Réponse correcte : " + args.correctAnswer,
      "Explication de référence : " + (args.referenceExplanation || "Non fournie"),
      "Explique en " + language + " pourquoi la réponse de l'étudiant est fausse. Dis clairement qu'elle est incorrecte, identifie l'erreur sans humilier, explique le raisonnement correct en étapes courtes, puis propose une petite question de vérification. N'ajoute pas de notions non nécessaires."
    ].join("\n\n"),
  }];
  return requestText(
    "Tu es un professeur patient d'INFOCONCOURS. Corrige précisément une réponse d'entraînement. L'étudiant est hors mode examen.",
    input,
    600,
  );
}
