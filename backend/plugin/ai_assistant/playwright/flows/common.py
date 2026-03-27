from typing import Any


class PlaywrightFlowUnavailableError(RuntimeError):
    """Raised when Playwright fallback is unavailable."""


async def get_or_create_page(context: Any) -> Any:
    pages = context.pages
    if pages:
        return pages[0]
    return await context.new_page()
