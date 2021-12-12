import aws_cdk as core
import aws_cdk.assertions as assertions

from aws_activity_tracking.aws_activity_tracking_stack import AwsActivityTrackingStack

# example tests. To run these tests, uncomment this file along with the example
# resource in aws_activity_tracking/aws_activity_tracking_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AwsActivityTrackingStack(app, "aws-activity-tracking")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
