"""gemini_eval — evaluate a job description using the Gemini API.

Port of gemini-eval.mjs. Requires GEMINI_API_KEY env var.
"""
from __future__ import annotations

import os
import sys

from career_ops_core.config import ProjectConfig


def gemini_eval(cfg: ProjectConfig, jd_text: str) -> None:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set")
        sys.exit(1)

    try:
        import google.generativeai as genai
    except ImportError:
        print("Error: google-generativeai not installed. Run: uv sync")
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-pro")

    # Read modes/_shared.md and modes/oferta.md for the system prompt
    shared = (cfg.root / "modes" / "_shared.md")
    oferta = (cfg.root / "modes" / "oferta.md")
    system_parts = []
    if shared.exists():
        system_parts.append(shared.read_text(encoding="utf-8"))
    if oferta.exists():
        system_parts.append(oferta.read_text(encoding="utf-8"))
    system_prompt = "\n\n---\n\n".join(system_parts) if system_parts else ""

    prompt = f"{system_prompt}\n\n---\n\nJob Description:\n\n{jd_text}" if system_prompt else jd_text

    print("Evaluating with Gemini...\n")
    try:
        response = model.generate_content(prompt)
        print(response.text)
    except Exception as e:
        # Redact API key from error messages
        msg = str(e).replace(api_key, "***")
        print(f"Error: {msg}", file=sys.stderr)
        sys.exit(1)
