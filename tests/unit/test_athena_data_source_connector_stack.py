import aws_cdk as core
import aws_cdk.assertions as assertions

from athena_data_source_connector.athena_data_source_connector_stack import AthenaDataSourceConnectorStack

# example tests. To run these tests, uncomment this file along with the example
# resource in athena_data_source_connector/athena_data_source_connector_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AthenaDataSourceConnectorStack(app, "athena-data-source-connector")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
