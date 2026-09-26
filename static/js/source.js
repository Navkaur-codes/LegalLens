/**
 * The source block shown on every finding: verification badge, page/section and verbatim quote.
 */

import { sourceLocation } from "./brief.js";
import { el } from "./dom.js";

export function sourceBlock(source) {
  const wrap = el("div", "source");
  const head = el("div", "source-head");
  head.append(
    el(
      "span",
      `badge ${source.verified ? "badge-verified" : "badge-unverified"}`,
      source.verified ? "✓ Source verified" : "⚠ Source not verified",
    ),
  );
  const location = sourceLocation(source);
  if (location) head.append(el("span", "source-location", location));
  wrap.append(head);

  if (source.quote) wrap.append(el("blockquote", "source-quote", `“${source.quote}”`));
  return wrap;
}
