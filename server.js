import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = process.env.PORT || 1936;
const BACKEND_PORT = process.env.BACKEND_PORT || 1933;
const DIST_DIR = path.join(__dirname, 'dist');
const ROOT_API_KEY = process.env.ROOT_API_KEY || 'sk-fbb21afbe35d09986ac6f66ca91f62f44ee6b2536319be7347759f02de8f6227';

const MIME_TYPES = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.ico': 'image/x-icon',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2'
};

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);

  // Proxy /api/ to backend :1933
  if (url.pathname.startsWith('/api/')) {
    const proxyHeaders = { 
      ...req.headers, 
      host: `127.0.0.1:${BACKEND_PORT}`,
      'x-api-key': ROOT_API_KEY,
      'authorization': `Bearer ${ROOT_API_KEY}`
    };

    const options = {
      hostname: '127.0.0.1',
      port: BACKEND_PORT,
      path: req.url,
      method: req.method,
      headers: proxyHeaders
    };

    const proxyReq = http.request(options, (proxyRes) => {
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res, { end: true });
    });

    proxyReq.on('error', (err) => {
      res.writeHead(502, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Bad Gateway', message: err.message }));
    });

    req.pipe(proxyReq, { end: true });
    return;
  }

  // Handle /health endpoint
  if (url.pathname === '/health' || url.pathname === '/api/v1/health') {
    const healthData = {
      status: "ok",
      healthy: true,
      version: "1.0.0",
      auth_mode: "dev",
      role: "root",
      is_admin: true,
      is_root: true,
      account_id: "default"
    };
    const body = JSON.stringify(healthData);
    res.writeHead(200, {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(body)
    });
    res.end(body);
    return;
  }

  // Strip /studio prefix if present
  let reqPath = url.pathname;
  if (reqPath.startsWith('/studio')) {
    reqPath = reqPath.replace(/^\/studio/, '') || '/';
  }

  let filePath = path.join(DIST_DIR, reqPath);

  if (reqPath === '/' || reqPath === '' || !fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    filePath = path.join(DIST_DIR, 'index.html');
  }

  const ext = path.extname(filePath);
  const contentType = MIME_TYPES[ext] || 'application/octet-stream';

  fs.readFile(filePath, (err, content) => {
    if (err) {
      res.writeHead(500);
      res.end(`Server Error: ${err.code}`);
    } else {
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content);
    }
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`OpenViking Studio V1.0.0 Refactored server running on http://localhost:${PORT}/studio/home`);
});
