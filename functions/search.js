exports.handler = async (event) => {
  const q = (event.queryStringParameters || {}).q;
  const key = process.env.BRAVE_API_KEY;
  const json = (code, body) => ({
    statusCode: code,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!q) return json(400, { error: "no_query" });
  if (!key) return json(200, { error: "no_key" });
  try {
    const r = await fetch(
      "https://api.search.brave.com/res/v1/web/search?count=10&q=" + encodeURIComponent(q),
      { headers: { Accept: "application/json", "X-Subscription-Token": key } }
    );
    if (!r.ok) return json(200, { error: "upstream" });
    const d = await r.json();
    const results = ((d.web && d.web.results) || []).map((x) => ({
      title: x.title,
      url: x.url,
      description: x.description,
    }));
    return json(200, { results });
  } catch (e) {
    return json(200, { error: "upstream" });
  }
};
