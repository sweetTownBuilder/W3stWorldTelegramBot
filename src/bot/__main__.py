import asyncio
import logging
import random
import re

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import MessageEntityType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ChatMemberUpdated

from src.agent.client import Dify
from src.configuration import conf


async def start_bot():
    """启动 bot 并监听消息"""
    bot = Bot(token=conf.bot.token, default=DefaultBotProperties(parse_mode='MarkdownV2'))
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
        chat = message.chat
        user_id = message.from_user.id
        result = None

        if chat.type in ["group", "supergroup"]:
            chat_id = chat.id
            mention_me = False

            # 检测是否被@提及
            if message.entities:
                for entity in message.entities:
                    if entity.type in [MessageEntityType.MENTION, MessageEntityType.TEXT_MENTION]:
                        mention_me = True
                        break

            if mention_me:
                result = f"{chat_id}-{user_id}"
            else:
                result = str(chat_id)

        elif chat.type == "private":
            result = str(user_id)
        conversation_id: str|None = None
        if result:
            conversation_id = state_data.get(result)
            user_id = result
        if message.text is None:
            return
        response = await dify.send_streaming_chat_message(
            message=message.text,
            user_id=user_id,
            conversation_id=conversation_id,
        )
        if conversation_id is None:
            if result and response.conversation_id:
                await state.update_data({result: response.conversation_id})  # 存储 UUID
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

    async def send_daily_random_messages():
        while True:
            if conf.bot.tg_group_id:
                response = await dify.send_streaming_chat_message(
                    message="Tell a piece of trending news in the field of crypto memecoins，preferably news about a "
                            "price of a memecoin went up trenmendously or someone make a huge returns on a memcoin. "
                            "News should have a clear and specific protagonist, not a general study of the field. If "
                            "appropriate, you may open with an interactive question as greetings such as \"Anyone "
                            "wants to hear an exciting news about ... ?\". If appropriate, you may end with a "
                            "suggestion about what people should do upon hearing the news. Your tone depicting the "
                            "news itself should be concise and professional but your overall tone should be casual "
                            "and friendly.",
                    user_id=conf.bot.tg_group_id,
                    conversation_id=None,
                    new_member_name=None
                )
                if response.need_response and conf.bot.tg_group_id:
                    logging.info(response.message)
                    await bot.send_message(text=escape_markdown_v2(response.message),chat_id=conf.bot.tg_group_id, parse_mode="MarkdownV2")
            await asyncio.sleep(random.randint(60 * 60 * 3, 60 * 60 * 5))  # Sleep for a random 5-6 hours

    asyncio.create_task(send_daily_random_messages())
    # 启动 bot
    await dp.start_polling(bot)


def escape_markdown_v2(text: str) -> str:
    """
    保留 MarkdownV2 结构（链接、粗体等），转义其他部分的保留字符
    """
    # 匹配 MarkdownV2 的核心结构（非贪婪匹配）
    pattern = re.compile(
        r'(\[.*?\]\(.*?\))'  # 链接 [text](url)
        r'|(\*.*?\*)'  # 粗体 *text*
        r'|(_.*?_)'  # 斜体 _text_
        r'|(`.*?`)'  # 行内代码 `text`
        r'|(```[\s\S]*?```)'  # 多行代码块（使用 [\s\S] 匹配任意字符）
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
    """转义普通文本中的 MarkdownV2 保留字符"""
    # 注意：将连字符 - 放在字符类开头或结尾，避免被识别为范围符号
    escape_chars = r'_*[]()~`>#+=|{}.!-'  # 包含所有保留字符
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


if __name__ == "__main__":
    logging.basicConfig(level=conf.logging_level)
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        logging.info("程序已手动中断。")
