import http from 'http';
import fs from 'fs';
import path from 'path';

const PORT = process.env.PORT || 1936;
const BACKEND_PORT = process.env.BACKEND_PORT || 1933;
const DIST_DIR = '/home/skloxo/.local/lib/python3.12/site-packages/openviking/web_studio/dist.bak';
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

  function moveHeaderControlsToSidebar() {
    // 1. Remove top-right GitHub link and hide top-right theme toggle in header
    const headerLinks = Array.from(document.querySelectorAll('header a'));
    headerLinks.forEach(a => {
      if (a.href && a.href.includes('github.com')) {
        a.style.display = 'none';
      }
    });

    const headerButtons = Array.from(document.querySelectorAll('header button'));
    const themeBtn = headerButtons.find(b => !b.textContent.includes('EN') && !b.textContent.includes('中'));
    const langBtn = headerButtons.find(b => b.textContent && (b.textContent.includes('EN') || b.textContent.includes('中')));

    // Hide header buttons
    if (themeBtn) themeBtn.style.display = 'none';
    if (langBtn) langBtn.style.display = 'none';
    if (langBtn && langBtn.parentElement) {
      langBtn.parentElement.style.display = 'none';
    }

    // 2. Find Sidebar item "连接与身份"
    const sidebarElements = Array.from(document.querySelectorAll('aside *, nav *, [class*="sidebar"] *'));
    const connItem = sidebarElements.find(el => el.children.length === 0 && el.textContent && el.textContent.trim().includes('连接与身份'));

    if (connItem) {
      let connRow = connItem;
      while (connRow && connRow.parentElement && !['ASIDE', 'NAV', 'BODY'].includes(connRow.parentElement.tagName)) {
        if (connRow.tagName === 'A' || connRow.tagName === 'BUTTON' || (connRow.classList && connRow.classList.contains('flex'))) {
          break;
        }
        connRow = connRow.parentElement;
      }

      if (connRow && !document.getElementById('v100-injected-controls')) {
        const wrapper = document.createElement('div');
        wrapper.id = 'v100-injected-controls';
        wrapper.className = 'px-3 py-2.5 my-2 rounded-xl bg-slate-200/50 border border-slate-200/80 flex flex-col gap-2 shadow-2xs font-sans text-xs';

        // Control row with Language Pill & Theme Button
        const ctrlRow = document.createElement('div');
        ctrlRow.className = 'flex items-center justify-between w-full';

        const langBox = document.createElement('div');
        langBox.className = 'flex items-center gap-1 bg-white px-2 py-1 rounded-lg border border-slate-200/60 shadow-2xs font-medium text-slate-700 cursor-pointer';
        langBox.innerHTML = '<span class="text-[11px]">中 / EN</span>';
        langBox.onclick = () => { if (langBtn) langBtn.click(); };

        const themeBox = document.createElement('div');
        themeBox.className = 'p-1 rounded-lg hover:bg-white text-slate-600 cursor-pointer transition';
        themeBox.innerHTML = '<span class="text-sm">🌙</span>';
        themeBox.onclick = () => { if (themeBtn) themeBtn.click(); };

        ctrlRow.appendChild(langBox);
        ctrlRow.appendChild(themeBox);

        // Version Row
        const verRow = document.createElement('div');
        verRow.className = 'flex items-center justify-between w-full pt-2 border-t border-slate-200/60 font-mono text-[11px] font-semibold text-slate-600';
        verRow.innerHTML = '<span>系统版本</span><span class="bg-blue-600 text-white px-1.5 py-0.5 rounded text-[10px] font-bold">V1.0.0</span>';

        wrapper.appendChild(ctrlRow);
        wrapper.appendChild(verRow);

        if (connRow.parentElement) {
          connRow.parentElement.insertBefore(wrapper, connRow);
        }
      }
    }
  }

  window.addEventListener('DOMContentLoaded', () => {
    moveHeaderControlsToSidebar();
    const obs = new MutationObserver(moveHeaderControlsToSidebar);
    obs.observe(document.body, { childList: true, subtree: true });
    setTimeout(moveHeaderControlsToSidebar, 300);
    setTimeout(moveHeaderControlsToSidebar, 1000);
  });
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
  console.log(`1933 Official 100% Perfect UI with V1.0.0 Controls in Sidebar on http://localhost:${PORT}/studio/home`);
});
