from aws_cdk import Stack, RemovalPolicy
from aws_cdk.aws_rds import DatabaseCluster, DatabaseClusterEngine, AuroraPostgresEngineVersion, ClusterInstance
from aws_cdk.aws_ec2 import (
    Vpc,
    SubnetType,
    SubnetConfiguration,
    SubnetSelection,
    IpAddresses,
    SecurityGroup,
    Peer,
    Port,
)

from constructs import Construct


class RdsNetworkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = Vpc(
            self, 
            id="RdsDatabaseVpc",
            vpc_name="RdsDatabaseVpc",
            create_internet_gateway=False,
            ip_addresses=IpAddresses.cidr("10.0.0.0/22"),  # Adjust CIDR as needed
            max_azs=2,
            subnet_configuration=[
                SubnetConfiguration(
                    subnet_type=SubnetType.PUBLIC,
                    name="Public",
                    cidr_mask=24
                ),
                SubnetConfiguration(
                    subnet_type=SubnetType.PRIVATE_WITH_EGRESS,
                    name="Private",
                    cidr_mask=24
                )
            ],
        )


class RdsDatabaseStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = Vpc.from_lookup(self, "RdsDatabaseVpc", vpc_name="RdsDatabaseVpc")

        security_group = SecurityGroup(
            scope=self,
            id="RdsDatabaseSecurityGroup",
            security_group_name="RdsDatabaseSecurityGroup",
            vpc=vpc,
            allow_all_outbound=True,
            description="Security group for RDS database",
        )
        security_group.add_ingress_rule(
            peer=Peer.any_ipv4(),
            connection=Port.tcp(5432),
            description="Allow inbound traffic on port 5432",
            remote_rule=False
        )

        self.database = DatabaseCluster(
            self,
            "DummyRdsInstance",
            engine=DatabaseClusterEngine.aurora_postgres(version=AuroraPostgresEngineVersion.VER_17_4),
            writer=ClusterInstance.serverless_v2(id="TestWriterInstance", publicly_accessible=False),
            readers=[ClusterInstance.serverless_v2(id="TestReaderInstance", publicly_accessible=False, scale_with_writer=True)],
            port=5432,
            vpc=vpc,
            vpc_subnets=SubnetSelection(subnet_type=SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[security_group],
            removal_policy=RemovalPolicy.DESTROY,
        )
