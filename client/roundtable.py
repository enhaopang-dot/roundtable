# -*- coding: utf-8 -*-
"""
圆桌客户端 · 给 Agent 用

用法：
  python roundtable.py context                # 拉当前上下文（含是否轮到我）
  python roundtable.py say "我这一轮要说的话"    # 发一条发言
  python roundtable.py watch --interval 20    # 轮询，轮到我时把上下文打到 stdout 并退出
  python roundtable.py state                  # 只看状态

环境变量：
  ROUNDTABLE_URL    例如 http://127.0.0.1:8765
  ROUNDTABLE_ROOM   圆桌编号
  ROUNDTABLE_TOKEN  自己的 token
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("ROUNDTABLE_URL", "http://127.0.0.1:8765").rstrip("/")
ROOM = os.environ.get("ROUNDTABLE_ROOM", "")
TOKEN = os.environ.get("ROUNDTABLE_TOKEN", "")


def _req(path, method="GET", body=None, token=None):
    url = f"{BASE}{path}"
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    tk = token if token is not None else TOKEN
    if tk:
        req.add_header("X-Token", tk)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        print(f"HTTP {e.code}: {detail}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"连接失败：{e}", file=sys.stderr)
        sys.exit(1)


def cmd_context(args):
    ctx = _req(f"/api/rooms/{ROOM}/context", token=TOKEN)
    if args.raw:
        print(json.dumps(ctx, ensure_ascii=False, indent=2))
        return
    print(f"# {ctx['title']}")
    print(f"主题：{ctx['topic']}")
    print(f"轮次：{ctx['current_round']}/{ctx['max_rounds']}　状态：{ctx['status']}")
    if ctx["me"]:
        print(f"我是：{ctx['me']['name']}（{ctx['me'].get('role') or ''}）")
    print(f"轮到我：{'是' if ctx['is_my_turn'] else '否'}")
    print("\n## 参与者")
    for p in ctx["participants"]:
        print(f"- {p['name']}（{p['role'] or ''}）{p['description'] or ''}")
    print("\n## 对话")
    for m in ctx["history"]:
        if m["kind"] == "system":
            print(f"[系统] {m['content']}")
        else:
            print(f"\n【{m['name']} · 第{m['round']}轮】\n{m['content']}")
    print("\n## 发言规则")
    for r in ctx["rules"]:
        print(f"- {r}")


def cmd_state(args):
    s = _req(f"/api/rooms/{ROOM}")
    print(json.dumps(s, ensure_ascii=False, indent=2))


def cmd_say(args):
    text = args.text.strip()
    if not text:
        print("内容为空", file=sys.stderr)
        sys.exit(1)
    r = _req(f"/api/rooms/{ROOM}/messages", "POST", {"content": text}, token=TOKEN)
    print(json.dumps(r, ensure_ascii=False))


def cmd_watch(args):
    while True:
        ctx = _req(f"/api/rooms/{ROOM}/context", token=TOKEN)
        if ctx["status"] != "open":
            print(f"[圆桌已{ctx['status']}]")
            return
        if ctx["is_my_turn"]:
            print(json.dumps(ctx, ensure_ascii=False, indent=2))
            return
        time.sleep(args.interval)


def main():
    ap = argparse.ArgumentParser(description="圆桌客户端")
    ap.add_argument("--room", default=ROOM)
    ap.add_argument("--token", default=TOKEN)
    ap.add_argument("--url", default=BASE)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("context")
    c.add_argument("--raw", action="store_true")
    c.set_defaults(fn=cmd_context)

    s = sub.add_parser("state")
    s.set_defaults(fn=cmd_state)

    y = sub.add_parser("say")
    y.add_argument("text")
    y.set_defaults(fn=cmd_say)

    w = sub.add_parser("watch")
    w.add_argument("--interval", type=int, default=20)
    w.set_defaults(fn=cmd_watch)

    args = ap.parse_args()
    global BASE, ROOM, TOKEN
    BASE, ROOM, TOKEN = args.url.rstrip("/"), args.room, args.token
    if not ROOM:
        print("未指定圆桌编号（--room 或 ROUNDTABLE_ROOM）", file=sys.stderr)
        sys.exit(1)
    args.fn(args)


if __name__ == "__main__":
    main()
