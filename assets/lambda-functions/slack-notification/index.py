import logging
import requests
import json
from datetime import datetime


logging.basicConfig(level=logging.DEBUG)
logger=logging.getLogger(__name__)

SLACK_CHANNELS = {
    'alarm-aws': 'https://hooks.slack.com/services/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'
}

def handler(event, context):
    logger.setLevel(logging.DEBUG)
    logger.debug(event)

    message = json.loads(event['Records'][0]['Sns']['Message'])
    message_attributes = event['Records'][0]['Sns']['MessageAttributes']

    fields = []

    text = 'See detail below'
    reason = message_attributes['reason']['Value']
    if reason == 'ManyFailedSignInAttempt':
        text = 'There are many failed sign-in attempts in last one hour'
        fields.extend([
            {
                'title': 'User',
                "value": message['detail']['userIdentity']['userName'],
                'short': True
            },
            {
                'title': 'Failed attempt',
                "value": message['failedAttempts'],
                'short': True
            }
        ])
    elif reason == 'NoMFAUsed':
        text = 'Detected MFA not used'
        fields.extend([
            {
                'title': 'User',
                "value": message['detail']['userIdentity']['userName'],
                'short': True
            },
            {
                'title': 'Event name',
                "value":  message['eventName'],
                'short': True
            }
        ])
    elif reason == 'RootActivity':
        text = 'Detected Root activity'
        fields.extend([
            {
                'title': 'User',
                "value": 'Root',
                'short': True
            },
            {
                'title': 'Event name',
                "value":  message['eventName'],
                'short': True
            }
        ])

    fields.extend([
        {
            'title': 'IP address',
            "value": message['detail']['sourceIPAddress'],
            'short': True
        },
        {
            'title': 'Severity',
            "value": message_attributes['severity']['Value'],
            'short': True
        },
        {
            'title': 'Event ID',
            "value": message['id'],
            'short': True
        }
    ])

    send_slack(
        channel=message_attributes['channel']['Value'],
        title=text,
        fields=fields,
        severity=message_attributes['severity']['Value']
    )

def send_slack(channel: str, title: str, fields: list, severity='Medium'):
    color = '#36a64f'
    if severity == 'Medium':
        color = '#edaf2b'
    elif severity == 'High':
        color = '#cc5f00'
    elif severity == 'Critical':
        color = '#cc0000'
    
    payload = {
        'username': 'Cloud Guard',
        'attachments': [{
            'title': title,
            'color': color,
            'fields': fields,
            'footer': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'fallback': 'Required plain-text summary of the attachment.'
        }]
    }
    if severity.lower() == 'critical':
        payload['attachments'][0].update({'pretext': '<!here>'})

    logger.info(payload)
    requests.post(SLACK_CHANNELS.get(channel), data=json.dumps(payload), headers={'Content-Type': 'application/json'})
    logger.info('Send Slack notify successfully')
