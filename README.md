# Athena Data Source Connector for RDS using Python CDK

## In essence

Straight to the code:

AWS DataSource Connector
```python
def create_athena_connector(...) -> None:
    self.spill_bucket = self.create_data_source_connector_spill_bucket(...)
    
    self.connector_lambda_role = self.createconnector_lambda_role(...)
    
    ...
    
    self.athena_connector_app = self.create_data_source_connector(...)
    
    self.athena_data_source = self.create_athena_data_source(...)

    self.athena_data_source.add_dependency(self.athena_connector_app)


def create_data_source_connector(...) -> aws_sam.CfnApplication:

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
```

Set up database secret to use for connector
```python
def read_only_user_secret(...) -> aws_secretsmanager.Secret:
    secret = aws_secretsmanager.Secret(
        scope=self,
        id=secret_id,
        secret_name=secret_id,
        generate_secret_string=aws_secretsmanager.SecretStringGenerator(
            generate_string_key="password",
            secret_string_template=json.dumps({"username": f"read_only_user"}),
        ),
    )

    return secret
```

### !Important! 
Set up IAM permission for connector Lambda to write to Spill Bucket
```python

```

## TL;DR The Story behind

Back then I was tasked to enable federated queries for Athena. 
Federated queries enabled us to combine multiple datasources in 
a single query, this way we were able to join data from an RDS 
database with data from S3 that could be accessed via Glue Data
Catalog.

To do so I needed to set up a Data Source Connector for Athena.
For the first attempt I went to the management console I put 
managed to quickly set it up by using clickops.

Here is the [guide](https://medium.com/piateamtech/how-to-use-athena-jdbc-connector-for-rds-database-from-athena-on-aws-environment-25c282b6fdc2) I used that gave me support on the journey:


The next step was implementing using Python CDK which seemed
a harder problem. First thing I looked at was the documentation
of the data source connector itself, but I found only [Level 1 Cfn
construct that](https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_appconfig/CfnApplication.html) is vaguely documented. Also, to create the connector I needed an AWS Lambda
Function wrapped in AWS SAM (Serverless Application Model), which
seemed like another barely documented service that I had to use.
At that time LLMs were in their early steps, so I was using the
OG internet search engine to get an example on implementing it.

Fortunately, I found an [example written in TypeScript](https://aws.plainenglish.io/aws-cdk-athena-rds-ddfa2a5859be). Strangely,
the configuration had to be provided using a JSON dictionary.
I felt saved. I managed to implement it by translating the 
Typescript code and using Python CDK contstructs.

Everything was working really well, until one day someone
reach out to me for help. The issue was that the query did
not give back all the columns, then we started getting access
denied error for the database tables.

Tried to investigate it, but did not find any database setting
that could cause it. Also, there was no recent infrastructure
change that could possibly cause denied table access.

So as final chance, AWS Support was contacted. It was a really
good experience. They replied fast to the request and swiftly
found out that the root cause of the error is the lacking IAM
permission for the connector Lambda to write to the S3 spill
bucket.

Queries that have a query result [bigger than 6 MB are stored
in the spill bucket](https://repost.aws/questions/QUa5rsUCCaQE-L0_BryLhZ7A/athena-spill-bucket-issue-dynamo-connect-lambda). When the connector was initially tested, we
used only small queries that did not exceed this limit. After it
when we were giving it more realistic queries, we hit the limit
and got the misterious error.

Although, the debugging process was not easy and felt lost beacuse
of the inability to access anything from the console, fortunately,
it turned out as a success story. Besides it was a really good 
experience with AWS Support, that I can just recommend in case
feeling stuck and lonely, and nor the internet is our friend.
