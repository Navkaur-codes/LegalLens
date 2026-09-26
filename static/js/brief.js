/**
 * Pure helpers for working with a brief (the API response). No DOM access, so they are unit-tested in Node.
 */

export const CATEGORY_LABELS = {
  obligation: "Obligation",
  deadline: "Deadline",
  notice: "Notice",
  date: "Date",
  other: "Other",
};

export const TOPIC_LABELS = {
  bond: "Service bond",
  non_compete: "Non-compete",
  termination: "Termination & notice",
  confidentiality: "Confidentiality",
  ip: "Intellectual property",
  compensation: "Compensation",
  working_terms: "Working terms",
  other: "Other",
};

const CHECKLIST_CATEGORIES = new Set(["deadline", "date", "notice"]);

/** Every item that carries a source, in display order (mirrors BriefContent.findings() on the server). */
export function allFindings(brief) {
  return [
    ...brief.overview.key_terms,
    ...brief.responsibilities,
    ...brief.clauses_to_review,
    ...brief.action_plan.missing_or_unclear,
  ];
}

export function verificationStats(brief) {
  const findings = allFindings(brief);
  return { total: findings.length, verified: findings.filter((finding) => finding.source.verified).length };
}

/** Responsibilities with a date, deadline or notice period, for the Action Plan checklist. */
export function checklistItems(brief) {
  return brief.responsibilities.filter((item) => CHECKLIST_CATEGORIES.has(item.category));
}

/** Clauses that come with suggested questions. */
export function questionGroups(brief) {
  return brief.clauses_to_review.filter((clause) => clause.questions_to_ask.length > 0);
}

/** Plain-text list of questions, ready to paste into an email to HR or a lawyer. */
export function questionsAsText(brief) {
  const lines = [`Questions about ${brief.document.filename} (prepared with LegalLens)`, ""];
  questionGroups(brief).forEach((clause, index) => {
    lines.push(`${index + 1}. ${clause.title}`);
    for (const question of clause.questions_to_ask) lines.push(`   - ${question}`);
  });
  return lines.join("\n");
}

/** "Page 2 · Clause 7" style label; empty string when neither is known. */
export function sourceLocation(source) {
  return [source.page ? `Page ${source.page}` : null, source.section].filter(Boolean).join(" · ");
}

export function documentLabel(document) {
  return `${document.filename} · ${document.pages} page${document.pages === 1 ? "" : "s"}`;
}
