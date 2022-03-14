from console import log, error, warning
from asyncio.exceptions import TimeoutError
from aiohttp.client_exceptions import ClientConnectorError
import asyncio, aiohttp, xmltodict, json, ujson, sys, aiofiles, os


login, password = 'username', 'password'
url = 'http://127.0.0.1/WEB1CZP/odata/standard.odata/'


async def new_basic_auth(login: str, password: str):
    return aiohttp.BasicAuth(login, password)


async def read_index_page(auth: aiohttp.BasicAuth):
    session = aiohttp.ClientSession(
        json_serialize=ujson.dumps,
        trust_env=True,
        connector=aiohttp.TCPConnector(verify_ssl=True)
    )

    async with session.get(url, auth=auth, timeout=15) as response:
        try:
            text = await response.text()
        except:
            text = None

        await session.close()

    return text


async def creating_menu_pages(pay_m: list, page_selector: int):
    result = []

    if page_selector == 0:
        page_selector = 5

    def append(elem, id):
        result[id].append(elem)

    for i in range(0, pay_m.__len__() % page_selector + len(pay_m)):
        result.append(list())
        for j in range(i * page_selector, (i + 1) * page_selector):
            try:
                append(pay_m[j], i)
                # print("Page {}".format(i + 1))
            except:
                pass

    result = list(filter(None, result))
    return result


async def data_collection(new_auth: aiohttp.BasicAuth, collection_link: str, collections: list, num: int):
    if 'Удалить' not in collection_link:
        session = aiohttp.ClientSession(
            json_serialize=ujson.dumps,
            trust_env=True,
            connector=aiohttp.TCPConnector(verify_ssl=True)
        )

        error_func = False
        try:
            async with session.get(f'{url}{collection_link}', auth=new_auth) as response:
                try:
                    text = await response.text(encoding='utf-8')
                except asyncio.exceptions.TimeoutError:
                    await warning(text=f'URL: {collection_link} - timeout error! '
                                       f'({num}/{len(collections)}).')
                    text = None
                except:
                    text = None

                await session.close()
        except ClientConnectorError:
            error_func = True
            await session.close()

            await warning(text='Сервак лёг поспать, но мы подождем 10 сек..')

            await asyncio.sleep(10)

            return await data_collection(new_auth=new_auth, collection_link=collection_link, collections=collections,
                                         num=num)
        except TimeoutError:
            error_func = True
            await session.close()

            await error(text=f'URL: {collection_link} - timeout error! ({num}/{len(collections)}).')


        if error_func is False:
            file_path = f'cache/{collection_link}'

            if text is not None:
                file_data = ''
                if os.path.exists(file_path):
                    file = await aiofiles.open(file_path, mode='r')
                    file_data = await file.read()

                    file_data = file_data.replace('\r', '')

                new_file_data = True
                if file_data == text:
                    new_file_data = False

                if new_file_data:
                    new_file = await aiofiles.open(f'cache/{collection_link}', mode='w')
                    await new_file.write(f'{text}')
                    await new_file.close()

                    await log(text=f'URL: {collection_link} - creating or updating file! ({num}/{len(collections)}).')
                else:
                    await log(text=f'URL: {collection_link} - is old file, skip! ({num}/{len(collections)}).')
            else:
                await log(text=f'URL: {collection_link} - not ok! ({num}/{len(collections)}).')
    else:
        await warning(text=f'URL: {collection_link} - "delete word" detected! '
                           f'({num}/{len(collections)}).')


async def updating_cache(new_auth: aiohttp.BasicAuth, cache_files: list):
    if len(cache_files) > 0:
        await warning(text='Очищаем папку с кешем..')
        for file in cache_files:
            os.remove(f'cache/{file}')

    await log(text='Попытка авторизации и чтение главной страницы..')
    rip_data = await read_index_page(auth=new_auth)

    if rip_data is not None:
        await log(text='Успешная авторизация, собираем информацию..')
        parse_xml = xmltodict.parse(rip_data)
        save_json = json.dumps(parse_xml)

        await log(text='Обрабатываем полученую информацию..')

        new_json = json.loads(save_json)

        service = new_json.get('service', None)
        if service is not None:
            workspace = new_json['service'].get('workspace', None)
            if workspace is not None:
                collections = new_json['service']['workspace'].get('collection', None)
                if collections is not None:
                    await log(text=f'Начинаю кеширование данных!')

                    tasks_list = []
                    for num, collection in enumerate(collections, start=1):
                        collection_link = collection['@href']
                        tasks_list.append(data_collection(new_auth=new_auth, collection_link=collection_link,
                                                          collections=collections, num=num))


                    if len(tasks_list) > 0:
                        await asyncio.gather(*tasks_list)
                    return True
                else:
                    await error(text='Не могу найти "collection" в словаре! Поправьте ошибку и повторите еще раз..')
                    return False
            else:
                await error(text='Не могу найти "workspace" в словаре! Поправьте ошибку и повторите еще раз..')
                return False
        else:
            await error(text='Не могу найти "service" в словаре! Поправьте ошибку и повторите еще раз..')
            return False
    else:
        await error(text='Не удалось прочитать главную страницу..')
        return False


async def search_in_cache(cache_files: list):
    coincidences = []
    search_text = input(f'Что будем искать ({len(cache_files)})?: ')

    await log(text=f'Начинаем поиск текста "{search_text}" в {len(cache_files)} файлах!')

    for num, file in enumerate(cache_files, start=1):
        async with aiofiles.open(f'cache/{file}', mode='r', encoding='utf-8') as read_file:
            try:
                content = await read_file.read()
            except:
                content = None

        if content is not None:
            if search_text.lower() in content.lower():
                await log(text=f'URL: "{url}{file}" ({num}/{len(cache_files)}) - есть совпадение c '
                               f'текстом: {search_text}!')

                coincidences.append(f'{url}{file}')
        else:
            await log(text=f'Не могу открыть файл "{file}" ({num}/{len(cache_files)}), пропускаем')

    if len(coincidences) > 0:
        await log(text=f'Результат поиска текста: {search_text}, совпадений: {len(coincidences)}/{len(cache_files)}!')
    else:
        await log(text=f'Результат поиска текста: {search_text}, совпадений: {len(coincidences)}/{len(cache_files)}!')


async def process(update_cache=False):
    new_auth = await new_basic_auth(login=login, password=password)

    if update_cache:
        cache_files = os.listdir('cache')
        await log(text=f'Запуск программы с аргументом "кеширование данных"!')
        await updating_cache(new_auth=new_auth, cache_files=cache_files)

    cache_files = os.listdir('cache')
    await search_in_cache(cache_files=cache_files)


async def main(args: list):
    update_cache = False
    if len(args) == 2:
        if args[1] == 'update_cache':
            update_cache = True

    await process(update_cache=update_cache)


if __name__ == "__main__":
    asyncio.run(main(args=sys.argv))