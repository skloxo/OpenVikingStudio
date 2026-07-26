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

  function fixV100UIAndInteractivity() {
    const header = document.querySelector('header');
    if (!header) return;

    const headerLinks = Array.from(header.querySelectorAll('a'));
    const headerButtons = Array.from(header.querySelectorAll('button'));

    // 1. Completely hide top-right GitHub link
    headerLinks.forEach(a => {
      if (a.href && a.href.includes('github.com')) {
        a.style.display = 'none';
      }
    });

    // 2. Find original language & theme buttons in top-right header
    const langBtn = headerButtons.find(b => b.textContent && (b.textContent.includes('EN') || b.textContent.includes('中')));
    const themeBtn = headerButtons.find(b => b !== langBtn && (b.querySelector('svg') || b.getAttribute('aria-label') || b.className.includes('theme') || b.className.includes('mode')));

    // Hide original header buttons visually so top-right is clean, but keep in DOM for React events
    if (langBtn) {
      langBtn.style.opacity = '0';
      langBtn.style.pointerEvents = 'none';
      langBtn.style.position = 'absolute';
      langBtn.style.right = '-9999px';
    }
    if (themeBtn) {
      themeBtn.style.opacity = '0';
      themeBtn.style.pointerEvents = 'none';
      themeBtn.style.position = 'absolute';
      themeBtn.style.right = '-9999px';
    }

    // 3. Locate Sidebar item "连接与身份"
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
        wrapper.style.cssText = 'padding: 10px 12px; margin: 8px 0 12px 0; border-radius: 10px; background: rgba(241, 245, 249, 0.9); border: 1px solid rgba(226, 232, 240, 0.8); display: flex; flex-direction: column; gap: 8px; font-family: sans-serif; font-size: 12px;';

        const ctrlRow = document.createElement('div');
        ctrlRow.style.cssText = 'display: flex; align-items: center; justify-content: space-between; width: 100%;';

        // Interactive Language Box
        const langBox = document.createElement('button');
        langBox.type = 'button';
        langBox.style.cssText = 'display: flex; align-items: center; gap: 4px; background: #ffffff; padding: 4px 10px; border-radius: 6px; border: 1px solid #cbd5e1; font-weight: 600; color: #334155; font-size: 11px; cursor: pointer; border-style: solid;';
        langBox.innerHTML = '<span id="v100-lang-txt">' + (langBtn ? langBtn.textContent.trim() : '中 / EN') + '</span>';
        langBox.onclick = (e) => {
          e.preventDefault();
          e.stopPropagation();
          if (langBtn) {
            langBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
          }
        };

        // Interactive Theme Box
        const themeBox = document.createElement('button');
        themeBox.type = 'button';
        themeBox.style.cssText = 'padding: 4px 8px; border-radius: 6px; background: transparent; border: none; font-size: 14px; cursor: pointer; color: #475569; display: flex; align-items: center; justify-content: center;';
        themeBox.innerHTML = '<span>🌙 / ☀️</span>';
        themeBox.onclick = (e) => {
          e.preventDefault();
          e.stopPropagation();
          if (themeBtn) {
            themeBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
          }
        };

        ctrlRow.appendChild(langBox);
        ctrlRow.appendChild(themeBox);

        // Version Badge Row
        const verRow = document.createElement('div');
        verRow.style.cssText = 'display: flex; align-items: center; justify-content: space-between; width: 100%; font-size: 11px; font-weight: 600; color: #334155; padding-top: 6px; border-top: 1px solid #e2e8f0; font-family: monospace;';
        verRow.innerHTML = '<span>系统版本</span><span style="background: #2563eb; color: #ffffff; padding: 2px 6px; border-radius: 4px; font-weight: 700;">V1.0.0</span>';

        wrapper.appendChild(ctrlRow);
        wrapper.appendChild(verRow);

        if (connRow.parentElement) {
          connRow.parentElement.insertBefore(wrapper, connRow);
        }
      } else if (document.getElementById('v100-lang-txt') && langBtn) {
        document.getElementById('v100-lang-txt').textContent = langBtn.textContent.trim();
      }
    }
  }

  window.addEventListener('DOMContentLoaded', () => {
    fixV100UIAndInteractivity();
    const obs = new MutationObserver(fixV100UIAndInteractivity);
    obs.observe(document.body, { childList: true, subtree: true });
    setTimeout(fixV100UIAndInteractivity, 300);
    setTimeout(fixV100UIAndInteractivity, 1000);
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
  console.log(`1933 Official 100% Perfect UI with Interactive V1.0.0 Controls in Sidebar on http://localhost:${PORT}/studio/home`);
});
