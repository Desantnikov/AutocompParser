import asyncio
import json
import timeit
from itertools import permutations
from string import ascii_lowercase

from aiohttp import ClientSession
from aiohttp_proxy import ProxyConnector
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import func

import db

DB_Session = sessionmaker(bind=db.engine)
db_session = DB_Session()

all_letters = 'йцукенгшщзхъфывапролджэячсмитьбю' + ascii_lowercase
queries = tuple([''.join(x) for x in permutations(all_letters, 3)])

possible_queries_amount, db_rows_amount = len(queries), db_session.query(db.Query).count()
if possible_queries_amount != db_rows_amount:
    usr_rsp = input('Amount of database rows ({}) != amount of possible queries ({}). Recreate database? (Y/N)'.
                    format(db_rows_amount, possible_queries_amount))

    if usr_rsp == 'Y':
        try:
            num_rows_deleted = db_session.query(db.Query).delete()
            autocompletions = [db.Query(query) for query in queries]

            db_session.bulk_save_objects(autocompletions)
            db_session.commit()
            print('Database recreated and now consists of {} rows'.format(db_session.query(db.Query).count()))
        except Exception as e:
            print('Recreating database failed with error: {}; Rolling changes back'.format(e.args))
            db_session.rollback()

    elif usr_rsp == 'N':
        print('As you wish')
    else:
        print('Wrong input')
        exit()

# these proxies are bad but free, better to update before launch
proxies = ('socks4://77.93.42.134:46235', 'http://194.32.136.127:8081', 'http://91.206.30.218:3128',
           'http://31.135.150.30:8080', 'http://194.79.20.30:8080', 'https://85.223.157.204:40329',
           'http://194.44.87.245:8080', 'https://188.163.170.130:41209', 'http://91.194.239.122:8080')


async def fetch_all(queries):
    tasks, sessions = [], []
    start = 0

    for proxy in proxies:
        print('Proxy ip: {}'.format(proxy))
        connector = ProxyConnector.from_url(proxy)
        session = ClientSession(connector=connector)
        sessions.append(session)

        for query in queries[start:start + 5]:  # more than 5 requests from IP -> 429
            task = asyncio.ensure_future(fetch(query, session))
            tasks.append(task)
        start += 5

    await asyncio.gather(*tasks)
    await asyncio.gather(*[asyncio.ensure_future(session.close()) for session in sessions])


async def fetch(query, session):
    try:
        async with session.post(
                url='https://allo.ua/ua/catalogsearch/ajax/suggest/?currentTheme=main&currentLocale=uk_UA',
                params={
                    'q': query.text,
                    'isAjax': 1,
                },
                headers={
                    'Referer': 'https://allo.ua/',
                }, timeout=20) as response:

            resp = await response.read()
            resp = json.loads(resp)

            try:
                autocompletion_texts_list = [d['name'] for d in resp['products']]
            except:
                # Not all queries returns responses even when typing it on site via browser (ex. йкы)
                autocompletion_texts_list = ['No response for this query']

            autocompletion_objects_list = [db.Autocompletion(text, query.id) for text in autocompletion_texts_list]
            db_session.bulk_save_objects(autocompletion_objects_list)
            db_session.commit()

            print('Status: + ; Query {}; Rsp: {}; Proxy: {}'.format(query.text, autocompletion_texts_list,
                                                                    session._connector.proxy_url))
            return resp

    except Exception as e:
        db_session.rollback()
        print('Status: - ; Query {}; Proxy: {}; Error: {}'.format(query.text, session._connector.proxy_url, e))
        return None


def make_fetching_iteration():
    start_time = timeit.default_timer()
    requests_per_iteration = 5 * len(proxies)  # allo.ua returns 429 if more than 5 requests from one IP

    # get all unfilled queries from db (Queries with blank Autocompletions)
    queries = db_session.query(db.Query).join(db.Autocompletion, isouter=True).group_by(db.Query). \
        having(~func.count(db.Query.autocompletions)).all()

    loop = asyncio.get_event_loop()
    while queries:
        future = asyncio.ensure_future(fetch_all(queries[:requests_per_iteration]))
        loop.run_until_complete(future)
        queries = queries[requests_per_iteration:]

    tot_elapsed = timeit.default_timer() - start_time
    print('Iteration took: {} time'.format(tot_elapsed))


if __name__ == '__main__':
    while queries:
        queries = db_session.query(db.Query).join(db.Autocompletion, isouter=True).group_by(db.Query). \
            having(~func.count(db.Query.autocompletions)).all()
        make_fetching_iteration()
