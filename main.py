import os
import logging

from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

load_dotenv()

from telegram.ext import Application
from bot.handlers import commands, journal
from db.db import get_db
from services.scheduler_service import SchedulerService

telegram_bot_token = os.environ.get('TELEGRAM_TOKEN')


def main() -> None:
    get_db()  # fail fast on a missing MONGODB_URI, not on the first check-in

    application = Application.builder().token(telegram_bot_token).build()

    logging.info('Application start...')

    commands.register(application)
    journal.register(application)

    SchedulerService().start(application.job_queue)

    logging.info('Polling for updates...')

    # Replaces start_polling() + idle(): run_polling owns the event loop and
    # handles initialisation and graceful shutdown itself.
    application.run_polling()


if __name__ == '__main__':
    main()
