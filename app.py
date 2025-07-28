#!/usr/bin/env python3
import os

import aws_cdk as cdk
from constructs import Construct

from athena_data_source_connector.rds_database_stack import RdsNetworkStack, RdsDatabaseStack
from athena_data_source_connector.athena_data_source_connector_stack import AthenaDataSourceConnectorStack


app = cdk.App()
env = cdk.Environment(
    account="120964623235",  # os.getenv('CDK_DEFAULT_ACCOUNT'), 
    region="us-east-1"  # os.getenv('CDK_DEFAULT_REGION')
)

db_network_stack = RdsNetworkStack(app, "RdsNetworkStack", env=env)
db_stack = RdsDatabaseStack(app, "RdsDatabaseStack", env=env)
db_stack.add_dependency(db_network_stack)

AthenaDataSourceConnectorStack(app, "AthenaDataSourceConnectorStack", env=env)

app.synth()

# TODO: documentation REAMDME.md and Medium, refer each one