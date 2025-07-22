from aws_cdk import (
    # Duration,
    Stack,
    aws_s3,
    aws_iam,
    RemovalPolicy,
    Duration,
    aws_sam,
    aws_ec2,
    aws_athena,
    Environment,
)
from constructs import Construct

class AthenaDataSourceConnectorStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.env = kwargs["env"]

        # TODO: fill in the parameters below
        self.create_athena_connector(
            spill_bucket_name="",  # "rds-connector-spill-bucket-test",
            db_instance_identifier="",
            connector_lambda_name="",  # "rds-connector-lambda",
            read_only_user_secret_name="",
            db_reader_endpoint="",
            db_port=5432,
            database_name="",
            vpc_id="",
            security_group_id="",
        )

    def create_athena_connector(
        self,
        spill_bucket_name: str,
        db_instance_identifier: str,
        connector_lambda_name: str,
        read_only_user_secret_name: str,
        db_reader_endpoint: str,
        db_port: int,
        database_name: str,
        vpc_id: str,
        security_group_id: str,
    ) -> None:
        self.spill_bucket = self.create_data_source_connector_spill_bucket(
            spill_bucket_name
        )
        self.connector_lambda_role = self.createconnector_lambda_role(
            self.spill_bucket, 
            db_instance_identifier=db_instance_identifier,
        )
        
        self.connector_lambda_name = connector_lambda_name

        self.athena_connector_app = self.create_data_source_connector(
            read_only_user_secret_name=read_only_user_secret_name,
            endpoint=db_reader_endpoint,
            port=db_port,
            database_name=database_name,
            vpc=aws_ec2.Vpc.from_lookup(
                scope=self, 
                id="rds-connector-vpc",
                vpc_id=vpc_id,
            ),
            security_group_id=security_group_id,
            connector_lambda_role=self.connector_lambda_role,
            connector_lambda_name=self.connector_lambda_name,
        )
        
        self.athena_data_source = self.create_athena_data_source(
            env=self.env,
            connector_lambda_name=self.connector_lambda_name,
        )
        self.athena_data_source.add_dependency(self.athena_connector_app)

    def create_data_source_connector_spill_bucket(self, spill_bucket_name: str) -> aws_s3.Bucket:
        spill_bucket_name = "connector-spill-bucket-test"

        return aws_s3.Bucket(
            scope=self,
            id=spill_bucket_name,
            bucket_name=spill_bucket_name,
            removal_policy=RemovalPolicy.DESTROY,
            lifecycle_rules=[aws_s3.LifecycleRule(expiration=Duration.days(1))],
        )

    def createconnector_lambda_role(self, spill_bucket: aws_s3.Bucket, db_instance_identifier: str) -> aws_iam.Role:
        role_name = "connector-role"
        connector_role = aws_iam.Role(
            scope=self,
            id=role_name,
            role_name=role_name,
            assumed_by=aws_iam.ServicePrincipal("lambda.amazonaws.com"),  # type: ignore
        )

        connector_role.add_managed_policy(
            aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
        )
        connector_role.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name("AmazonAthenaFullAccess"))
        connector_role.add_to_policy(
            statement=aws_iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"], resources=["*"], effect=aws_iam.Effect.ALLOW
            )
        )

        connector_role.add_to_policy(
            statement=aws_iam.PolicyStatement(
                sid="RDSReadOnlyAccess",
                resources=[
                    # f"arn:aws:rds:{self.env.region}:{self.env.account}:cluster:{cluster_id}*",  # Uncomment if using RDS clusters
                    f"arn:aws:rds:{self.env.region}:{self.env.account}:db:{db_instance_identifier}",
                ],
                actions=[
                    "rds:List*",
                    "rds:Describe*",
                    "rds-db:connect",
                    "rds-data:ExecuteSql",
                    "rds-data:ExecuteStatement",
                    "rds-data:BatchExecuteStatement",
                ],
                effect=aws_iam.Effect.ALLOW,
            )
        )

        connector_role.add_to_policy(
            statement=aws_iam.PolicyStatement(
                sid="CreateConnection",
                resources=["*"],
                actions=[
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:CreateNetworkInterface",
                    "ec2:DeleteNetworkInterface",
                    "ec2:DescribeInstances",
                    "ec2:AttachNetworkInterface",
                ],
            )
        )

        connector_role.add_to_policy(
            statement=aws_iam.PolicyStatement(
                sid="SpillBucketAccess",
                resources=[spill_bucket.bucket_arn, f"{spill_bucket.bucket_arn}/*"],
                actions=[
                    "s3:Get*",
                    "s3:List*",
                    "s3:Put*",
                    "s3:DeleteObject*",
                ],
            )
        )

        return connector_role

    def create_data_source_connector(
        self,
        read_only_user_secret_name: str,
        endpoint: str,
        port: int,
        database_name: str,
        vpc: aws_ec2.IVpc,
        security_group_id: str,
        connector_lambda_role: aws_iam.IRole,
        connector_lambda_name: str,
    ) -> aws_sam.CfnApplication:

        # Note: double literal variable notation is required for specifying the secret
        jdbc_connection_string = f"postgres://jdbc:postgresql://{endpoint}:{port}/{database_name}?${{{read_only_user_secret_name}}}"
        # to enable SSL in the connection string add to connection string:
        # "&sslmode=verify-ca&sslfactory=org.postgresql.ssl.DefaultJavaSSLFactory"

        subnet_ids = vpc.select_subnets(subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_EGRESS).subnet_ids

        return aws_sam.CfnApplication(
            scope=self,
            id="rds-connector-application",
            location=aws_sam.CfnApplication.ApplicationLocationProperty(
                application_id="arn:aws:serverlessrepo:us-east-1:292517598671:applications/AthenaPostgreSQLConnector",
                semantic_version="2024.38.1",
            ),
            parameters={
                "SpillBucket": self.spill_bucket.bucket_name,
                "SecretNamePrefix": read_only_user_secret_name,  # name or prefix of the secret
                "LambdaFunctionName": connector_lambda_name,
                "CompositeHandler": "PostGreSqlCompositeHandler",  # to access single instance using DefaultConnectionString
                "LambdaRoleARN": connector_lambda_role.role_arn,
                "DefaultConnectionString": jdbc_connection_string,
                "SecurityGroupIds": security_group_id,
                "SubnetIds": ",".join(subnet_ids),
            },
            # tags=tags,
        )

    def create_athena_data_source(self, env: Environment, connector_lambda_name: str) -> aws_athena.CfnDataCatalog:
        connector_lambda_arn = f"arn:aws:lambda:{env.region}:{env.account}:function:{connector_lambda_name}"
        # data_source_tags = [{"key": k, "value": v} for k, v in tags.items()]

        data_source_id = "rds-connector-data-source"
        return aws_athena.CfnDataCatalog(
            scope=self,
            id=data_source_id,
            type="LAMBDA",
            name=data_source_id,
            parameters={"function": connector_lambda_arn},
            # tags=data_source_tags,
        )
