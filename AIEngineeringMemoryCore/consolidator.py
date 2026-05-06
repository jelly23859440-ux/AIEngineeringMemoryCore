import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional, List

import httpx
from pydantic import BaseModel, Field

from models import MemoryPacket, EpisodeSummary, EntityRecord, ConfidenceLevel


CONSOLIDATION_SYSTEM_PROMPT = """You are a memory consolidation engine. Your task is to analyze conversation histories and extract structured memories.

You must output a valid JSON object with this structure:
{
  "episodes": [
    {
      "summary_text": "Brief description of what happened in this part of the conversation",
      "confidence": "high",
      "related_entity_names": ["entity1", "entity2"]
    }
  ],
  "entities": [
    {
      "entity_name": "variable_or_concept_name",
      "entity_type": "decision|config|finding|question|other",
      "exact_value": "the precise value or answer",
      "confidence": "high"
    }
  ]
}

Rules:
1. STRIP ALL secrets, API keys, tokens, passwords, and credentials. Replace them with "[REDACTED]".
2. confidence must be one of: "high", "medium", "low"
3. For well-established facts with clear evidence, use "high".
4. For tentative conclusions or partial evidence, use "medium".
5. For speculative or inferred information, use "low".
6. Extract precise, factual entities that could be referenced later.
7. Keep summaries concise (1-3 sentences).
8. Only include meaningful entities and summaries. Skip empty chatter.
"""

FALLBACK_SYSTEM_PROMPT = """You are a conversation summarizer. Create a concise summary of the conversation history below.
Focus on: key decisions made, problems being solved, current task status, and important facts.
Output ONLY the summary text, no JSON formatting, no markdown headers."""


class ManagementAIConfig(BaseModel):
    api_base: str = "http://localhost:11434/v1"
    api_key: str = ""
    model: str = "llama3"
    max_retries: int = 3
    timeout: int = 60
    temperature: float = 0.3


class Consolidator:
    def __init__(self, config: ManagementAIConfig):
        self.config = config
        self._http_client: Optional[httpx.Client] = None

    @property
    def http_client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=self.config.timeout)
        return self._http_client

    def consolidate(self, conversation_history: List[dict]) -> MemoryPacket:
        prompt = self._build_consolidation_prompt(conversation_history)
        response_text = self._call_with_retry(prompt, system_prompt=CONSOLIDATION_SYSTEM_PROMPT)

        try:
            return self._parse_response(response_text)
        except Exception:
            fallback_text = self._call_with_retry(
                self._build_fallback_prompt(conversation_history),
                system_prompt=FALLBACK_SYSTEM_PROMPT,
            )
            return self._fallback_to_plain_summary(fallback_text)

    def summarize_for_consolidation(self, packets_json: str) -> MemoryPacket:
        prompt = f"""You are performing memory consolidation: deduplication, error correction, and index rebuilding.

Below are multiple memory packets that may contain duplicates, contradictions, or outdated information.

{packets_json}

Please merge, correct, and rebuild these into a single clean MemoryPacket JSON following the standard format.
Resolve contradictions by preferring newer entries. Merge duplicate entities.
Output only the JSON."""

        response_text = self._call_with_retry(prompt, system_prompt=CONSOLIDATION_SYSTEM_PROMPT)
        try:
            return self._parse_response(response_text)
        except Exception:
            return MemoryPacket(
                episodes=[EpisodeSummary(summary_text=response_text[:500])]
            )

    def _build_consolidation_prompt(self, history: List[dict]) -> str:
        lines = []
        for entry in history:
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            lines.append(f"[{role}]: {content}")

        history_text = "\n\n".join(lines)

        return f"""Analyze the following conversation history and extract structured memories.

CONVERSATION HISTORY:
{history_text}

Output ONLY the JSON object (no markdown code blocks, no extra text):"""

    def _build_fallback_prompt(self, history: List[dict]) -> str:
        lines = []
        for entry in history:
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            lines.append(f"[{role}]: {content}")

        history_text = "\n\n".join(lines)
        return f"Conversation history:\n\n{history_text}\n\nSummary:"

    def _call_with_retry(self, prompt: str, system_prompt: str = "") -> str:
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                return self._call_management_ai(prompt, system_prompt)
            except Exception as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    wait = 2 ** attempt
                    time.sleep(wait)

        raise last_error or RuntimeError("All retries exhausted")

    def _call_management_ai(self, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        request_body = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
        }

        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        url = f"{self.config.api_base.rstrip('/')}/chat/completions"

        response = self.http_client.post(url, json=request_body, headers=headers)
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _parse_response(self, response_text: str) -> MemoryPacket:
        cleaned = self._extract_json(response_text)
        data = json.loads(cleaned)

        episodes = []
        for ep_data in data.get("episodes", []):
            related_ids = []
            for name in ep_data.get("related_entity_names", []):
                related_ids.append(name)
            episodes.append(EpisodeSummary(
                summary_text=ep_data.get("summary_text", ""),
                confidence=self._normalize_confidence(ep_data.get("confidence", "medium")),
                related_entity_ids=related_ids,
            ))

        entities = []
        for ent_data in data.get("entities", []):
            entities.append(EntityRecord(
                entity_name=ent_data.get("entity_name", ""),
                entity_type=ent_data.get("entity_type", "other"),
                exact_value=ent_data.get("exact_value", ""),
                confidence=self._normalize_confidence(ent_data.get("confidence", "medium")),
            ))

        return MemoryPacket(episodes=episodes, entities=entities)

    def _extract_json(self, text: str) -> str:
        text = text.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            return match.group(1).strip()
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start != -1 and brace_end != -1:
            return text[brace_start:brace_end + 1]
        return text

    def _normalize_confidence(self, value: str) -> ConfidenceLevel:
        value = value.lower().strip()
        if value in ("high", "medium", "low", "manual_corrected"):
            return value  # type: ignore[return-value]
        return "medium"

    def _fallback_to_plain_summary(self, text: str) -> MemoryPacket:
        episode = EpisodeSummary(
            summary_text=text[:1000],
            confidence="medium",
        )
        return MemoryPacket(episodes=[episode])

    def close(self) -> None:
        if self._http_client:
            self._http_client.close()
            self._http_client = None
