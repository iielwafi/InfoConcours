export type AttemptRecord = {
  id?: number | string;
  details?: string | unknown[] | null;
};

export type DomainReviewSummary = {
  domain: string;
  average: number;
  attempts: number;
  responses: number;
};

/**
 * Builds per-domain QCM performance from the answer details stored on each
 * attempt. The attempt table intentionally has no "domain" column: domain is
 * stored on each question detail.
 */
export function summarizeAttemptDetails(attempts: readonly AttemptRecord[]): DomainReviewSummary[] {
  const grouped = new Map<string, {
    correct: number;
    responses: number;
    attempts: number;
  }>();

  for (const attempt of attempts) {
    let details: unknown = attempt.details;
    if (typeof details === "string") {
      try {
        details = JSON.parse(details);
      } catch {
        continue;
      }
    }
    if (!Array.isArray(details)) continue;

    const domainsInAttempt = new Set<string>();
    for (const item of details) {
      if (!item || typeof item !== "object") continue;
      const detail = item as Record<string, unknown>;
      const domain = typeof detail.domain === "string" ? detail.domain.trim() : "";
      if (!domain || typeof detail.ok !== "boolean") continue;

      const summary = grouped.get(domain) ?? { correct: 0, responses: 0, attempts: 0 };
      summary.responses += 1;
      if (detail.ok) summary.correct += 1;
      grouped.set(domain, summary);
      domainsInAttempt.add(domain);
    }

    for (const domain of domainsInAttempt) {
      const summary = grouped.get(domain);
      if (summary) summary.attempts += 1;
    }
  }

  return Array.from(grouped, ([domain, summary]) => ({
    domain,
    average: summary.responses ? Math.round((summary.correct * 100) / summary.responses) : 0,
    attempts: summary.attempts,
    responses: summary.responses,
  })).sort((a, b) => a.average - b.average || a.domain.localeCompare(b.domain, "fr"));
}
