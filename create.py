import boto3

def create_instance():
    ec2 = boto3.resource('ec2')
    new_instances = ec2.create_instances(
        ImageId='ami-0c614dee691cbbf37',
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.nano',
        KeyName='shaunskey',
        AvailabilityZone='us-east-1a',
        SecurityGroupIds=[
            'sg-0bc89a26114a1c180',
        ],
        TagSpecifications=[
            {'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': 'Shauns DevOps Assignment'
                    },
                ]
            },
        ],
        UserData="""#!/bin/bash
                    yum update -y
                    yum install httpd -y
                    systemctl enable httpd
                    systemctl start httpd
                    echo "<html><body><h1>Hello World</h1></body></html>" > /var/www/html/index.html"""

    )
    print (new_instances[0].id)
    new_instances[0].wait_until_running()
    print (new_instances[0].id + " instance is now running")
    new_instances[0].reload()
    return new_instances