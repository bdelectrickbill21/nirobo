// Counts searches, impressions and clicks (totals per day only, no personal data).
import { getStore } from "@netlify/blobs";

const HOST = /^[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?$/;

export default async (req) => {
  if (req.method !== "POST") return new Response("Method not allowed", { status: 405 });

  let body;
  try {
    const text = await req.text();
    if (text.length > 4000) return new Response("Too large", { status: 413 });
    body = JSON.parse(text);
  } catch (e) {
    return new Response("Bad request", { status: 400 });
  }
  if (!body || (body.t !== "search" && body.t !== "click")) {
    return new Response("Bad request", { status: 400 });
  }

  const hosts = (Array.isArray(body.h) ? body.h : [])
    .slice(0, 20)
    .map((h) => String(h).toLowerCase())
    .filter((h) => HOST.test(h));

  const store = getStore("stats");
  const key = "day-" + new Date().toISOString().slice(0, 10);
  const d = (await store.get(key, { type: "json" })) || { searches: 0, noresults: 0, impressions: {}, clicks: {} };

  if (body.t === "search") {
    d.searches += 1;
    if (Number(body.n) === 0) d.noresults += 1;
    for (const h of hosts) d.impressions[h] = (d.impressions[h] || 0) + 1;
  } else if (hosts[0]) {
    d.clicks[hosts[0]] = (d.clicks[hosts[0]] || 0) + 1;
  }

  await store.setJSON(key, d);
  return new Response(null, { status: 204 });
};

export const config = { path: "/api/event" };
