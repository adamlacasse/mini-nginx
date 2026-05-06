const express = require("express");

const app = express();
const PORT = 3000;
const HOST = "127.0.0.1";

app.get("/api/hello", (req, res) => {
  res.json({
    message: "Hello from Node.js",
    path: req.path,
    timestamp: new Date().toISOString()
  });
});

app.get("/api/status", (req, res) => {
  res.json({
    status: "ok",
    service: "node-backend"
  });
});

app.get("/api/echo-headers", (req, res) => {
  res.json({
    headers: req.headers
  });
});

app.use((req, res) => {
  res.status(404).json({
    error: "Not found in Node app",
    path: req.path
  });
});

app.listen(PORT, HOST, () => {
  console.log(`Node app listening at http://${HOST}:${PORT}`);
});
