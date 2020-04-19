from requests import request, Session
from itertools import permutations
from string import ascii_lowercase
import asyncio
from time import time

cyryllic_letters = 'йцукенгшщзхъфывапролджэячсмитьбю'
queries = tuple([''.join(x) for x in permutations(cyryllic_letters, 3)])
responses = {}
start_time = time()

for query in queries[:50]:
    session = Session()
    session.head('https://allo.ua/')
    response = session.post(
        url='https://allo.ua/ua/catalogsearch/ajax/suggest/',
        data={
            'q': '{}'.format(query.encode()),
            'isAjax': 1,
        },
        headers={
            'Referer': 'https://allo.ua/'
        }
    )
    rsp_json = response.json()
    #sleep(5)
    try:
        responses.update({query: rsp_json.get('query', rsp_json.get('products'))})
    except:
        print(len(responses))
        print('; '.join(responses))
        # new session each time - 23.8, 24.5, 23.4
        #

loop = asyncio.get_event_loop()
print('It took {} seconds'.format(time() - start_time))
print('Ended: {}'.format(len(responses)))
print('; '.join(responses))
# import pdb; pdb.set_trace()