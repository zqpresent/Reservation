import argparse
import sys
import time
from uuid import uuid4

import httpx


def _ok(msg: str):
    print(f"[PASS] {msg}")


def _fail(msg: str):
    print(f"[FAIL] {msg}")


def main() -> int:
    parser = argparse.ArgumentParser(description="测试已启动的 Agent 服务")
    parser.add_argument("--agent-url", default="http://localhost:8100", help="Agent 服务地址")
    parser.add_argument("--student-id", type=int, default=123, help="测试用 student_id")
    parser.add_argument("--timeout", type=float, default=20.0, help="请求超时时间（秒）")
    args = parser.parse_args()

    session_id = f"test-{uuid4().hex[:8]}"
    base = args.agent_url.rstrip("/")
    client = httpx.Client(timeout=args.timeout)
    has_error = False

    print("=== Agent 服务联调测试开始 ===")
    print(f"Agent URL: {base}")
    print(f"Student ID: {args.student_id}")
    print(f"Session ID: {session_id}")
    print("")

    # 1) 健康检查
    try:
        resp = client.get(f"{base}/health")
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "ok":
            _ok(f"/health -> {data}")
        else:
            _fail(f"/health 状态异常: {data}")
            has_error = True
    except Exception as exc:
        _fail(f"/health 请求失败: {exc}")
        return 1

    # 2) 就绪检查
    try:
        resp = client.get(f"{base}/ready")
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "ok":
            _ok(f"/ready -> {data}")
        else:
            _fail(f"/ready 未就绪: {data}")
            has_error = True
    except Exception as exc:
        _fail(f"/ready 请求失败: {exc}")
        has_error = True

    # 3) Chat 基本可用性
    payload = {
        "session_id": session_id,
        "student_id": args.student_id,
        "message": "请调用 my_reservations 工具查询我当前预约，并用一句话返回结果。",
    }
    try:
        start = time.time()
        resp = client.post(f"{base}/chat", json=payload)
        elapsed = time.time() - start
        resp.raise_for_status()
        data = resp.json()
        reply = (data.get("reply") or "").strip()
        if reply:
            _ok(f"/chat 返回成功（{elapsed:.2f}s）")
            print("----- reply -----")
            print(reply)
            print("-----------------")
        else:
            _fail("/chat 返回为空")
            has_error = True
    except Exception as exc:
        _fail(f"/chat 请求失败: {exc}")
        has_error = True

    client.close()
    print("")
    if has_error:
        print("=== 测试结束：存在失败项 ===")
        return 1
    print("=== 测试结束：全部通过 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
