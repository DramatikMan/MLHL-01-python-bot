import os
import asyncio
from collections.abc import Iterable

from aiohttp import ClientSession


quotes = (
    "Everybody's got a secret, can you tell me what is mine?",
    "I want to share it all with Mary, results are gonna vary now.",
    "Give me a reason, cause I've got nothing to gain.",
    "And if I'm the king of cowards, you're the queen of pain.",
    "Не ведьма, не кольдунья ко мне явилась в дом."
)

BOT_TOKEN = os.environ['BOT_TOKEN']
CHAT_ID = os.environ['CHAT_ID']


async def spam_quotes(quotes: Iterable[str]) -> None:
    async with ClientSession() as http_sess:
        for quote in quotes:
            url = f'https://api.telegram.org/bot{BOT_TOKEN}/' \
                f'sendMessage?chat_id={CHAT_ID}&text="{quote}"'
            await http_sess.get(url)
            await asyncio.sleep(5)


def main() -> None:
    asyncio.run(spam_quotes(quotes))


if __name__ == '__main__':
    main()
