from backend.plugin.ai_assistant.schema.chat import ChatRoutePlan
from backend.plugin.ai_assistant.service.action_catalog import ACTION_CATALOG


class RouterService:
    @staticmethod
    def resolve_route(*, content: str, action_name: str | None = None) -> ChatRoutePlan:
        normalized = content.lower()
        if action_name and action_name in ACTION_CATALOG:
            config = ACTION_CATALOG[action_name]
            return ChatRoutePlan(
                route_type=config['route_type'],
                target_name=config['target_name'],
                sync_allowed=bool(config['sync_allowed']),
                reason='explicit_action',
            )

        for config in ACTION_CATALOG.values():
            keywords = config.get('keywords', [])
            if any(str(keyword).lower() in normalized for keyword in keywords):
                return ChatRoutePlan(
                    route_type=config['route_type'],
                    target_name=config['target_name'],
                    sync_allowed=bool(config['sync_allowed']),
                    reason='keyword_match',
                )

        return ChatRoutePlan(
            route_type='chat',
            target_name='plain_reply',
            sync_allowed=True,
            reason='legacy_fallback_chat',
        )
