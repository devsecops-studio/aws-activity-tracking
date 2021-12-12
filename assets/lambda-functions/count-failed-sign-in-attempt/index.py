import logging
import time
import boto3
import os
from boto3.dynamodb.conditions import Key, Attr


logging.basicConfig(level=logging.DEBUG)
logger=logging.getLogger(__name__)

def handler(event, context):
    logger.setLevel(logging.DEBUG)

    TABLE_NAME = os.getenv('DYNAMODB_TABLE_NAME')
    user_identity_index = {
        'name': 'UserIdentityIndex',
        'hash_key': 'userIdentity',
        'sort_key': 'timestamp'
    }
        

    user_identity = event['userIdentity']
    
    # last 1 hour = now - 1h
    # seconds
    now = int(time.time())
    last_one_hour = now - 1 * 60 * 60
    
    # table = boto3.resource('dynamodb', region_name='us-east-1').Table(TABLE_NAME)
    table = boto3.resource('dynamodb').Table(TABLE_NAME)
    results = []
    last_evaluated_key = None
    
    while True:
        if not last_evaluated_key:
            response = table.query(
                IndexName=user_identity_index['name'],
                KeyConditionExpression=Key(user_identity_index['hash_key']).eq(user_identity) & Key(user_identity_index['sort_key']).between(last_one_hour, now),
                FilterExpression=Attr('eventName').eq('ConsoleLogin') & Attr('detail.responseElements.ConsoleLogin').eq('Failure'),
                ScanIndexForward=False,
            )
        else: 
            response = table.query(
                IndexName=user_identity_index['name'],
                KeyConditionExpression=Key(user_identity_index['hash_key']).eq(user_identity) & Key(user_identity_index['sort_key']).between(last_one_hour, now),
                FilterExpression=Attr('eventName').eq('ConsoleLogin') & Attr('detail.responseElements.ConsoleLogin').eq('Failure'),
                ScanIndexForward=False,
                ExclusiveStartKey=last_evaluated_key
            )
        results.extend(response['Items'])

        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break
    logger.info(len(results))
    
    event['failedAttempts'] = len(results)
    logger.debug(event)
    
    return event
