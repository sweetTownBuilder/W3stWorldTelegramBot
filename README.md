## W3stWorldTelegramBot

*Provide Telegram chat capabilities for AI Agent*

## To run locally / develop:

1. copy `.env.example` to `.env` and fill the required fields (get bot token from botfather, and dify api from your dify workflow)
2. create a virtual environment `python3 -m venv venv`
3. activate the virtual environment `source venv/bin/activate`
4. install the dependencies `pip install -r requirements.txt`
5. run the server `python -m src.bot`
6. go to telegram and start the bot

## To run with docker
1. copy `.env.example` to `.env` and fill the required fields (get bot token from botfather, and dify api from your dify workflow)
2. run with docker compose `docker compose up -d`
3. shutdown program with `docker compose down`
