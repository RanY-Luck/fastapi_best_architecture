from typing import Any

from backend.core.conf import settings
from backend.plugin.ai_assistant.playwright.flows.common import get_or_create_page


async def run_open_dashboard_flow(*, context: Any, content: str) -> str:
    page = await get_or_create_page(context)
    start_url = settings.AI_ASSISTANT_PLAYWRIGHT_START_URL.strip()
    if start_url:
        await page.goto(start_url, wait_until='networkidle')
        title = await page.title()
        return f'已打开页面: {start_url}，页面标题: {title or "(empty)"}'
    title = await page.title()
    current_url = page.url or 'about:blank'
    return f'未配置 AI_ASSISTANT_PLAYWRIGHT_START_URL，当前页面: {current_url}，页面标题: {title or "(empty)"}，原始消息: {content}'
