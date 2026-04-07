import express from "express";
import { createServer as createViteServer } from "vite";
import path from "path";
import { fileURLToPath } from "url";
import net from "net";
import ping from "ping";
// speedtest-net removed due to native dependency issues

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json());

  // Mock database
  let ipsToMonitor = [
    { id: 1, ip: "8.8.8.8", label: "Google DNS", port: 53 },
    { id: 2, ip: "1.1.1.1", label: "Cloudflare DNS", port: 53 },
    { id: 3, ip: "github.com", label: "GitHub", port: 443 }
  ];

  // API: Check Ping Status
  app.get("/api/status", async (req, res) => {
    const results = await Promise.all(
      ipsToMonitor.map(async (item) => {
        try {
          const res = await ping.promise.probe(item.ip, {
            timeout: 2,
            extra: ["-c", "1"]
          });
          return { ...item, status: res.alive ? "online" : "offline", ping: res.time };
        } catch (error) {
          return { ...item, status: "offline", ping: null };
        }
      })
    );
    res.json(results);
  });

  // API: Add IP
  app.post("/api/add_ip", (req, res) => {
    const { ip, label, port } = req.body;
    if (ip) {
      const newItem = {
        id: Date.now(),
        ip,
        label: label || "Novo Host",
        port: parseInt(port) || 80
      };
      ipsToMonitor.push(newItem);
      res.json({ status: "success", item: newItem });
    } else {
      res.status(400).json({ status: "error" });
    }
  });

  // API: Speedtest (Mocked for environment compatibility)
  app.get("/api/speedtest", async (req, res) => {
    try {
      // Simulating a speedtest delay
      await new Promise(resolve => setTimeout(resolve, 3000));
      res.json({
        download: (Math.random() * 100 + 50).toFixed(2),
        upload: (Math.random() * 50 + 20).toFixed(2),
        ping: Math.floor(Math.random() * 20 + 5),
        server: "Vercel Edge Node (Simulated)"
      });
    } catch (error) {
      res.status(500).json({ error: "Speedtest failed" });
    }
  });

  // API: Traceroute (Simulated)
  app.get("/api/traceroute/:host", (req, res) => {
    const host = req.params.host;
    res.json({
      host,
      hops: [
        { hop: 1, ip: "10.0.0.1", ms: 0.5 },
        { hop: 2, ip: "172.16.0.1", ms: 2.1 },
        { hop: 3, ip: "8.8.8.8", ms: 15.4 }
      ],
      note: "Traceroute simulado para ambiente de demonstração."
    });
  });

  // API: Delete IP
  app.delete("/api/delete_ip/:id", (req, res) => {
    const id = parseInt(req.params.id);
    const initialLength = ipsToMonitor.length;
    ipsToMonitor = ipsToMonitor.filter(item => item.id !== id);
    
    if (ipsToMonitor.length < initialLength) {
      res.json({ status: "success" });
    } else {
      res.status(404).json({ status: "error", message: "IP not found" });
    }
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });
}

startServer();
