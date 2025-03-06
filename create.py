import time
import json
import boto3
import random
import string
import subprocess
import shutil
import requests

ec2_resource = boto3.resource("ec2")
ec2_client = boto3.client("ec2")
s3_client = boto3.client("s3")
s3_resource = boto3.resource("s3")


def random_id(length=6):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


# create a security group called 'shauns-sg' that only allows port 22 and 80
def create_security_group_with_rules(name):
    try:
        response = ec2_client.create_security_group(
            Description="Shauns Security Group",
            GroupName=name,
            VpcId="vpc-0d779c69b4df15fe9",
        )
        sg_id = response["GroupId"]
        # add ingress port 80 and 22
        response = ec2_client.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {
                    "IpProtocol": "tcp",
                    "FromPort": 80,
                    "ToPort": 80,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                },
                {
                    "IpProtocol": "tcp",
                    "FromPort": 22,
                    "ToPort": 22,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                },
            ],
        )
        return sg_id
    except Exception as sg:
        print(f"An error occurred while creating the security group: {sg}")
        return None


def create_instance(name, security_group_id, instance_type="t2.nano"):
    # Try and except information was gather from https://docs.python.org/3/library/exceptions.html
    try:
        ec2 = ec2_resource
        response = ec2.create_instances(
            ImageId="ami-05b10e08d247fb927",
            MinCount=1,
            MaxCount=1,
            InstanceType=instance_type,
            KeyName="shaunskey",
            Placement={"AvailabilityZone": "us-east-1a"},
            SecurityGroupIds=[security_group_id],
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {"Key": "Name", "Value": name},
                        {"Key": "Project", "Value": "DevOps Assignment"},
                        {"Key": "CreatedBy", "Value": "boto3"},
                    ],
                },
            ],
            UserData="""#!/bin/bash
                        # update system
                        sudo yum update -y
                        # install apache
                        sudo yum install httpd -y
                        sudo systemctl enable httpd
                        sudo systemctl start httpd
                        
                        # Get info from EC2 Metadata
                        TOKEN=`curl -sX PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600"`
                        curl -sH "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/
                        PUBLIC_IP=`curl -sH "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4/`
                        INSTANCE_ID=`curl -sH "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id/`
                        INSTANCE_TYPE=`curl -sH "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-type/`
                        echo $PUBLIC_IP $INSTANCE_ID $INSTANCE_TYPE

                        #Simple HTML Page for EC2 info 
                        echo "
                        <html>
                        <h1>Some Useful EC2 Instance Info!</h1>

                        <li>Public IP: $PUBLIC_IP </li>
                        <li>Type of Instance: $INSTANCE_TYPE</li>
                        <li>Instance ID: $INSTANCE_ID</li>
                        </html>
                        " | sudo tee /var/www/html/index.html

                        touch /tmp/userdata_ran
                        echo "User Data Ran!"

                        """,
        )
        print(response[0].id)
        response[0].wait_until_running()
        print(response[0].id + " instance is now running")
        response[0].reload()
        public_ip = response[0].public_ip_address
        print("Public IP: ", public_ip)

        return response[0]
    except Exception as inst:
        print(f"An error occurred while creating the instance: {inst}")
        return None


def cloudwatch_url(instance_id):
    return f"https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#metricsV2?graph=~(metrics~(~(~'AWS*2fEC2~'CPUUtilization~'InstanceId~'{instance_id}))~view~'timeSeries~stacked~false~region~'us-east-1~start~'-PT1H~end~'P0D~stat~'Maximum~period~60)&query=~'*7bAWS*2fEC2*2cInstanceId*7d*20InstanceId*3d*22{instance_id}*22"


# http://devops.setudemo.net/logo.jpg
# We will grab image, upload it under a /img key in the bucket
# For convenience, we will always call the image /img/image.jpg
# we need a basic html file that has image tags and uses /img/image.jpg

def create_error_page(bucket_name):
    error_page = """
    <!DOCTYPE html>
    <html> 
        <head> 
            <title>404 Not Found</title>  
        </head> 
        <body> 
            <h1>404 Not Found</h1>
            <p>The page you are looking for does not exist.</p>
        </body>
    </html>"""
    with open("error.html", "w") as f:
        f.write(error_page) # write the error page to a file    
    s3_client.put_object(Bucket=bucket_name, Key="error.html", Body=open("error.html", 'rb'), ContentType="text/html") # upload the error page to the bucket

def create_home_page(bucket_name):
    home_page = """
    <!DOCTYPE html>
    <html> 
        <head> 
            <title>Welcome</title>  
        </head> 
        <body> 
            <h1>Test</h1>
            <p>Here is the image.</p>
            <img src="img/image.jpg" alt="image"> 
        </body>
    </html>"""
    with open("index.html", "w") as f:
        f.write(home_page) # write the error page to a file    
    s3_client.put_object(Bucket=bucket_name, Key="index.html", Body=open("index.html", 'rb'), ContentType="text/html") # upload the error page to the bucket


def create_bucket_with_hosting(name):
    try:
        response = s3_client.create_bucket(Bucket=name)
        bucket_name = response["Location"].replace("/", "")
        # Disable the block public access security feature
        s3_client.delete_public_access_block(Bucket=bucket_name)
        # Create a bucket policy to allow public access
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": f"arn:aws:s3:::{bucket_name}/*",
                }
            ],
        }
        response = s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(bucket_policy),
        )
        # Website configuration
        website_configuration = {
            'ErrorDocument': {'Key': 'error.html'},
            'IndexDocument': {'Suffix': 'index.html'},
        }
        bucket_website = s3_resource.BucketWebsite(bucket_name)
        bucket_website.put(WebsiteConfiguration=website_configuration)
        create_error_page(bucket_name)
        create_home_page(bucket_name)

        return bucket_name
    except Exception as bucket:
        print(f"An error occurred while creating the bucket: {bucket}")
        return None

def copy_image_to_bucket(bucket_name,image_url):
    try:
        response = requests.get(image_url, stream=True)
        image_name = "logo.jpg"
        with open(image_name, 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)
        s3_client.put_object(Bucket=bucket_name, Key="img/image.jpg", Body=open(image_name, 'rb'), ContentType="image/jpeg") 
    except Exception as img:
        print(f"An error occurred while copying the image to the bucket: {img}")
