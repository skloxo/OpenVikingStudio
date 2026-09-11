import subprocess

py_script = """
import subprocess
import os

test_mjs = '''
import pluginObj from "file:///C:/Users/Skl/.openviking/mimo-openviking-plugin.mjs";

async function test() {
  const hooks = await pluginObj.server();
  console.log("Registered hook names:", Object.keys(hooks));

  if (hooks["experimental.chat.messages.transform"]) {
    const fakeMessages = [
      {
        info: { role: "user", id: "msg-1" },
        parts: [
          { type: "text", text: "在 OpenViking 官方大模型基准评测中，Mac Studio M3 Ultra 实机直连的 Qwen 3.8 Flash Next 综合得分是多少？" }
        ]
      }
    ];
    await hooks["experimental.chat.messages.transform"]({}, { messages: fakeMessages });
    console.log("TRANSFORMED_PARTS_COUNT:", fakeMessages[0].parts.length);
    for (const p of fakeMessages[0].parts) {
      console.log("PART:", p.text.slice(0, 150));
    }
  }
}
test().catch(console.error);
'''

with open(r'C:\\Users\\Skl\\.openviking\\test_sim_hook.mjs', 'w', encoding='utf-8') as f:
    f.write(test_mjs)

my_env = os.environ.copy()
my_env['ELECTRON_RUN_AS_NODE'] = '1'
res = subprocess.run([r'C:\\Program Files\\Xiaomi MiMo\\Xiaomi MiMo.exe', r'C:\\Users\\Skl\\.openviking\\test_sim_hook.mjs'], capture_output=True, text=True, encoding='utf-8', errors='replace', env=my_env)
print("STDOUT:", res.stdout)
print("STDERR:", res.stderr)
"""
import base64
py_b64 = base64.b64encode(py_script.encode("utf-8")).decode("ascii")
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
