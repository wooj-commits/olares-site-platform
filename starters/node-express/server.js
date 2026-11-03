import express from "express";
const app = express();
const port = Number(process.env.PORT || 3000);
app.get("/api/health", (_req, res) => res.json({ ok: true, runtime: "node-express" }));
app.get("/", (_req, res) => res.type("html").send("<h1>Olares Express starter</h1><p>/api/health</p>"));
app.listen(port, "0.0.0.0", () => console.log(`listening on ${port}`));
