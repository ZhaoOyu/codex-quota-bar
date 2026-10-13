"""Deterministic process-level protocol fixture. Contains no real credentials."""
import json
import sys
import time

mode = sys.argv[1] if len(sys.argv) > 1 else "ok"
initialized = False
for line in sys.stdin:
    request = json.loads(line)
    method = request["method"]
    if method == "initialize":
        assert request["params"]["clientInfo"]["name"] == "codex_quota_bar"
        result = {"userAgent": "fixture"}
    elif method == "initialized":
        initialized = True
        continue
    elif method == "account/rateLimits/read":
        assert initialized
        if mode == "timeout":
            time.sleep(10)
        if mode == "exit":
            sys.exit(0)
        if mode == "error":
            print(json.dumps({"id": request["id"], "error": {"message": "secret-token-do-not-display"}}), flush=True)
            continue
        print("non-json output", flush=True)
        print(json.dumps({"method": "account/updated", "params": {}}), flush=True)
        result = {"rateLimits": {
            "primary": {"usedPercent": 22, "windowDurationMins": 300, "resetsAt": 2000000000},
            "secondary": {"usedPercent": 38, "windowDurationMins": 10080, "resetsAt": 2000500000}}}
    else:
        raise AssertionError(f"Unexpected method: {method}")
    print(json.dumps({"id": request["id"], "result": result}), flush=True)

