#!/usr/bin/env python3
import os

import aws_cdk as cdk

from database import AwsActivityDatabaseStack
from notification import AwsActivityNotificationStack
from login import AwsSignInActivityStack


app = cdk.App()

us_east_1 = cdk.Environment(region=os.environ["CDK_DEFAULT_REGION"], account=os.getenv('CDK_DEFAULT_ACCOUNT'))

# database
db_stack = AwsActivityDatabaseStack(app, 'aws-activity-db', env=us_east_1,
    description='Tracking AWS activities for security compliance'
)

# notification
notification_stack = AwsActivityNotificationStack(app, 'aws-activity-notification', env=us_east_1,
    description='Notify AWS activities for security compliance'
)

# sign-in activity
AwsSignInActivityStack(app, 'aws-sign-in-activity', env=us_east_1,
    dynamodb_table=db_stack.table,
    notification_topic=notification_stack.topic,
    description='Tracking AWS sign-in activities for security compliance'
)

app.synth()
