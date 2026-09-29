"""
memory.py - IncidentPilot's Hindsight memory layer.

Uses the official `hindsight-client` SDK (https://hindsight.vectorize.io/sdks/python).

Design rule: NO silent fake memory. If Hindsight is unreachable we raise
MemoryUnavailable and the UI shows it.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

BANK_ID = os.getenv("HINDSIGHT_BANK_ID", "incident-pilot-prod")
BASE_URL = os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io")

BANK_MISSION = (
    "You are the institutional memory of a site-reliability team. Remember past "
    "production incidents: symptoms, affected services, root causes, the exact fix "
    "that worked, fixes that FAILED, and how long resolution took. Prefer concrete "
    "commands, config values and service names over generalities."
)


class MemoryUnavailable(RuntimeError):
    """Raised when Hindsight cannot be reached / authenticated."""


@dataclass
class RecalledMemory:
    text: str
    kind: str = "unknown"          # world / experience / observation
    score: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    document_id: Optional[str] = None


class IncidentMemory:
    def __init__(self, api_key: Optional[str] = None, bank_id: str = BANK_ID):
        api_key = api_key or os.getenv("HINDSIGHT_API_KEY")
        if not api_key:
            raise MemoryUnavailable("HINDSIGHT_API_KEY is not set")
        self.bank_id = bank_id
        self.client = Hindsight(base_url=BASE_URL, api_key=api_key, timeout=60.0)
        self._ensure_bank()

    def close(self) -> None:
        try:
            self.client.close()
        except Exception:
            pass

    # ---- setup -----------------------------------------------------------
    def _ensure_bank(self) -> None:
        """Create the bank with an SRE mission. Safe to call repeatedly."""
        try:
            self.client.create_bank(bank_id=self.bank_id, name="IncidentPilot", mission=BANK_MISSION)
        except Exception as e:  # "already exists" is fine; auth/network errors are not
            msg = str(e).lower()
            if any(w in msg for w in ("401", "403", "unauthor", "forbidden", "connect", "timeout")):
                raise MemoryUnavailable(f"Cannot reach Hindsight: {e}") from e

    # ---- retain ----------------------------------------------------------
    def retain_incident(
        self,
        incident_id: str,
        summary: str,
        root_cause: str,
        fix_applied: str,
        outcome: str = "resolved",
        service: str = "",
        minutes_to_resolve: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """Store a post-mortem. `outcome` may be 'resolved' or 'fix_failed' -
        remembering what did NOT work is where memory beats a runbook wiki."""
        content = (
            f"Incident {incident_id} ({outcome}).\n"
            f"Service: {service or 'unspecified'}\n"
            f"Symptoms: {summary}\n"
            f"Root cause: {root_cause}\n"
            f"Fix applied: {fix_applied}\n"
            + (f"Time to resolve: {minutes_to_resolve} minutes\n" if minutes_to_resolve else "")
        )
        try:
            self.client.retain(
                bank_id=self.bank_id,
                content=content,
                context="Production incident post-mortem",
                document_id=incident_id,          # re-retaining the same id updates it
                tags=(tags or []) + [outcome],
                metadata={"incident_id": incident_id, "service": service or "unspecified"},
            )
        except Exception as e:
            raise MemoryUnavailable(f"Retain failed: {e}") from e

    def retain_batch(self, incidents: List[dict]) -> int:
        n = 0
        for inc in incidents:
            self.retain_incident(**inc)
            n += 1
        return n

    # ---- recall ----------------------------------------------------------
    def recall(self, query: str, budget: str = "mid", max_tokens: int = 2048) -> List[RecalledMemory]:
        try:
            resp = self.client.recall(
                bank_id=self.bank_id, query=query, budget=budget, max_tokens=max_tokens
            )
        except Exception as e:
            raise MemoryUnavailable(f"Recall failed: {e}") from e
        out = []
        for r in resp.results or []:
            out.append(
                RecalledMemory(
                    text=r.text,
                    kind=getattr(r, "type", None) or "unknown",
                    tags=list(r.tags or []),
                    document_id=r.document_id,
                )
            )
        return out

    # ---- reflect ---------------------------------------------------------
    def reflect(self, question: str, budget: str = "mid") -> str:
        """Ask Hindsight to REASON over memory (not just retrieve), e.g.
        'Which service fails most often and what usually fixes it?'"""
        try:
            resp = self.client.reflect(bank_id=self.bank_id, query=question, budget=budget)
            return resp.text or ""
        except Exception as e:
            raise MemoryUnavailable(f"Reflect failed: {e}") from e