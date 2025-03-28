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
from src.agent.news_client import Dify as NewsDify
from src.configuration import conf


async def start_bot():
    """启动 bot 并监听消息"""
    bot_clementine = Bot(token=conf.bot.token, default=DefaultBotProperties(parse_mode='MarkdownV2'))
    bot_maeve = Bot(token=conf.bot.maeve_token, default=DefaultBotProperties(parse_mode='MarkdownV2'))
    bot_teddy = Bot(token=conf.bot.teddy_token, default=DefaultBotProperties(parse_mode='MarkdownV2'))
    dp = Dispatcher()  # 创建 Dispatcher（消息管理器）
    dify: Dify = Dify(conf.dify.api_key, conf.dify.base_url)
    news_client: NewsDify = NewsDify(conf.news.api_key, conf.news.base_url)

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

        mention_me = False
        if chat.type in ["group", "supergroup"]:
            chat_id = chat.id

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
            mention_me = True
        conversation_id: str|None = None
        if result:
            conversation_id = state_data.get(result)
            user_id = result
        if message.text is None:
            return
        if mention_me:
            response = await dify.send_streaming_chat_message(
                message=message.text,
                user_id=user_id,
                conversation_id=conversation_id,
                user_name=message.from_user.username,
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
                new_member_name=new_member_name,
                user_name=member_name,
                telegram_chat_type="welcome",
            )
            if response.need_response:
                await event.answer(escape_markdown_v2(response.message), parse_mode="MarkdownV2")

    async def send_daily_random_messages():
        while True:
            if conf.bot.tg_group_id:
                response = await news_client.send_streaming_chat_message(
                    message="get today news.",
                    user_id=conf.bot.tg_group_id,
                    conversation_id=None,
                    new_member_name=None,
                    telegram_chat_type="ask_for_news",
                )
                for conversation in response.conversations:
                    # sleep conversation.delayTime seconds
                    await asyncio.sleep(conversation.delayTime * 10)
                    if conversation.user == "maeve":
                        # use telegram bot api to send message
                        await bot_maeve.send_message(text=escape_markdown_v2(conversation.content),chat_id=conf.bot.tg_group_id, parse_mode="MarkdownV2")
                    elif conversation.user == "teddy":
                        await bot_teddy.send_message(text=escape_markdown_v2(conversation.content),chat_id=conf.bot.tg_group_id, parse_mode="MarkdownV2")
                    elif conversation.user == "clementine":
                        await bot_clementine.send_message(text=escape_markdown_v2(conversation.content),chat_id=conf.bot.tg_group_id, parse_mode="MarkdownV2")
            await asyncio.sleep(random.randint(60 * 60 * 3, 60 * 60 * 5))  # Sleep for a random 5-6 hours

    asyncio.create_task(send_daily_random_messages())
    # 启动 bot
    await dp.start_polling(bot_clementine)


def escape_markdown_v2(text: str) -> str:
    """
    保留 MarkdownV2 结构（链接、粗体等），转义其他部分的保留字符
    """
    # 匹配 MarkdownV2 的核心结构（非贪婪匹配，优先处理链接）
    pattern = re.compile(
        r'(\[.*?\]\(\S*?\))'      # 链接 [text](url)，URL中不允许空格
        r'|(\*\*.*?\*\*)'          # 粗体 **text**
        r'|(\*.*?\*)'              # 斜体 *text*
        r'|(__.*?__)'              # 下划线 __text__
        r'|(_.*?_)'                # 斜体 _text_
        r'|(`.*?`)'                # 行内代码 `text`
        r'|(```[\s\S]*?```)'       # 多行代码块
        r'|\\n'                    # 换行
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
        group_text = match.group()
        if match := re.match(r'\[(.*?)\]\((\S*?)\)', group_text, re.DOTALL):
            link_text = match.group(1)
            link_url = match.group(2)
            parts.append(f'[{_escape_plain_text(link_text)}]({_escape_plain_text(link_url)})')
        elif match := re.match(r'\*\*(.*?)\*\*', group_text, re.DOTALL):
            txt = match.group(1)
            parts.append(f'**{_escape_plain_text(txt)}**')
        elif match := re.match(r'__(.*?)__', group_text, re.DOTALL):
            txt = match.group(1)
            parts.append(f'__{_escape_plain_text(txt)}__')
        elif match := re.match(r'_(.*?)_', group_text):
            txt = match.group(1)
            parts.append(f'_{_escape_plain_text(txt)}_')
        elif match := re.match(r'`(.*?)`', group_text):
            txt = match.group(1)
            parts.append(f'`{_escape_plain_text(txt)}`')
        elif match := re.match(r'```([\s\S]*?)```', group_text):
            txt = match.group(1)
            parts.append(f'```{_escape_plain_text(txt)}```')
        elif re.match(r'\\n', group_text):
            parts.append(f'\n')
        else:
            parts.append(group_text)
        last_end = end

    # 处理剩余文本
    if last_end < len(text):
        plain_text = text[last_end:]
        parts.append(_escape_plain_text(plain_text))

    return ''.join(parts)


def _escape_plain_text(text: str) -> str:
    """转义普通文本中的 MarkdownV2 保留字符"""
    return re.sub(pattern=re.compile(r"([_*\[\]()~`>#+\-=|{}.!\\])"), repl=r'\\\1', string=text)


if __name__ == "__main__":
    logging.basicConfig(level=conf.logging_level)
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        logging.info("程序已手动中断。")
