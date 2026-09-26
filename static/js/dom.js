/**
 * Minimal DOM helpers. All text goes through textContent, never innerHTML, so model output cannot inject markup.
 */

export const $ = (id) => document.getElementById(id);

export function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

/** Placeholder shown when a section has no items; use tag "li" inside lists. */
export function emptyMessage(text, tag = "p") {
  return el(tag, "empty", text);
}
