import json
from typing import Any

from backend.core.conf import settings
from backend.plugin.ai_assistant.playwright.flows.common import get_or_create_page


async def run_query_device_reports_flow(*, context: Any, content: str) -> str:
    page = await get_or_create_page(context)
    report_url = settings.AI_ASSISTANT_PLAYWRIGHT_REPORTS_URL.strip() or settings.AI_ASSISTANT_PLAYWRIGHT_START_URL.strip()
    if report_url:
        await page.goto(report_url, wait_until='networkidle')

    keyword = content.strip()
    if keyword:
        await page.evaluate(
            """
            ({ keyword }) => {
              const selectors = ['input', '.el-input__inner', '[placeholder*="设备"]', '[placeholder*="关键字"]']
              for (const selector of selectors) {
                const node = document.querySelector(selector)
                if (!node) continue
                node.focus()
                node.value = keyword
                node.dispatchEvent(new Event('input', { bubbles: true }))
                node.dispatchEvent(new Event('change', { bubbles: true }))
                break
              }
            }
            """,
            {'keyword': keyword},
        )
        await page.evaluate(
            """
            () => {
              const buttons = Array.from(document.querySelectorAll('button, .el-button, [role="button"]'))
              const target = buttons.find(node => node.textContent?.includes('查询') || node.textContent?.includes('搜索'))
              if (target) target.click()
            }
            """
        )
        await page.wait_for_timeout(1500)

    title = await page.title()
    current_url = page.url or 'about:blank'
    rows = await page.evaluate(
        """
        () => {
          const tables = Array.from(document.querySelectorAll('table'))
          const table = tables[0]
          if (!table) return []
          const headerCells = Array.from(table.querySelectorAll('thead th')).map(cell => cell.textContent?.trim() || '')
          const bodyRows = Array.from(table.querySelectorAll('tbody tr')).slice(0, 10)
          return bodyRows.map(row => {
            const cells = Array.from(row.querySelectorAll('td')).map(cell => cell.textContent?.trim() || '')
            const item = {}
            headerCells.forEach((header, index) => {
              if (header) item[header] = cells[index] || ''
            })
            if (!headerCells.length) {
              cells.forEach((value, index) => {
                item[`col_${index + 1}`] = value
              })
            }
            return item
          })
        }
        """
    )
    result = {
        'action_name': 'query_device_reports',
        'source': 'playwright',
        'status': 'completed',
        'page_title': title or '(empty)',
        'page_url': current_url,
        'query': {
            'keyword': keyword,
        },
        'data': {
            'rows': rows,
            'count': len(rows),
        },
        'raw_message': content,
    }
    return json.dumps(result, ensure_ascii=False, indent=2)
