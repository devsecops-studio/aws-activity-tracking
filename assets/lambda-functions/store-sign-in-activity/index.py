import logging
import time
from dateutil import parser
import boto3
import os
import json


logging.basicConfig(level=logging.DEBUG)
logger=logging.getLogger(__name__)

def handler(event, context):
    # logger.setLevel(logging.DEBUG)
    
    # 365 days
    ttl = int(time.time()) + 365 * 24 * 60 * 60
    timestamp = int(parser.parse(event['time']).timestamp())

    event_detail = event['detail']
    event_name = event_detail['eventName']
    user_identity_type = event_detail['userIdentity']['type']

    user_identity = f'{user_identity_type}#Unknown'
    if user_identity_type == 'IAMUser':
        user_identity = f'{user_identity_type}-{event_detail["userIdentity"]["userName"]}'
    elif user_identity_type == 'Root':
        user_identity = f'{user_identity_type}#Root'
    elif user_identity == 'AssumedRole':
        user_identity = f'{user_identity_type}#{event_detail["userIdentity"]["sessionContext"]["sessionIssuer"]["userName"]}'

    event = {**event, 'eventName': event_name, 'userIdentity': user_identity, 'timestamp': timestamp, 'ttl': ttl}
    logger.debug(json.dumps(event))

    # dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.getenv('DYNAMODB_TABLE_NAME'))
    table.put_item(Item=event)
    logger.info(f'Activity has been stored into database successfully')

    return event
