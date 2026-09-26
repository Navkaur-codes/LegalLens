/**
 * WAI-ARIA tabs: click or arrow keys / Home / End to switch; only the selected tab is in the tab order.
 */

import { $ } from "./dom.js";

export function selectTab(tab, moveFocus = true) {
  for (const other of document.querySelectorAll('[role="tab"]')) {
    const selected = other === tab;
    other.setAttribute("aria-selected", String(selected));
    other.tabIndex = selected ? 0 : -1;
    $(other.getAttribute("aria-controls")).hidden = !selected;
  }
  if (moveFocus) tab.focus();
}

export function setupTabs() {
  const tabs = [...document.querySelectorAll('[role="tab"]')];
  for (const tab of tabs) {
    tab.addEventListener("click", () => selectTab(tab));
    tab.addEventListener("keydown", (event) => {
      const index = tabs.indexOf(tab);
      const targets = {
        ArrowRight: tabs[(index + 1) % tabs.length],
        ArrowLeft: tabs[(index - 1 + tabs.length) % tabs.length],
        Home: tabs[0],
        End: tabs[tabs.length - 1],
      };
      if (targets[event.key]) {
        event.preventDefault();
        selectTab(targets[event.key]);
      }
    });
  }
}
