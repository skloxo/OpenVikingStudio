import subprocess, base64

js_script = """
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const home = process.env.USERPROFILE || process.env.HOME || "C:\\Users\\Skl";
const configPath = resolve(home, ".config", "mimocode", "mimocode.jsonc");
const raw = readFileSync(configPath, "utf-8");

const matchApi = raw.match(/"OPENVIKING_API"\\s*:\\s*"([^"]+)"/);
const matchKey = raw.match(/"OPENVIKING_API_KEY"\\s*:\\s*"([^"]+)"/);
const matchPeer = raw.match(/"OPENVIKING_ACTOR_PEER"\\s*:\\s*"([^"]+)"/);

const api = matchApi ? matchApi[1] : "http://127.0.0.1:1933";
const key = matchKey ? matchKey[1] : "";
const peer = matchPeer ? matchPeer[1] : "xiaomimo@3070";

console.log("CONFIG:", { api, peer, key_len: key.length });

const url = `${api.replace(/\\/+$/, "")}/api/v1/search/find`;
const headers = {
  "Content-Type": "application/json",
  "X-OpenViking-Actor-Peer": peer,
  "X-Caller": peer
};
if (key) {
  headers["Authorization"] = `Bearer ${key}`;
}

const query = "在 OpenViking 官方大模型基准评测中，Mac Studio M3 Ultra 实机直连的 Qwen 3.8 Flash Next 综合得分是多少？在 S1 场景中检出的 3 个隐藏架构漏洞具体是哪三个？";

try {
  const res = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify({
      query: query.slice(0, 300),
      limit: 2,
      mode: "fast"
    })
  });
  console.log("STATUS:", res.status);
  const json = await res.json();
  console.log("RESULT:", JSON.stringify(json, null, 2));
} catch (e) {
  console.error("FETCH_ERR:", e);
}
"""

b64 = base64.b64encode(js_script.encode("utf-8")).decode("ascii")

# We can run it using Electron's bundled Node on 3070
py_runner = f"""
import subprocess
import os

os.environ['ELECTRON_RUN_AS_NODE'] = '1'
cmd = [
    r'C:\\Program Files\\Xiaomi MiMo\\Xiaomi MiMo.exe',
    '--input-type=module',
    '-e',
    '''import base64; const code = Buffer.from('{b64}', 'base64').toString('utf-8'); eval(code);'''
]
# We write to a temp file on 3070 and run it with node
import base64
with open(r'C:\\Users\\Skl\\.openviking\\test_fetch.mjs', 'w', encoding='utf-8') as f:
    f.write(base64.b64decode('{b64}').decode('utf-8'))

res = subprocess.run([r'C:\\Program Files\\Xiaomi MiMo\\Xiaomi MiMo.exe', r'C:\\Users\\Skl\\.openviking\\test_fetch.mjs'], capture_output=True)
with open(r'C:\\Users\\Skl\\.openviking\\fetch_debug.txt', 'wb') as f:
    f.write(res.stdout + b'\\n---STDERR---\\n' + res.stderr)
print('WRITTEN_TO_FILE, STDOUT_LEN:', len(res.stdout), 'STDERR_LEN:', len(res.stderr))
"""

py_b64 = base64.b64encode(py_runner.encode("utf-8")).decode("ascii")
cmd = [
    "sshpass", "-p", "Skl3289568",
    "ssh", "-p", "6022",
    "-o", "StrictHostKeyChecking=no",
    "-o", "PubkeyAuthentication=no",
    "-o", "PreferredAuthentications=password",
    "-o", "ConnectTimeout=10",
    "AzureAD\\s@tide.red@8.129.0.26",
    f"C:\\Users\\Skl\\.venv-openviking\\Scripts\\python.exe -c \"import base64; exec(base64.b64decode('{py_b64}'))\""
]
res = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
print(res.stdout)
if res.stderr:
    print("STDERR:", res.stderr)

read_cmd = [
    "sshpass", "-p", "Skl3289568",
    "ssh", "-p", "6022",
    "-o", "StrictHostKeyChecking=no",
    "-o", "PubkeyAuthentication=no",
    "-o", "PreferredAuthentications=password",
    "-o", "ConnectTimeout=10",
    "AzureAD\\s@tide.red@8.129.0.26",
    "type C:\\Users\\Skl\\.openviking\\fetch_debug.txt"
]
res2 = subprocess.run(read_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
print("=== FETCH_DEBUG.TXT ===")
print(res2.stdout)
