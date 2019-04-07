import logging
import random

from fastapi import FastAPI
from google.cloud import firestore
from google.cloud.exceptions import NotFound
from pydantic import BaseModel
from requests import Response, RequestException, get
from starlette.status import HTTP_200_OK
from twilio.rest import Client
from ujson import loads

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)

db = firestore.Client()
api_keys_ref = db.collection(u'api_keys').document(u'gvRhG4XnOHccmty4UoBU')

try:
    doc = api_keys_ref.get()
    API_KEYS = doc.to_dict()
    logging.info('API Keys successfully retrieved.')
except NotFound as e:
    API_KEYS = {}
    logging.error('The API keys could not be retrieved from Firestore!')

app = FastAPI(title='Fact Sender',
              description='This is an API that handles constructing and sending SMS messages via'
                          'an automated task queue.')


class Task(BaseModel):
    fact_type: str
    target_name: str
    target_phone: str
    account_sid: str
    is_first_task: bool


async def get_random_path() -> str:
    try:
        resp: Response = get(url='https://fact-getter-dot-facts-sender.appspot.com/openapi.json')
    except RequestException as e:
        logging.error('Response exception: ' + str(e))
        return '/kanye'

    if resp.status_code != 200:
        logging.error('Abnormal status code in response. Code: ' + str(resp.status_code))
        return '/kanye'

    return random.choice([path for path in loads(resp.content)['paths'].keys()])


async def get_fact(task_payload: Task) -> str or None:
    if task_payload.fact_type == 'random':
        task_payload.fact_type = await get_random_path()
    try:
        resp: Response = get(url='https://fact-getter-dot-facts-sender.appspot.com' + task_payload.fact_type)
    except RequestException as e:
        logging.error('Response exception: ' + str(e))
        return None

    if resp.status_code != 200:
        logging.error('Abnormal status code in response. Code: ' + str(resp.status_code))
        return None

    return loads(resp.content)['fact']


async def send_fact(fact: str, task_payload: Task) -> None:
    auth_token = API_KEYS['twilio_auth_token']
    client = Client(task_payload.account_sid, auth_token)

    if task_payload.is_first_task:
        body = 'Hi ' + task_payload.target_name + \
               ', thanks for signing up for facts! You have signed up for: 3 Years ' \
               'of facts at a rate of: 1 per hour. As a reminder, there is no way to cancel! ' \
               'Enjoy your facts! ' + fact
    else:
        body = 'Hi ' + task_payload.target_name + ', enjoy your fact! ' + fact,

    message = client.messages.create(
        body=body,
        from_='+18164664798',
        to=task_payload.target_phone
    )


@app.post("/send", status_code=HTTP_200_OK)
async def send_sms(task_payload: Task):
    fact: str or None = await get_fact(task_payload)

    if fact:
        await send_fact(fact, task_payload)

    return {}


@app.get("/_ah/warmup", status_code=HTTP_200_OK, include_in_schema=False)
def warmup():
    return {'Response': '200'}
