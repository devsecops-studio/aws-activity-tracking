from aws_cdk import (
    Stack,
    aws_dynamodb as dynamodb
)
from constructs import Construct


class AwsActivityDatabaseStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # dynamodb
        self.table = dynamodb.Table(self, 'DynamoDB',
            table_name='aws-activity',
            partition_key=dynamodb.Attribute(name='id', type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name='timestamp', type=dynamodb.AttributeType.NUMBER),
            time_to_live_attribute='ttl',
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )

        # DynamoDB GSI
        self.table.add_global_secondary_index(
            index_name='UserIdentityIndex',
            partition_key=dynamodb.Attribute(name='userIdentity', type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name='timestamp', type=dynamodb.AttributeType.NUMBER),
            non_key_attributes=['id', 'eventName', 'detail'],
            projection_type=dynamodb.ProjectionType.INCLUDE
        )
