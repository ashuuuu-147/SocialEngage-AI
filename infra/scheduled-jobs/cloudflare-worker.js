/**
 * Cloudflare Worker Cron Scheduler for SocialEngage AI
 * Triggers cloud-side monitoring independently of the user's laptop.
 * Secrets (set via `wrangler secret put`):
 *   - API_BASE_URL (e.g. https://api.socialengage.example.com)
 *   - INTERNAL_JOB_SECRET
 */

async function signPayload(secret, timestamp, body) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const data = enc.encode(`${timestamp}.${body}`);
  const sigBuffer = await crypto.subtle.sign("HMAC", key, data);
  return Array.from(new Uint8Array(sigBuffer))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

async function triggerInternalJob(env, path, payload = {}) {
  const body = JSON.stringify(payload);
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const signature = await signPayload(env.INTERNAL_JOB_SECRET, timestamp, body);

  const response = await fetch(`${env.API_BASE_URL.replace(/\/$/, "")}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Internal-Job-Timestamp": timestamp,
      "X-Internal-Job-Signature": signature,
    },
    body,
  });

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`Job ${path} failed with HTTP ${response.status}: ${errText}`);
  }
  return response.json();
}

export default {
  async scheduled(event, env, ctx) {
    if (event.cron === "0 13 * * *") {
      ctx.waitUntil(triggerInternalJob(env, "/api/v1/internal/jobs/daily-digest", {}));
    } else {
      ctx.waitUntil(triggerInternalJob(env, "/api/v1/internal/jobs/monitor", {}));
    }
  },
};
