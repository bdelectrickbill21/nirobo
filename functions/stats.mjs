// Admin only: returns the last 14 days of numbers. Needs the ADMIN_KEY set in Netlify.
import { getStore } from "@netlify/blobs";
import { timingSafeEqual } from "node:crypto";

const json = (status, body) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });

const same = (a, b) => {
  const x = Buffer.from(a);
  const y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
};

export default async (req) => {
  const secret = process.env.ADMIN_KEY;
  if (!secret) return json(503, { error: "ADMIN_KEY is not set in Netlify yet" });
  if (!same(req.headers.get("x-admin-key") || "", secret)) return json(401, { error: "Wrong key" });

  const store = getStore("stats");
  const days = [];
  for (let i = 0; i < 14; i++) {
    const day = new Date(Date.now() - i * 86400000).toISOString().slice(0, 10);
    const d = (await store.get("day-" + day, { type: "json" })) || { searches: 0, noresults: 0, impressions: {}, clicks: {} };
    days.push({ day, ...d });
  }
  return json(200, { days });
};

export const config = { path: "/api/stats" };
