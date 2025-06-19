from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import requests
from sseclient import SSEClient

if TYPE_CHECKING:
    from collections.abc import Mapping

    from yarl import URL


@dataclass
class Conversations:
    user: str
    content: str
    delayTime: int


@dataclass
class NewsResponse:
    conversations: list[Conversations]
    conversation_id: str


class NewsClient:
    """基于 sseclient-py 的 SSE 客户端"""

    def __init__(self, base_url: str | URL) -> None:
        self._base_url = str(base_url)
        self.log = logging.getLogger(self.__class__.__name__)

    async def _make_streaming_request(
            self,
            method: str,
            url: str,
            params: Mapping[str, str] | None = None,
            json_data: Mapping[str, str] | None = None,
            headers: Mapping[str, str] | None = None,
            data: Mapping[str, str] | None = None,
    ) -> str:
        """
        在后台线程里使用 requests + sseclient-py，完成 POST/GET + SSE 流式消费。
        """

        def _sync_sse() -> str:
            full_url = urljoin(self._base_url, url)
            self.log.debug("sync request %s %s, json=%r, params=%r", method, full_url, json_data, params)

            # 发起同步请求
            resp = requests.request(
                method,
                full_url,
                params=params,
                json=json_data,
                data=data,
                headers={**(headers or {}), "Accept": "text/event-stream"},
                stream=True,
            )
            resp.raise_for_status()

            client = SSEClient(resp)
            message = ""
            for evt in client.events():
                try:
                    payload = json.loads(evt.data)
                except (ValueError, TypeError):
                    continue

                event_type = payload.get("event")
                if event_type == "agent_message":
                    message += payload.get("answer", "")
                elif event_type == "message_end":
                    break
                elif event_type == "workflow_finished":
                    # 如果 workflow_finished 后面还有文本输出，直接取它
                    out = payload.get("data", {}).get("outputs", {}).get("text", "")
                    message = out
                    break

            return message

        # 切回 asyncio
        return await asyncio.to_thread(_sync_sse)
