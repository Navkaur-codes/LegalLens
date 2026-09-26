import assert from "node:assert/strict";
import { afterEach, test } from "node:test";

import { NETWORK_ERROR, fetchConfig, postBrief } from "../../static/js/api.js";

const realFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = realFetch;
});

function respondWith(status, body, contentType = "application/json") {
  globalThis.fetch = async () =>
    new Response(typeof body === "string" ? body : JSON.stringify(body), {
      status,
      headers: { "content-type": contentType },
    });
}

test("postBrief returns the brief on success", async () => {
  respondWith(200, { is_demo: true });
  assert.deepEqual(await postBrief("/api/brief/sample"), { is_demo: true });
});

test("postBrief surfaces the server's friendly error message", async () => {
  respondWith(413, { detail: "The file is larger than 5 MB." });
  await assert.rejects(postBrief("/api/brief"), { message: "The file is larger than 5 MB." });
});

test("postBrief explains non-JSON responses (e.g. page opened without the backend)", async () => {
  respondWith(501, "<html>Not implemented</html>", "text/html");
  await assert.rejects(postBrief("/api/brief"), /Unexpected response from the server \(HTTP 501\)/);
});

test("postBrief turns network failures into a clear message", async () => {
  globalThis.fetch = async () => {
    throw new TypeError("Failed to fetch");
  };
  await assert.rejects(postBrief("/api/brief"), { message: NETWORK_ERROR });
});

test("fetchConfig returns the limits", async () => {
  respondWith(200, { max_file_mb: 5, max_pages: 10, max_chars: 18000, llm_mode: "mock" });
  assert.equal((await fetchConfig()).max_pages, 10);
});

test("fetchConfig rejects when the server is unreachable", async () => {
  respondWith(404, "Not found", "text/plain");
  await assert.rejects(fetchConfig(), { message: NETWORK_ERROR });
});
