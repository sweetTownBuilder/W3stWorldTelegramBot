import asyncio
import logging
import re

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ChatMemberUpdated

from src.agent.client import Dify
from src.configuration import conf


async def start_bot():
    """启动 bot 并监听消息"""
    bot = Bot(token=conf.bot.token, default=DefaultBotProperties(parse_mode='HTML'))
    dp = Dispatcher()  # 创建 Dispatcher（消息管理器）
    dify: Dify = Dify(conf.dify.api_key, conf.dify.base_url)

    # 注册命令处理器
    @dp.message(Command("start"))
    async def start_handler(message: Message):
        await message.answer("你好！我是你的 Bot 🤖")

    @dp.message(Command("help"))
    async def help_handler(message: Message):
        await message.answer("支持的命令：\n/start - 启动机器人\n/help - 获取帮助")

    @dp.message()
    async def echo_handler(message: Message, state: FSMContext):
        """监听所有文本消息，并原样返回"""
        state_data: dict = await state.get_data()
        conversation_id: str = state_data.get('conversation_id')
        if message.text is None:
            return
        response = await dify.send_streaming_chat_message(
            message=message.text,
            user_id=message.from_user.id,
            conversation_id=conversation_id,
        )
        if response.need_response:
            await message.reply(escape_markdown_v2(response.message), parse_mode="MarkdownV2")

    @dp.chat_member()
    async def welcome_handler(event: ChatMemberUpdated):
        """当有新成员加入时，@他并发送欢迎消息"""
        if event.new_chat_member.status in ["member", "restricted"]:  # 只欢迎新成员
            member_name = event.new_chat_member.user.username or event.new_chat_member.user.first_name or "New Member"
            new_member_name = f"@{member_name}"
            response = await dify.send_streaming_chat_message(
                message="new member join the group",
                user_id=event.from_user.id,
                conversation_id=None,
                new_member_name=new_member_name
            )
            if response.need_response:
                await event.answer(escape_markdown_v2(response.message), parse_mode="MarkdownV2")

    # 启动 bot
    await dp.start_polling(bot)


def escape_markdown_v2(text: str) -> str:
    """
    保留 MarkdownV2 结构（链接、粗体、斜体、代码块），转义其他部分的特殊字符
    """
    # 匹配 MarkdownV2 的核心结构（非贪婪匹配）
    pattern = re.compile(
        r'(\[.*?\]\(.*?\))'  # 链接 [text](url)
        r'|(\*.*?\*)'  # 粗体 *text*
        r'|(_.*?_)'  # 斜体 _text_
        r'|(`.*?`)'  # 行内代码 `text`
        r'|(```.*?```)'  # 多行代码块（需配合 re.DOTALL）
        , re.DOTALL)

    parts = []
    last_end = 0

    for match in pattern.finditer(text):
        start = match.start()
        end = match.end()

        # 转义非结构化的普通文本
        if start > last_end:
            plain_text = text[last_end:start]
            parts.append(_escape_plain_text(plain_text))

        # 保留 Markdown 结构
        parts.append(match.group())
        last_end = end

    # 处理剩余文本
    if last_end < len(text):
        plain_text = text[last_end:]
        parts.append(_escape_plain_text(plain_text))

    return ''.join(parts)


def _escape_plain_text(text: str) -> str:
    """转义普通文本中的 MarkdownV2 特殊字符"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


if __name__ == "__main__":
    logging.basicConfig(level=conf.logging_level)
    asyncio.run(start_bot())
