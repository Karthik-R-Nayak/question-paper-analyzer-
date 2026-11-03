import assert from "node:assert/strict";
import test from "node:test";

import { ApiError, apiFetch } from "./api.js";

test("apiFetch includes credentials and parses JSON responses", async (context) => {
  let requestUrl;
  let requestOptions;
  context.mock.method(globalThis, "fetch", async (url, options) => {
    requestUrl = url;
    requestOptions = options;
    return new Response(JSON.stringify({ user_id: 7 }), {
      headers: { "Content-Type": "application/json" }
    });
  });

  const result = await apiFetch("/api/v1/auth/me");

  assert.equal(requestUrl, "http://localhost:8000/api/v1/auth/me");
  assert.equal(requestOptions.credentials, "include");
  assert.deepEqual(result, { user_id: 7 });
});

test("apiFetch preserves backend status and detail for API failures", async (context) => {
  context.mock.method(globalThis, "fetch", async () =>
    new Response(JSON.stringify({ detail: "Embedding model unavailable." }), {
      status: 503,
      headers: { "Content-Type": "application/json" }
    })
  );

  await assert.rejects(apiFetch("/api/v1/semantic/similar?q=normalization"), (error) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 503);
    assert.equal(error.message, "Embedding model unavailable.");
    return true;
  });
});

test("apiFetch handles no-content responses", async (context) => {
  context.mock.method(globalThis, "fetch", async () => new Response(null, { status: 204 }));

  assert.equal(await apiFetch("/api/v1/auth/logout", { method: "POST" }), null);
});
