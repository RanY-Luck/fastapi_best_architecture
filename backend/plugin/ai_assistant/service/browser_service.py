import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from backend.core.conf import settings
from backend.database.redis import redis_client
from backend.plugin.ai_assistant.playwright.flows.common import PlaywrightFlowUnavailableError
from backend.plugin.ai_assistant.playwright.flows.dashboard import run_open_dashboard_flow
from backend.plugin.ai_assistant.schema.session import AssistantSessionResetResult, AssistantSessionStatus
from backend.plugin.ai_assistant.utils.session_keys import build_browser_context_key, build_room_name

try:
    from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    Browser = BrowserContext = Playwright = Any  # type: ignore
    async_playwright = None  # type: ignore
    PLAYWRIGHT_AVAILABLE = False


class BrowserService:
    """浏览器运行时服务。"""

    _playwright: Playwright | None = None
    _browser: Browser | None = None
    _contexts: dict[str, BrowserContext] = {}
    _lock = asyncio.Lock()
    _flow_registry: dict[str, Callable[..., Awaitable[str]]] = {
        'open_dashboard': run_open_dashboard_flow,
    }

    @classmethod
    async def _ensure_browser(cls) -> Browser:
        if not PLAYWRIGHT_AVAILABLE or async_playwright is None:
            raise PlaywrightFlowUnavailableError('Playwright 未安装，无法执行页面自动化')
        async with cls._lock:
            if cls._browser is not None:
                return cls._browser
            if cls._playwright is None:
                cls._playwright = await async_playwright().start()
            cls._browser = await cls._playwright.chromium.launch(
                headless=settings.AI_ASSISTANT_PLAYWRIGHT_HEADLESS,
                slow_mo=settings.AI_ASSISTANT_PLAYWRIGHT_SLOW_MO_MS,
            )
            return cls._browser

    @classmethod
    async def _get_context(cls, *, user_id: int, session_uuid: str) -> BrowserContext:
        browser_context_key = build_browser_context_key(user_id, session_uuid)
        async with cls._lock:
            cached_context = cls._contexts.get(browser_context_key)
            if cached_context is not None:
                return cached_context
        browser = await cls._ensure_browser()
        context = await browser.new_context()
        async with cls._lock:
            cls._contexts[browser_context_key] = context
        await redis_client.set(browser_context_key, 'active')
        return context

    @classmethod
    async def _close_context(cls, *, user_id: int, session_uuid: str) -> None:
        browser_context_key = build_browser_context_key(user_id, session_uuid)
        async with cls._lock:
            context = cls._contexts.pop(browser_context_key, None)
        if context is not None:
            await context.close()
        await redis_client.delete(browser_context_key)

    @classmethod
    async def get_session_status(cls, *, user_id: int, session_uuid: str) -> AssistantSessionStatus:
        browser_context_key = build_browser_context_key(user_id, session_uuid)
        browser_context_active = bool(await redis_client.get(browser_context_key))
        return AssistantSessionStatus(
            user_id=user_id,
            session_uuid=session_uuid,
            room_name=build_room_name(user_id, session_uuid),
            browser_context_key=browser_context_key,
            playwright_available=PLAYWRIGHT_AVAILABLE,
            browser_context_active=browser_context_active,
        )

    @classmethod
    async def reset_session(cls, *, user_id: int, session_uuid: str) -> AssistantSessionResetResult:
        browser_context_key = build_browser_context_key(user_id, session_uuid)
        await cls._close_context(user_id=user_id, session_uuid=session_uuid)
        return AssistantSessionResetResult(reset=True, browser_context_key=browser_context_key)

    @classmethod
    async def execute_flow(cls, *, action_name: str | None, content: str, user_id: int, session_uuid: str) -> str:
        if not action_name:
            raise PlaywrightFlowUnavailableError('缺少 Playwright 动作名称，无法执行页面自动化')
        flow = cls._flow_registry.get(action_name)
        if flow is None:
            raise PlaywrightFlowUnavailableError(f'未注册的 Playwright 动作: {action_name}')
        context = await cls._get_context(user_id=user_id, session_uuid=session_uuid)
        return await flow(context=context, content=content)
