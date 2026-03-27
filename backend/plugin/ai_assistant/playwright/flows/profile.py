import json
from typing import Any

from backend.core.conf import settings
from backend.plugin.ai_assistant.playwright.flows.common import get_or_create_page


async def run_query_user_profile_flow(*, context: Any, content: str) -> str:
    page = await get_or_create_page(context)
    profile_url = settings.AI_ASSISTANT_PLAYWRIGHT_PROFILE_URL.strip() or settings.AI_ASSISTANT_PLAYWRIGHT_START_URL.strip()
    if profile_url:
        await page.goto(profile_url, wait_until='networkidle')

    title = await page.title()
    current_url = page.url or 'about:blank'
    profile_data = await page.evaluate(
        """
        () => {
          const textOf = (selectors) => {
            for (const selector of selectors) {
              const node = document.querySelector(selector)
              const value = node?.textContent?.trim()
              if (value) return value
            }
            return null
          }
          const firstByLabel = (labels) => {
            const items = Array.from(document.querySelectorAll('body *'))
            for (const item of items) {
              const label = item.textContent?.trim()
              if (!label) continue
              if (!labels.some(keyword => label.includes(keyword))) continue
              const next = item.nextElementSibling?.textContent?.trim()
              if (next) return next
            }
            return null
          }
          return {
            user_id: firstByLabel(['用户ID', '用户编号', '账号ID', 'ID']),
            user_name: textOf(['[data-testid="user-name"]', '.user-name', '.nickname', '.username']) || firstByLabel(['用户名', '昵称', '姓名', '账号']),
            role_names: firstByLabel(['角色', '用户角色']),
            department_name: firstByLabel(['部门', '所属部门']),
            mobile: firstByLabel(['手机号', '手机']),
            email: firstByLabel(['邮箱', 'Email', '电子邮箱']),
            status: firstByLabel(['状态', '账号状态']),
          }
        }
        """
    )
    result = {
        'action_name': 'query_user_profile',
        'source': 'playwright',
        'status': 'completed',
        'page_title': title or '(empty)',
        'page_url': current_url,
        'data': profile_data,
        'raw_message': content,
    }
    return json.dumps(result, ensure_ascii=False, indent=2)
