"""Generate text through the token checkpoint: validate, estimate, reserve, call, reconcile."""

import math
import random
from dataclasses import dataclass
from datetime import datetime

from app.ai import budget
from app.ai.claude import TextGenerator
from app.ai.prompts import Kind, build_prompt, clean_output

# Characters per token for the estimate. Real text is nearer 4, so 3 over-reserves a little.
CHARS_PER_TOKEN = 3


@dataclass(frozen=True)
class Result:
    kind: str
    text: str
    dial: int
    temperature: float
    input_tokens: int
    output_tokens: int
    usage: budget.Usage


def estimate_tokens(system: str, user: str, max_tokens: int) -> int:
    """The most one call can cost: its input (estimated) plus the most Claude may write."""
    return math.ceil((len(system) + len(user)) / CHARS_PER_TOKEN) + max_tokens


def generate(
    user_id: str,
    generator: TextGenerator,
    kind: Kind,
    seed: str,
    dial: int,
    rng: random.Random | None = None,
    now: datetime | None = None,
) -> Result:
    """One generation. Raises BudgetExceeded before calling Claude if the budget cannot cover it."""
    prompt = build_prompt(kind, seed, dial, rng)
    estimate = estimate_tokens(prompt.system, prompt.user, prompt.max_tokens)

    budget.reserve(user_id, estimate, now)

    try:
        generated = generator.generate(
            system=prompt.system,
            prompt=prompt.user,
            max_tokens=prompt.max_tokens,
            temperature=prompt.temperature,
        )
    except Exception:
        budget.release(user_id, estimate, now)
        raise

    budget.reconcile(
        user_id, estimate, generated.input_tokens + generated.output_tokens, now
    )

    return Result(
        kind=kind,
        text=clean_output(kind, generated.text),
        dial=dial,
        temperature=prompt.temperature,
        input_tokens=generated.input_tokens,
        output_tokens=generated.output_tokens,
        usage=budget.get_usage(user_id, now),
    )
