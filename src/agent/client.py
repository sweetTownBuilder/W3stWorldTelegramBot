import logging

from src.agent.base import BaseClient, Response

logger = logging.getLogger(__name__)


class Dify(BaseClient):
    def __init__(self, api_key: str, **kwargs):
        self.api_key = api_key
        self.base_url = "https://dify.w3stworld.io"
        super().__init__(base_url=self.base_url)

    async def send_streaming_chat_message(
            self,
            message: str,
            user_id: int,
            conversation_id: str = None,
            new_member_name: str | None = None,
    ) -> Response:
        return await self._make_streaming_request(
            'post',
            '/v1/chat-messages',
            json_data={
                "query": message,
                "response_mode": 'streaming',
                "conversation_id": conversation_id if conversation_id else '',
                "user": user_id,
                "inputs": {
                    "new_member_name": new_member_name
                }
            },
            headers={'Authorization': f'Bearer {self.api_key}'}
        )
