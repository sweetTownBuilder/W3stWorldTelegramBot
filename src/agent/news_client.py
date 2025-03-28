import logging

from src.agent.news import NewsClient, NewsResponse

logger = logging.getLogger(__name__)


class Dify(NewsClient):
    def __init__(self, api_key: str, base_url: str, **kwargs):
        self.api_key = api_key
        self.base_url = base_url
        super().__init__(base_url=self.base_url)

    async def send_streaming_chat_message(
            self,
            message: str,
            user_id: int,
            user_name: str = 'telegram',
            telegram_chat_type: str = 'chat',
            conversation_id: str = None,
            new_member_name: str | None = None,
    ) -> NewsResponse:
        return await self._make_streaming_request(
            'post',
            '/v1/chat-messages',
            json_data={
                "query": message,
                "response_mode": 'streaming',
                "conversation_id": conversation_id if conversation_id else '',
                "user": user_id,
                "inputs": {
                    "run_type": "chat",
                    "chat_place": "telegram",
                    "user_name": user_name,
                    "new_member_name": new_member_name,
                    "telegram_chat_type": telegram_chat_type,
                }
            },
            headers={'Authorization': f'Bearer {self.api_key}'}
        )
