# Athena Data Source Connector for RDS using Python CDK

This repository contains a working example of how to set up an **AWS Athena Data Source Connector** for **Amazon RDS** using **Python CDK**. It enables **federated queries** in Athena, allowing you to join data from RDS and S3 (via Glue Data Catalog).

> 📖 Read the full story behind this implementation in the Medium blog post:
[Building an AWS Athena RDS Connector with Python CDK](https://medium.com/@attila9778/building-an-aws-athena-rds-connector-with-python-cdk-lessons-from-the-trenches-e06cb1aff885)

## 📁 Repository Structure
```
athena_data_source_connector/
├── rds_database_vpc_stack.py          # Sample CDK stack to set up Aurora Serverless RDS with a separate VPC
├── athena_data_source_connector_stack.py  # Full implementation of the Athena Data Source Connector
└── README.md                          # This file
```

## 🚀 Key Features

Python CDK implementation of Athena RDS Connector using aws_sam.CfnApplication
Aurora Serverless RDS setup with isolated VPC for testing
IAM permissions for spill bucket access
Secrets Manager integration for secure database credentials
Athena Data Catalog registration for Lambda-based connector

## 🔍 Background & Motivation
At the time of implementation, there were no Python CDK examples available for setting up Athena Data Source Connectors. Most resources were in TypeScript, and the CfnApplication documentation was sparse.

This project was built by translating a TypeScript example and experimenting with CDK constructs to create a reusable, automated setup.

## 🐛 Common Pitfall

Make sure to grant write permissions to the S3 spill bucket for the connector Lambda. Without this, queries exceeding the spill threshold will fail silently or return incomplete results.

```python
connector_role.add_to_policy(
    aws_iam.PolicyStatement(
        sid="SpillBucketAccess",
        resources=[spill_bucket.bucket_arn, f"{spill_bucket.bucket_arn}/*"],
        actions=["s3:Put*", "s3:DeleteObject*"],
    )
)
```

## 📚 References

* [Medium blog post on manual setup](https://medium.com/piateamtech/how-to-use-athena-jdbc-connector-for-rds-database-from-athena-on-aws-environment-25c282b6fdc2)
* [TypeScript CDK example](https://aws.plainenglish.io/aws-cdk-athena-rds-ddfa2a5859be)
* [CfnApplication Python CDK Docs](https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_appconfig/CfnApplication.html)
