"""Responses streaming adapter using explicitly granted ChatGPT plan usage."""

import json
import re

import httpx

from app.chatgpt_auth import RESOURCE, ChatGPTConnection
from app.llm import PROMPT, ExtractionError, ResponseType
from app.models import ProcessModel, Sentence


def safe_diagnostics(error: object) -> str:
    """Expose provider error identifiers without returning arbitrary provider text."""
    if not isinstance(error, dict):
        return ""
    result = ""
    for label, value in (
        ("code", error.get("code")),
        ("parameter", error.get("param")),
        ("reason", error.get("reason")),
    ):
        if isinstance(value, str) and re.fullmatch(r"[a-zA-Z0-9_.-]{1,100}", value):
            result += f" {label}={value}."
    return result


def provider_error(status: int | None, error: object) -> ExtractionError:
    """Translate upstream failures into safe, actionable application errors."""
    code = error.get("code") if isinstance(error, dict) else None
    if code == "subscription_sharing_usage_limit_exceeded" or status == 429:
        return ExtractionError(
            "ChatGPT usage or rate limit reached. Check your plan usage in ChatGPT settings "
            "and retry when allowance is available.", code="usage_limit", status_code=429,
        )
    if status == 401:
        return ExtractionError(
            "ChatGPT authorization expired. Reconnect in ChatGPT Connection.",
            code="connection_required", status_code=401,
        )
    if status == 403:
        return ExtractionError(
            "ChatGPT denied access. Check the account's workspace and app permissions "
            "in ChatGPT Connection.", code="access_denied", status_code=403,
        )
    return ExtractionError(
        "ChatGPT could not complete the request. Retry, or check the selected model in "
        f"ChatGPT Connection.{safe_diagnostics(error)}"
    )


class ChatGPTClient:
    def __init__(self, connection: ChatGPTConnection):
        self.connection = connection

    def extract(self, ledger: list[Sentence]) -> ProcessModel:
        """Extract through the same validated JSON contract as hosted providers."""
        return self.structured(
            PROMPT, {"sentences": [s.model_dump() for s in ledger]}, ProcessModel
        )

    def structured(self, prompt: str, data: dict, schema: type[ResponseType]) -> ResponseType:
        """Only accept a complete successful stream and locally valid output."""
        token, model = self.connection.request_credentials()
        payload = {
            "model": model,
            "store": False,
            "stream": True,
            "instructions": prompt
            + json.dumps(schema.model_json_schema())
            + "\nReturn only a JSON object, with no markdown.",
            "input": [{"role": "user", "content": json.dumps(data)}],
        }
        output = ""
        completed = False
        try:
            with (
                httpx.Client(timeout=180, follow_redirects=False) as client,
                client.stream(
                    "POST",
                    RESOURCE + "/responses",
                    json=payload,
                    headers={"Authorization": "Bearer " + token},
                ) as response,
            ):
                if response.is_error:
                    response.read()
                    error = None
                    try:
                        error = response.json().get("error", {})
                    except (ValueError, AttributeError):
                        pass
                    raise provider_error(response.status_code, error)
                for line in response.iter_lines():
                    if not line.startswith("data:") or line[5:].strip() == "[DONE]":
                        continue
                    event = json.loads(line[5:])
                    kind = event.get("type")
                    if kind == "response.output_text.delta":
                        output += event["delta"]
                        if len(output) > 500000:
                            raise ExtractionError("ChatGPT response exceeded the output limit")
                    elif kind in {
                        "response.failed",
                        "response.incomplete",
                        "error",
                        "response.refusal.delta",
                    }:
                        response_body = event.get("response") or {}
                        error = (
                            event.get("error")
                            or response_body.get("error")
                            or response_body.get("incomplete_details")
                            or event
                        )
                        raise provider_error(None, error)
                    elif kind == "response.completed":
                        completed = event.get("response", {}).get("status") == "completed"
            if not completed:
                raise ExtractionError("ChatGPT stream ended before completion")
            return schema.model_validate_json(output)
        except httpx.TimeoutException:
            raise ExtractionError(
                "ChatGPT took too long to respond. Retry your question.",
                code="provider_timeout", status_code=504,
            ) from None
        except httpx.HTTPError:
            raise ExtractionError("Cannot reach ChatGPT. Check internet access and retry.") from None
        except (ValueError, KeyError, TypeError):
            raise ExtractionError(
                "ChatGPT returned an invalid response. Retry your question; no result was saved."
            ) from None
