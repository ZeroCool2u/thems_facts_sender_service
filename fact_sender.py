import logging
import os
import random
from fastapi import FastAPI
from google.cloud import firestore
from google.cloud.exceptions import NotFound
from orjson import loads
from pydantic import BaseModel
from requests import Response, RequestException, get
from starlette.status import HTTP_200_OK
from twilio.rest import Client

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)

if not os.getenv('GAE_ENV', '').startswith('standard') and os.getenv('GITHUB_WORKFLOW') is None:
    os.environ[
        'GOOGLE_APPLICATION_CREDENTIALS'] = r'/home/theo/PycharmProjects/thems_facts/sender_service/facts-sender-owner.json'

elif os.getenv('GITHUB_WORKFLOW') is not None:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join(os.getenv('HOME'), 'facts-sender-owner.json')


def gcp_support() -> dict:

    try:
        db = firestore.Client()
        api_keys_ref = db.collection(u'api_keys').document(u'gvRhG4XnOHccmty4UoBU')
        doc = api_keys_ref.get()
        api_keys = doc.to_dict()
        logging.info('API Keys successfully retrieved.')
        return api_keys
    except NotFound as e:
        api_keys = {'twilio_sid': 'TWILIO_SID_NOT_FOUND'}
        logging.error(f'The API keys could not be retrieved from Firestore: {str(e)}')
        return api_keys
    except Exception as e:
        api_keys = {'twilio_sid': 'TWILIO_SID_NOT_FOUND'}
        logging.error(f'Firestore client failed to init. The fact sender service will run in local only mode: {str(e)}')
        return api_keys


API_KEYS = gcp_support()

app = FastAPI(title='Fact Sender',
              description='This is an API that handles constructing and sending SMS messages via'
                          'an automated task queue.')


class Task(BaseModel):
    fact_type: str
    target_name: str
    target_phone: str
    account_sid: str
    is_first_task: bool
    task_queue_size: int


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
               ', thanks for signing up for alternative facts! You have signed up for: ' + str(
            task_payload.task_queue_size) + ' Years ' \
                                            'of facts at a rate of: 1 per hour. As a reminder, there is no way to cancel! ' \
                                            'Enjoy your alternative facts! \n ' + fact
    else:
        body = 'Hi ' + task_payload.target_name + ', enjoy your alternative fact! \n ' + fact,

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
    else:
        logging.error(f"Failed to retrieve a fact to send. This task will be discarded and fail to execute."
                      f"Target Name: {task_payload.target_name} Target Number: {task_payload.target_phone} "
                      f"Fact Type: {task_payload.fact_type}")

    return {}


@app.get("/_ah/warmup", status_code=HTTP_200_OK, include_in_schema=False)
def warmup():
    return {'Response Code': '418'}
