/**
 * Renders a brief into the results view: meta, banners, Overview, Responsibilities, Clauses and the summary panel.
 */

import { renderActionPlan } from "./action-plan.js";
import { CATEGORY_LABELS, TOPIC_LABELS, documentLabel, verificationStats } from "./brief.js";
import { $, el, emptyMessage } from "./dom.js";
import { sourceBlock } from "./source.js";
import { selectTab } from "./tabs.js";

function renderOverview(overview) {
  const root = $("overview-content");
  root.replaceChildren();

  const summaryCard = el("div", "card summary-card");
  summaryCard.append(el("h3", "card-title", "Summary"), el("p", "summary", overview.summary));

  const facts = el("dl", "facts");
  for (const [label, value] of [
    ["Document type", overview.document_type],
    ["Employer", overview.employer],
    ["Employee", overview.employee],
  ]) {
    const fact = el("div");
    fact.append(el("dt", null, label), el("dd", null, value || "Not stated"));
    facts.append(fact);
  }
  summaryCard.append(facts);
  root.append(summaryCard, el("h3", "section-title", "Key terms"));

  if (!overview.key_terms.length) {
    root.append(emptyMessage("No key terms were identified in the document."));
    return;
  }
  const grid = el("div", "card-grid");
  for (const term of overview.key_terms) {
    const card = el("article", "card finding key-term");
    card.append(el("p", "finding-label", term.term));
    if (term.value) card.append(el("p", "finding-value", term.value));
    card.append(el("p", null, term.explanation), sourceBlock(term.source));
    grid.append(card);
  }
  root.append(grid);
}

function findingHead(title, tagClass, tagText) {
  const head = el("div", "finding-head");
  head.append(el("h3", "card-title", title), el("span", `tag ${tagClass}`, tagText));
  return head;
}

function renderResponsibilities(items) {
  const root = $("responsibilities-content");
  root.replaceChildren();
  $("count-responsibilities").textContent = `(${items.length})`;
  if (!items.length) {
    root.append(emptyMessage("No responsibilities or deadlines were identified in the document."));
    return;
  }
  for (const item of items) {
    const card = el("article", `card finding accent-${item.category}`);
    card.append(findingHead(item.title, `tag-${item.category}`, CATEGORY_LABELS[item.category]));
    if (item.timing) card.append(el("p", "timing", `When: ${item.timing}`));
    card.append(el("p", null, item.description), sourceBlock(item.source));
    root.append(card);
  }
}

function renderClauses(items) {
  const root = $("clauses-content");
  root.replaceChildren();
  $("count-clauses").textContent = `(${items.length})`;
  if (!items.length) {
    root.append(emptyMessage("No clauses were flagged for review."));
    return;
  }
  for (const item of items) {
    const card = el("article", "card finding accent-clause");
    card.append(findingHead(item.title, "tag-topic", TOPIC_LABELS[item.topic]));
    card.append(el("p", "field-label", "What it says"), el("p", null, item.what_it_says));
    card.append(el("p", "field-label", "Why it may matter"), el("p", null, item.why_it_matters));
    if (item.questions_to_ask.length) {
      card.append(el("p", "field-label", "Questions you could ask"));
      const list = el("ul", "questions");
      for (const question of item.questions_to_ask) list.append(el("li", null, question));
      card.append(list);
    }
    card.append(sourceBlock(item.source));
    root.append(card);
  }
}

function renderStats(brief) {
  const { total, verified } = verificationStats(brief);
  $("stat-terms").textContent = brief.overview.key_terms.length;
  $("stat-resp").textContent = brief.responsibilities.length;
  $("stat-clauses").textContent = brief.clauses_to_review.length;
  $("stat-missing").textContent = brief.action_plan.missing_or_unclear.length;
  $("stat-verified").textContent = `${verified} / ${total}`;
  $("verified-progress").max = Math.max(total, 1);
  $("verified-progress").value = verified;
}

export function renderBrief(brief) {
  $("doc-meta").textContent = documentLabel(brief.document);
  $("demo-banner").hidden = !brief.is_demo;
  $("mock-banner").hidden = brief.is_demo || !brief.is_mock;
  $("verification-note").textContent = brief.verification_note;
  $("disclaimer").replaceChildren(el("strong", null, "Disclaimer: "), document.createTextNode(brief.disclaimer));

  renderOverview(brief.overview);
  renderResponsibilities(brief.responsibilities);
  renderClauses(brief.clauses_to_review);
  renderActionPlan(brief);
  renderStats(brief);
  selectTab($("tab-overview"), false);
}
