"""
Lighthouse audit runner (CLI integration).

Requires Node.js and Lighthouse installed globally or via npx.

Subprocess: ``npx lighthouse <url> --output=json --quiet`` (or ``lighthouse`` on PATH).
"""
from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any, Dict, List

import structlog

logger = structlog.get_logger()


class LighthouseError(Exception):
    """Raised when Lighthouse CLI fails or returns unusable output."""


def _score_to_hundred(raw: Any) -> float:
    if raw is None:
        return 0.0
    try:
        s = float(raw)
    except (TypeError, ValueError):
        return 0.0
    if s <= 1.0:
        return round(s * 100, 2)
    return round(min(s, 100.0), 2)


def _normalize(lhr: Dict[str, Any], url: str) -> Dict[str, Any]:
    """
    Normalize raw Lighthouse JSON into scores and URL (used by tests and helpers).
    """
    cats = lhr.get("categories") or {}
    scores = {
        "performance": _score_to_hundred((cats.get("performance") or {}).get("score")),
        "seo": _score_to_hundred((cats.get("seo") or {}).get("score")),
        "accessibility": _score_to_hundred((cats.get("accessibility") or {}).get("score")),
        "best_practices": _score_to_hundred((cats.get("best-practices") or {}).get("score")),
    }
    return {"scores": scores, "url": url}


def _severity_for_audit(audit: Dict[str, Any]) -> str:
    score = audit.get("score")
    smode = audit.get("scoreDisplayMode") or ""
    if smode in ("notApplicable", "manual"):
        return "low"
    if score is None:
        return "medium"
    if score == 0:
        return "high"
    if isinstance(score, (int, float)) and score < 0.5:
        return "medium"
    return "low"


def _issues_for_category(lhr: Dict[str, Any], category_id: str) -> List[Dict[str, Any]]:
    cat = (lhr.get("categories") or {}).get(category_id) or {}
    refs = cat.get("auditRefs") or []
    audits = lhr.get("audits") or {}
    issues: List[Dict[str, Any]] = []
    for ref in refs:
        aid = ref.get("id")
        if not aid:
            continue
        audit = audits.get(aid) or {}
        score = audit.get("score")
        smode = audit.get("scoreDisplayMode") or ""
        if smode in ("notApplicable", "informative", "manual") and score is None:
            continue
        if score is not None and score >= 1:
            continue
        title = audit.get("title") or aid
        desc = audit.get("description") or audit.get("explanation") or ""
        if isinstance(desc, str) and len(desc) > 500:
            desc = desc[:500]
        issues.append(
            {
                "severity": _severity_for_audit(audit),
                "title": str(title),
                "description": str(desc) if desc else "",
            }
        )
    return issues


def run_audit(url: str) -> Dict[str, Any]:
    """
    Run Lighthouse against ``url`` and return normalized results.

    Returns dict with ``scores``, ``issues``, ``raw_summary``.
    """
    lighthouse_bin = shutil.which("lighthouse")
    npx_bin = shutil.which("npx")
    if lighthouse_bin:
        cmd = [
            lighthouse_bin,
            url,
            "--output=json",
            "--quiet",
            "--chrome-flags=--headless=new",
        ]
    elif npx_bin:
        cmd = [
            npx_bin,
            "--yes",
            "lighthouse",
            url,
            "--output=json",
            "--quiet",
            "--chrome-flags=--headless=new",
        ]
    else:
        raise LighthouseError(
            "Lighthouse CLI not found. Install Node.js and run: npm install -g lighthouse "
            "or ensure `npx` is on PATH."
        )

    logger.info("Running Lighthouse", cmd_preview=" ".join(cmd[:4]), url=url)
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise LighthouseError("Lighthouse timed out") from e
    except OSError as e:
        raise LighthouseError(f"Failed to spawn Lighthouse: {e}") from e

    out = proc.stdout.strip()
    if proc.returncode != 0 and not out:
        err = (proc.stderr or "").strip() or "unknown error"
        raise LighthouseError(f"Lighthouse exited {proc.returncode}: {err[:500]}")

    try:
        lhr = json.loads(out)
    except json.JSONDecodeError as e:
        raise LighthouseError("Lighthouse did not return valid JSON") from e

    norm = _normalize(lhr, url)
    scores = norm["scores"]

    perf_i = _issues_for_category(lhr, "performance")
    seo_i = _issues_for_category(lhr, "seo")
    a11y_i = _issues_for_category(lhr, "accessibility")
    bp_i = _issues_for_category(lhr, "best-practices")
    merged_bp = a11y_i + bp_i

    issues: Dict[str, List[Dict[str, Any]]] = {
        "performance": perf_i,
        "seo": seo_i,
        "accessibility": a11y_i,
        "best_practices": merged_bp,
    }

    raw_summary = {
        "lighthouseVersion": lhr.get("lighthouseVersion"),
        "requestedUrl": lhr.get("requestedUrl"),
        "finalUrl": lhr.get("finalUrl"),
        "fetchTime": lhr.get("fetchTime"),
        "userAgent": (lhr.get("userAgent") or "")[:200],
    }

    return {
        "scores": scores,
        "issues": issues,
        "raw_summary": raw_summary,
    }
