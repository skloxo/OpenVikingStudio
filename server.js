import http from 'http';
import fs from 'fs';
import path from 'path';

const PORT = process.env.PORT || 1936;
const BACKEND_PORT = process.env.BACKEND_PORT || 1933;
const DIST_DIR = '/home/skloxo/.local/lib/python3.12/site-packages/openviking/web_studio/dist';
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

const SCRIPT_INJECTION = `
<script>
(function() {
  try {
    const conn = {
      adminApiKey: '${ROOT_API_KEY}',
      apiKey: '${ROOT_API_KEY}',
      role: 'root',
      baseUrl: window.location.origin
    };
    localStorage.setItem('ov_console_connection', JSON.stringify(conn));
  } catch(e) {
    console.error(e);
  }
})();
</script>
`;

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
      version: "0.4.10",
      auth_mode: "dev",
      role: "root",
      role_name: "root",
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

  // Strip /studio prefix for file lookup if present
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
      if (ext === '.html') {
        let htmlStr = content.toString('utf-8');
        if (htmlStr.includes('<head>')) {
          htmlStr = htmlStr.replace('<head>', `<head>${SCRIPT_INJECTION}`);
        } else {
          htmlStr = SCRIPT_INJECTION + htmlStr;
        }
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(htmlStr, 'utf-8');
      } else {
        res.writeHead(200, { 'Content-Type': contentType });
        res.end(content);
      }
    }
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`100% Pure Official 1933 OpenViking Studio running on http://localhost:${PORT}/studio/home`);
});
