"""Smoke test verifying live gateway launch on port 1934."""

import subprocess
import sys
import time
import httpx

def main():
    cmd = [sys.executable, "-m", "openviking_gateway", "--port", "1934"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        # Wait up to 5 seconds for server to start
        url = "http://127.0.0.1:1934/health"
        models_url = "http://127.0.0.1:1934/v1/models"
        ready = False
        for _ in range(15):
            time.sleep(0.4)
            try:
                resp = httpx.get(url, timeout=1.0)
                if resp.status_code == 200:
                    print("✅ /health probe successful:", resp.json())
                    ready = True
                    break
            except Exception:
                pass
        
        if not ready:
            print("❌ Failed to connect to gateway on port 1934")
            sys.exit(1)

        resp2 = httpx.get(models_url, timeout=1.0)
        assert resp2.status_code == 200
        print("✅ /v1/models probe successful:", resp2.json())
        print("🎉 OpenViking Gateway 2.0 live on port 1934 100% verified!")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    main()
