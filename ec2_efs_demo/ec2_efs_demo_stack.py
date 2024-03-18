from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
)
import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_efs as efs
from aws_cdk import aws_iam as iam
from constructs import Construct

class Ec2EfsDemoStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.Vpc.from_lookup(self, "MyVpc", is_default=True)
        
        ec2_sg = ec2.SecurityGroup(self, "SecurityGroup",
            vpc=vpc,
            security_group_name="ec2_sg",
            description="Allow ssh access to ec2 instances",
            allow_all_outbound=True,
        # disable_inline_rules=True
        )
        
        ec2_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(22), "allow ssh access from the world")
        
        
        
        efs_sg = ec2.SecurityGroup(self, "SecurityGroupForEFS",
            vpc=vpc,
            security_group_name="efs_sg",
            description="Allow nfs to efs",
            allow_all_outbound=True,
        # disable_inline_rules=True
        )
        
        ec2_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(2049), "allow nfs for mounting")
        
        my_efs=efs.FileSystem(
            scope=self,
            id="PackageEfs",
            vpc=vpc,
            file_system_name="package-st-lib-efs",
            # Makes sure to delete EFS when stack goes down
            removal_policy=cdk.RemovalPolicy.DESTROY,
            security_group=efs_sg,
        )
        
        #create iam role for ec2 
        ec2_role = iam.Role(
            self,
            "EC2EfsRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonElasticFileSystemClientFullAccess"
                )
            ],
        )

        ec2_instance = ec2.Instance(
            self,
            "PackageTransferEC2",
            instance_type=ec2.InstanceType("t3.micro"),
            machine_image=ec2.MachineImage.latest_amazon_linux2(),
            vpc=vpc,
            # key_name="your-key-name-here",  # Replace with your SSH key name
            security_group=ec2_sg,
            role=ec2_role,
            instance_name="package-transfer-server",
        )
        
        my_efs.connections.allow_default_port_from(ec2_instance)
        
        # ec2_instance.user_data.add_commands(
        #     "sudo su",
        #     "yum install -y amazon-efs-utils",
        #     "yum install -y nfs-utils",
        #     f"mkdir -p /mnt/efs",
        #     f"mount -t efs -o tls {my_efs.file_system_id}:/ /mnt/efs",
        #     "echo 'EFS mount complete'",
        # )
        
        # self.file_system.connections.allow_default_port_from(self.ec2_instance)

        ec2_instance.user_data.add_commands(
            "yum check-update -y",
            "yum upgrade -y",
            "yum install -y amazon-efs-utils",
            "yum install -y nfs-utils",
            "file_system_id_1=" + my_efs.file_system_id,
            "efs_mount_point_1=/mnt/efs/fs1",
            'mkdir -p "${efs_mount_point_1}"',
            'sudo mount -t efs -o tls "${file_system_id_1}":/ "${efs_mount_point_1}"'
            )
