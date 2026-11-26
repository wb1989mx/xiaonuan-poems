#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
离线验收：确认 Service Worker 装上了、缓存齐了，断网后还能打开页面。

做法：
  1. 连上一个已启动的无头 Chrome（--remote-debugging-port）
  2. 等 navigator.serviceWorker.controller 出现
  3. 读 caches 里 nuanshi-v1 的条目数
  4. Network.emulateNetworkConditions 切离线 → reload → 截图

用法：
  python test_offline.py <url> <debug_port> <out_png>
"""

import base64
import json
import sys
import time
import urllib.request

import websocket


def http_json(port, path):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))


class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=30)
        self.id = 0

    def call(self, method, params=None):
        self.id += 1
        payload = {"id": self.id, "method": method, "params": params or {}}
        self.ws.send(json.dumps(payload))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.id:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def eval(self, expr, await_promise=False):
        res = self.call(
            "Runtime.evaluate",
            {"expression": expr, "returnByValue": True, "awaitPromise": await_promise},
        )
        return res.get("result", {}).get("value")


def main():
    url, port, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    targets = http_json(port, "/json/list")
    page = next(t for t in targets if t["type"] == "page")
    cdp = CDP(page["webSocketDebuggerUrl"])
    cdp.call("Page.enable")
    cdp.call("Runtime.enable")
    cdp.call("Network.enable")

    # 等 controller 就位（最多 20 秒）
    ok = False
    for _ in range(40):
        if cdp.eval("!!(navigator.serviceWorker && navigator.serviceWorker.controller)"):
            ok = True
            break
        time.sleep(0.5)
    print("SW 控制页面：", ok)

    count = cdp.eval(
        "caches.open('nuanshi-v1').then(c => c.keys()).then(k => k.length)",
        await_promise=True,
    )
    print("缓存条目数：", count)

    # 切离线
    cdp.call(
        "Network.emulateNetworkConditions",
        {
            "offline": True,
            "latency": 0,
            "downloadThroughput": 0,
            "uploadThroughput": 0,
        },
    )
    cdp.call("Page.navigate", {"url": url})
    time.sleep(6)

    title = cdp.eval("document.title")
    body_len = cdp.eval("document.body ? document.body.innerText.length : -1")
    print("离线后 title：", title, "| 正文字符数：", body_len)

    shot = cdp.call("Page.captureScreenshot", {"captureBeyondViewport": False})
    with open(out, "wb") as fh:
        fh.write(base64.b64decode(shot["data"]))
    print("截图已存：", out)


if __name__ == "__main__":
    main()
