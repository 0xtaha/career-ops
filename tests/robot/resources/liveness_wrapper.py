#!/usr/bin/env python3
"""CLI shim for classify_liveness — used by RF suite 06.

Usage: python liveness_wrapper.py '<json>'
Output: JSON with {result, reason}
"""
import json
import sys

from career_ops_core.scripts.liveness_core import classify_liveness

payload = json.loads(sys.argv[1])
result = classify_liveness(
    status=payload.get("status", 0),
    final_url=payload.get("finalUrl", ""),
    body_text=payload.get("bodyText", ""),
    apply_controls=payload.get("applyControls", []),
)
print(json.dumps({"result": result.result, "reason": result.reason}))
