from aws_cdk import (
    Stack,
    Duration,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_lambda as lambda_,
    aws_iam as iam
)
from constructs import Construct


class AwsActivityNotificationStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # IAM role
        role = iam.Role(self, 'Role',
            role_name='aws-activity-notification',
            description='Role for functions related to aws-activity-notification',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            inline_policies={
                'CloudwatchLog': iam.PolicyDocument(statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=[
                            'logs:CreateLogGroup'
                        ],
                        resources=[f'arn:aws:logs:{self.region}:{self.account}:*']
                    ),
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=['logs:CreateLogStream', 'logs:PutLogEvents'],
                        resources=[f'arn:aws:logs:{self.region}:{self.account}:log-group:/aws/lambda/*:*']
                    )
                ])
            }
        )

        slack_notify_function=lambda_.Function(self, 'SlackNotifyFunction',
            function_name='aws-activity-slack-notify',
            handler='index.handler',
            runtime=lambda_.Runtime.PYTHON_3_9,
            description='Notify to Slack for AWS activities',
            code=lambda_.Code.from_asset(
                path='assets/lambda-functions/slack-notification'
            ),
            timeout=Duration.minutes(2),
            memory_size=128,
            role=role
        )

        self.topic = sns.Topic(self, 'SnsTopic', 
            topic_name='aws-activity-notification'
        )

        # Lambda should receive only message matching the following conditions on attributes:
        # target: 'Slack' or 'slack' or begins with 'bl'
        # channel: attribute must be present
        self.topic.add_subscription(subscriptions.LambdaSubscription(
            fn=slack_notify_function,
            filter_policy={
                "targets": sns.SubscriptionFilter.string_filter(
                    allowlist=["Slack", "slack"]
                ),
                "channel": sns.SubscriptionFilter.exists_filter()
            }
        ))
