/**
 * Action Plan tab: deadlines checklist, next steps, missing or unclear information, and consolidated questions.
 */

import { checklistItems, questionGroups, questionsAsText } from "./brief.js";
import { $, el, emptyMessage } from "./dom.js";
import { sourceBlock } from "./source.js";

function renderChecklist(brief) {
  const list = $("plan-checklist");
  list.replaceChildren();
  const items = checklistItems(brief);
  if (!items.length) list.append(emptyMessage("No dates or deadlines were identified.", "li"));
  for (const item of items) {
    const box = el("input");
    box.type = "checkbox";
    const text = el("span", "check-text");
    text.append(el("strong", null, item.title));
    if (item.timing) text.append(el("span", "check-timing", item.timing));
    const label = el("label", "check-item");
    label.append(box, text);
    const row = el("li");
    row.append(label);
    list.append(row);
  }
}

function renderNextSteps(steps) {
  const list = $("plan-steps");
  list.replaceChildren();
  if (!steps.length) list.append(emptyMessage("No next steps were suggested.", "li"));
  for (const step of steps) list.append(el("li", null, step));
}

function renderMissing(items) {
  const root = $("plan-missing");
  root.replaceChildren();
  if (!items.length) root.append(emptyMessage("Nothing was identified as missing or unclear."));
  for (const item of items) {
    const card = el("article", "card finding accent-missing");
    card.append(el("h3", "card-title", item.title), el("p", null, item.detail), sourceBlock(item.source));
    root.append(card);
  }
}

function renderQuestions(brief) {
  const root = $("plan-questions");
  root.replaceChildren();
  $("copy-status").textContent = "";
  const groups = questionGroups(brief);
  $("copy-questions").hidden = !groups.length;
  if (!groups.length) root.append(emptyMessage("No questions were suggested.", "li"));
  for (const clause of groups) {
    const list = el("ul", "questions");
    for (const question of clause.questions_to_ask) list.append(el("li", null, question));
    const group = el("li");
    group.append(el("p", "group-title", clause.title), list);
    root.append(group);
  }
}

export function renderActionPlan(brief) {
  renderChecklist(brief);
  renderNextSteps(brief.action_plan.next_steps);
  renderMissing(brief.action_plan.missing_or_unclear);
  renderQuestions(brief);
}

export async function copyQuestions(brief) {
  try {
    await navigator.clipboard.writeText(questionsAsText(brief));
    $("copy-status").textContent = "Questions copied to your clipboard.";
  } catch {
    $("copy-status").textContent = "Copying is not available in this browser. Please select the questions and copy them.";
  }
}
