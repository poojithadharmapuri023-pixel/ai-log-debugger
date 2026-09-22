import json
import os
from typing import Any

from dotenv import load_dotenv
from google import genai

load_dotenv()

MODEL_NAME = "gemini-3.6-flash"


class GeminiService:
    """Gemini-powered explanation layer with deterministic fallback."""

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None

    @property
    def available(self) -> bool:
        return self.client is not None

    def explain_root_cause(self, analysis: dict[str, Any]) -> dict[str, Any]:
        fallback = {
            "probable_root_cause": analysis.get("root_cause_service"),
            "affected_services": list(analysis.get("service_scores", {}).keys()),
            "evidence": [
                analysis.get("first_problem_message"),
                analysis.get("reason"),
            ],
            "impact": "Potential downstream service failures.",
            "recommended_investigation_steps": [
                "Check the root-cause service health and logs.",
                "Inspect resource usage and service dependencies.",
                "Review downstream failures after the first problem event.",
            ],
        }

        if not self.client:
            return {
                "available": False,
                "status": "fallback",
                "analysis": fallback,
            }

        prompt = f"""
You are an AI incident analysis assistant.

Analyze ONLY the deterministic evidence below.

Do not invent facts.
Do not change the identified root-cause service.
Return ONLY valid JSON.
Do not use markdown.
Do not include code fences.

Required JSON structure:
{{
  "probable_root_cause": "string",
  "affected_services": ["string"],
  "evidence": ["string"],
  "impact": "string",
  "recommended_investigation_steps": ["string"]
}}

Deterministic evidence:
{json.dumps(analysis, indent=2)}
"""

        try:
            response = self.client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )

            text = (response.text or "").strip()
            parsed = json.loads(text)

            required = {
                "probable_root_cause",
                "affected_services",
                "evidence",
                "impact",
                "recommended_investigation_steps",
            }

            if not required.issubset(parsed.keys()):
                raise ValueError("Gemini response is missing required fields.")

            return {
                "available": True,
                "status": "generated",
                "analysis": parsed,
            }

        except Exception as exc:
            return {
                "available": False,
                "status": "fallback",
                "analysis": fallback,
                "error": str(exc),
            }
