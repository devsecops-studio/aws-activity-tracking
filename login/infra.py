from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_logs as logs,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_events as events,
    aws_events_targets as events_targets,
    aws_sns as sns
)
from constructs import Construct


class AwsSignInActivityStack(Stack):
    def __init__(self, scope: Construct, id: str, dynamodb_table: dynamodb.ITable, notification_topic: sns.ITopic, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Cloudwatch log
        log_group = logs.LogGroup(self, 'CloudWatchLogGroup',
            log_group_name='aws-sign-in-activity',
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY
        )

        # IAM role
        role = iam.Role(self, 'Role',
            role_name='aws-sign-in-activity',
            description='Role for functions related to aws-sign-in activities',
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
                ]),
                'DynamoDBWrite': iam.PolicyDocument(statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=['dynamodb:BatchWriteItem', 'dynamodb:PutItem', 'dynamodb:UpdateItem'],
                        resources=[dynamodb_table.table_arn]
                    )
                ]),
                'DynamoDBRead': iam.PolicyDocument(statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=['dynamodb:BatchGetItem', 'dynamodb:GetItem', 'dynamodb:Scan', 'dynamodb:Query'],
                        resources=[dynamodb_table.table_arn, f'{dynamodb_table.table_arn}/index/*']
                    )
                ])
            }
        )

        # Step function
        store_job = tasks.LambdaInvoke(self, 'Store activity',
            lambda_function=lambda_.Function(self, 'StoreActivityFunction',
                function_name='store-aws-sign-in-activity',
                handler='index.handler',
                runtime=lambda_.Runtime.PYTHON_3_9,
                description='Store AWS sign-in activities into DynamoDB',
                code=lambda_.Code.from_asset(
                    path='assets/lambda-functions/store-sign-in-activity'
                ),
                environment={
                    'DYNAMODB_TABLE_NAME': dynamodb_table.table_name
                },
                timeout=Duration.seconds(15),
                memory_size=128,
                role=role
            ),
            output_path='$.Payload'
        )

        succeed_job = sfn.Succeed(self, 'Do nothing')

        count_failed_sign_in_job = tasks.LambdaInvoke(self, 'Count failed sign-in attempt',
            lambda_function=lambda_.Function(self, 'CountFailedSignInFunction',
                function_name='count-failed-sign-in-attempt',
                handler='index.handler',
                runtime=lambda_.Runtime.PYTHON_3_9,
                description='Count failed AWS sign-in attempts',
                code=lambda_.Code.from_asset(
                    path='assets/lambda-functions/count-failed-sign-in-attempt'
                ),
                environment={
                    'DYNAMODB_TABLE_NAME': dynamodb_table.table_name
                },
                timeout=Duration.minutes(3),
                memory_size=128,
                role=role
            ),
            output_path='$.Payload'
        ).next(
            sfn.Choice(self, 'More than 2 attempts?').when(
                condition=sfn.Condition.number_greater_than('$.failedAttempts', 2),
                next=tasks.SnsPublish(self, 'Alert on many failed sign-in attempts',
                    topic=notification_topic,
                    message=sfn.TaskInput.from_json_path_at('$'),
                    message_attributes={
                        'severity': tasks.MessageAttribute(value='High'),
                        'reason': tasks.MessageAttribute(value='ManyFailedSignInAttempt'),
                        'targets': tasks.MessageAttribute(value=['Slack']),
                        'channel': tasks.MessageAttribute(value='alarm-aws')
                    }
                )
            ).otherwise(succeed_job)
        )

        check_mfa = sfn.Choice(self, 'MFA used?').when(
            condition=sfn.Condition.string_equals('$.detail.additionalEventData.MFAUsed', 'Yes'),
            next=succeed_job
        ).otherwise(
            tasks.SnsPublish(self, 'Alert on no MFA',
                topic=notification_topic,
                message=sfn.TaskInput.from_json_path_at('$'),
                message_attributes={
                    'severity': tasks.MessageAttribute(value='Medium'),
                    'reason': tasks.MessageAttribute(value='NoMFAUsed'),
                    'targets': tasks.MessageAttribute(value=['Slack']),
                    'channel': tasks.MessageAttribute(value='alarm-aws')
                }
            )
        )

        check_login = sfn.Choice(self, 'Login failed?').when(
            condition=sfn.Condition.string_equals('$.detail.responseElements.ConsoleLogin', 'Failure'),
            next=count_failed_sign_in_job
        ).otherwise(check_mfa)

        sign_in_activity = sfn.Choice(self, 'Sign-in activity?').when(
            sfn.Condition.string_equals('$.eventName', 'ConsoleLogin'),
            next=check_login
        ).otherwise(succeed_job)

        check_root_user = sfn.Choice(self, 'Root user?').when(
            condition=sfn.Condition.string_equals('$.detail.userIdentity.type', 'Root'), 
            next=tasks.SnsPublish(self, 'Alert on Root activity',
                topic=notification_topic,
                message=sfn.TaskInput.from_json_path_at('$'),
                message_attributes={
                    'severity': tasks.MessageAttribute(value='Critical'),
                    'reason': tasks.MessageAttribute(value='RootActivity'),
                    'targets': tasks.MessageAttribute(value=['Slack']),
                    'channel': tasks.MessageAttribute(value='alarm-aws')
                }
            )
        ).when(
            sfn.Condition.string_equals('$.detail.userIdentity.type', 'IAMUser'), 
            sign_in_activity
        )

        definition = store_job.next(check_root_user)

        state_machine = sfn.StateMachine(self, 'StepFunction',
            state_machine_name='aws-sign-in-activity',
            state_machine_type=sfn.StateMachineType.STANDARD,
            definition=definition,
            logs=sfn.LogOptions(
                destination=log_group,
                level=sfn.LogLevel.ERROR
            )
        )

        # event bridge
        events.Rule(self, 'EventBridgeRule',
            rule_name='aws-sign-in-activity',
            description='Rule of AWS sign-in activities',
            event_pattern=events.EventPattern(
                detail_type=[
                    'AWS API Call via CloudTrail',
                    'AWS Console Sign In via CloudTrail'
                ],
                source=['aws.signin']
            ),
            targets=[events_targets.SfnStateMachine(
                machine=state_machine,
                retry_attempts=3
            )]
        )
