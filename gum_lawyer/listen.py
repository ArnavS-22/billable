"""Start GUM's Screen observer with lawyer propose/revise prompts."""

from __future__ import annotations

import asyncio
import inspect
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from gum.gum import gum as Gum
from gum.observers import Screen

from gum_lawyer.live import append_observation
from gum_lawyer.prompts import LAWYER_PROPOSE_PROMPT, LAWYER_REVISE_PROMPT


class _NoBatch:
    def __init__(self, *args, **kwargs):
        pass

    async def start(self):
        return None

    async def stop(self):
        return None

    def push(self, observer_name, content, content_type):
        append_observation(content, observer=observer_name)
        return "live"

    def size(self):
        return 0

    def pop_batch(self, batch_size=None):
        return []


def _screen(model: str) -> Screen:
    params = inspect.signature(Screen.__init__).parameters
    if "model_name" in params:
        return Screen(model_name=model)
    if "model" in params:
        return Screen(model=model)
    return Screen()


async def _on_screen(self, observer, update) -> None:
    append_observation(getattr(update, "content", "") or "", getattr(observer, "name", "Screen"))
    self.logger.info("Observation from %s", getattr(observer, "name", "Screen"))


def _patch_gum() -> None:
    import gum.batcher as batcher_mod
    import gum.gum as gum_mod

    batcher_mod.ObservationBatcher = _NoBatch
    gum_mod.ObservationBatcher = _NoBatch
    Gum._default_handler = _on_screen
    leftover = Path.home() / ".cache/gum" / "batches"
    if leftover.exists():
        shutil.rmtree(leftover, ignore_errors=True)


async def listen() -> None:
    _patch_gum()
    user_name = os.getenv("USER_NAME") or os.getenv("GUM_USER_NAME") or "Lawyer"
    model = os.getenv("MODEL_NAME") or "gpt-4o-mini"
    print(f"GUM lawyer listener: user={user_name!r} model={model!r}")
    print("Screen dumps become observations immediately.")

    async with Gum(
        user_name,
        model,
        _screen(model),
        propose_prompt=LAWYER_PROPOSE_PROMPT,
        revise_prompt=LAWYER_REVISE_PROMPT,
    ) as instance:
        if instance._batch_task:
            instance._batch_task.cancel()
            instance._batch_task = None
        await asyncio.Future()


def main() -> None:
    asyncio.run(listen())


if __name__ == "__main__":
    main()
