"""Talking to Claude. The rest of the app depends on `TextGenerator`, not on the SDK, so tests
and the local preview use a fake and never spend tokens."""

import functools
import os
from dataclasses import dataclass
from typing import Protocol

import boto3

# The one place the model is named. Haiku 4.5 is the cheapest model and still accepts
# `temperature`; newer models reject it (see ADR 0015).
MODEL = "claude-haiku-4-5"

REQUEST_TIMEOUT_SECONDS = 25.0


class AiNotConfigured(Exception):
    """No Anthropic API key is available to this deployment."""


class AiUnavailable(Exception):
    """Claude could not be reached or refused the request."""


@dataclass(frozen=True)
class Generated:
    text: str
    input_tokens: int
    output_tokens: int


class TextGenerator(Protocol):
    def generate(
        self, *, system: str, prompt: str, max_tokens: int, temperature: float
    ) -> Generated: ...


class ClaudeGenerator:
    """Calls the Claude API with the Anthropic SDK."""

    def __init__(self, api_key: str):
        import anthropic

        self._client = anthropic.Anthropic(
            api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS, max_retries=1
        )

    def generate(
        self, *, system: str, prompt: str, max_tokens: int, temperature: float
    ) -> Generated:
        import anthropic

        try:
            response = self._client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as error:
            raise AiUnavailable(str(error)) from error

        text = "".join(block.text for block in response.content if block.type == "text")

        return Generated(
            text=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )


def _read_api_key() -> str:
    """The key from Secrets Manager (deployed), or ANTHROPIC_API_KEY (local development)."""
    secret_arn = os.environ.get("ANTHROPIC_SECRET_ARN")

    if secret_arn:
        client = boto3.client("secretsmanager")

        return client.get_secret_value(SecretId=secret_arn)["SecretString"].strip()

    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()

    if key:
        return key

    raise AiNotConfigured("No Anthropic API key is set up")


@functools.cache
def _shared_generator() -> ClaudeGenerator:
    return ClaudeGenerator(_read_api_key())


def get_generator() -> TextGenerator:
    """The generator routes use. Tests replace this with a fake via `dependency_overrides`."""
    return _shared_generator()
