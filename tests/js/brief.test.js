import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import {
  CATEGORY_LABELS,
  TOPIC_LABELS,
  allFindings,
  checklistItems,
  documentLabel,
  questionGroups,
  questionsAsText,
  sourceLocation,
  verificationStats,
} from "../../static/js/brief.js";

const sample = JSON.parse(readFileSync(new URL("../../samples/sample_brief.json", import.meta.url), "utf8"));

const source = (verified) => ({ page: 1, section: null, quote: "q", verified });

function makeBrief() {
  return {
    document: { filename: "offer.pdf", pages: 1, characters: 500 },
    overview: { key_terms: [{ term: "Notice", source: source(true) }] },
    responsibilities: [
      { title: "Sign", category: "deadline", source: source(true) },
      { title: "Keep secrets", category: "obligation", source: source(false) },
      { title: "Give notice", category: "notice", source: source(true) },
    ],
    clauses_to_review: [
      { title: "Bond", questions_to_ask: ["How is it calculated?", "Is it pro-rata?"], source: source(true) },
      { title: "Transfer", questions_to_ask: [], source: source(false) },
    ],
    action_plan: { missing_or_unclear: [{ title: "Annexure", source: source(true) }], next_steps: [] },
  };
}

test("allFindings covers every section that carries a source", () => {
  assert.equal(allFindings(makeBrief()).length, 7);
});

test("verificationStats counts verified sources", () => {
  assert.deepEqual(verificationStats(makeBrief()), { total: 7, verified: 5 });
});

test("checklistItems keeps only dated, deadline and notice responsibilities", () => {
  assert.deepEqual(
    checklistItems(makeBrief()).map((item) => item.title),
    ["Sign", "Give notice"],
  );
});

test("questionGroups skips clauses without questions", () => {
  assert.deepEqual(
    questionGroups(makeBrief()).map((clause) => clause.title),
    ["Bond"],
  );
});

test("questionsAsText produces a numbered, paste-ready list", () => {
  const text = questionsAsText(makeBrief());
  assert.match(text, /^Questions about offer\.pdf \(prepared with LegalLens\)/);
  assert.match(text, /1\. Bond\n {3}- How is it calculated\?\n {3}- Is it pro-rata\?/);
  assert.doesNotMatch(text, /Transfer/);
});

test("sourceLocation joins the known parts only", () => {
  assert.equal(sourceLocation({ page: 2, section: "7. Service Bond" }), "Page 2 · 7. Service Bond");
  assert.equal(sourceLocation({ page: null, section: "Clause 3" }), "Clause 3");
  assert.equal(sourceLocation({ page: null, section: null }), "");
});

test("documentLabel pluralises pages", () => {
  assert.equal(documentLabel({ filename: "a.pdf", pages: 1 }), "a.pdf · 1 page");
  assert.equal(documentLabel({ filename: "a.pdf", pages: 3 }), "a.pdf · 3 pages");
});

test("labels exist for every category and topic the server can send", () => {
  for (const item of sample.responsibilities) assert.ok(CATEGORY_LABELS[item.category], item.category);
  for (const clause of sample.clauses_to_review) assert.ok(TOPIC_LABELS[clause.topic], clause.topic);
});

test("the committed sample brief is fully verified", () => {
  const { total, verified } = verificationStats(sample);
  assert.ok(total > 0);
  assert.equal(verified, total);
});
