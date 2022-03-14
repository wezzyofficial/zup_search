import logging


file_log = logging.FileHandler('server.log')
console_out = logging.StreamHandler()


logging.basicConfig(handlers=(file_log, console_out),
                    format='\n[%(asctime)s | %(levelname)s] [ZUP SEARCH] %(message)s\n',
                    datefmt='%H:%M:%S, %m.%d.%Y',
                    level=logging.INFO)


async def log(text):
    logging.info(text)


async def error(text):
    logging.error(text)


async def warning(text):
    logging.warning(text)