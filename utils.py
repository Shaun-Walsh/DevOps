import json
import boto3
import random
import string
import subprocess
import shutil
import requests
from datetime import datetime

# Creating shortcuts for the boto3 clients and resources, the difference between the two was sourced from:
# https://stackoverflow.com/questions/42809096/difference-in-boto3-between-resource-client-and-session
ec2_resource = boto3.resource("ec2")
ec2_client = boto3.client("ec2")
s3_client = boto3.client("s3")
s3_resource = boto3.resource("s3")

# Function to generate a random ID, this is used to create unique names for resources. Fucntion calls random.choices 
# to generate a random string of lowercase letters and digits
# source: https://pynative.com/python-generate-random-string/
def random_id(length=6):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


# create a security group called 'shauns-sg' that only allows port 22 and 80. Function uses boto3 to create the security group
# and then authorizes the ingress rules for the ports
# source: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.create_security_group
# source: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.authorize_security_group_ingress
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

# Function to create an EC2 instance, this function uses boto3 to create an instance with the specified parameters
def create_instance(name, security_group_id, instance_type="t2.nano"):
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
            # Enable detailed monitoring
            # source: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.monitor_instances
            Monitoring={"Enabled": True},
            UserData="""#!/bin/bash
                        # update system
                        sudo yum update -y
                        # install apache
                        sudo yum install httpd -y
                        sudo systemctl enable httpd
                        sudo systemctl start httpd
                        
                        # Get info from EC2 Metadata
                        TOKEN=`curl -sX PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600"`
                        PUBLIC_IP=`curl -sH "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4/`
                        INSTANCE_ID=`curl -sH "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id/`
                        INSTANCE_TYPE=`curl -sH "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-type/`
                        echo $PUBLIC_IP $INSTANCE_ID $INSTANCE_TYPE

                        #Simple HTML Page for EC2 info
                        #Tee is used to allow correct permissions to write to the file
                        echo "
                        <html>
                        <h1>Some Useful EC2 Instance Info!</h1>

                        <li>Public IP: $PUBLIC_IP </li>
                        <li>Type of Instance: $INSTANCE_TYPE</li>
                        <li>Instance ID: $INSTANCE_ID</li>
                        </html>
                        " | sudo tee /var/www/html/index.html

                        # Sleep to test user data completion checker
                        sleep 30
                        # Create a file to indicate that the user data has run, this appoach was abandoned in favour of a different method
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
        # Return the instance ID
        return response[0].id
    except Exception as inst:
        print(f"An error occurred while creating the instance: {inst}")
        return None

# This function takes an instance Id and inserts it into a cloudwatch URL to directly take the user to the metrics for that instance
# source: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/viewing_metrics_with_cloudwatch.html
def cloudwatch_url(instance_id):
    return f"https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#metricsV2?graph=~(metrics~(~(~'AWS*2fEC2~'CPUUtilization~'InstanceId~'{instance_id}))~view~'timeSeries~stacked~false~region~'us-east-1~start~'-PT1H~end~'P0D~stat~'Maximum~period~60)&query=~'*7bAWS*2fEC2*2cInstanceId*7d*20InstanceId*3d*22{instance_id}*22"

# This function takes an instance Id and inserts it into an EC2 URL to directly take the user to the instance
def ec2_url(instance_id):
    public_hostname = ec2_resource.Instance(instance_id).public_dns_name
    return f"http://{public_hostname}"

# This function takes a bucket name and inserts it into an S3 URL to directly take the user to the bucket
def s3_website_url(bucket_name):
    return f"http://{bucket_name}.s3-website-us-east-1.amazonaws.com"

# This function takes an instance Id and a bucket name and stores the URLs in a file called swalsh-websites.txt
# source: https://www.geeksforgeeks.org/reading-writing-text-files-python/
def store_urls(instance_id, bucket_name, file_name="swalsh-websites.txt"):
    with open(file_name, "w") as f:
        f.write(f"{ec2_url(instance_id)}\n")
        f.write(f"{s3_website_url(bucket_name)}\n")

# Function that reads the URLs from the file and prints them to allow easy access from the command line
def print_urls(file_name="swalsh-websites.txt"):
    with open(file_name, "r") as f:
        for url in f:
            print(url)

# Function to create an error page for the S3 bucket, this function creates a simple HTML page that displays a 404 error
#The error page is then uploaded to the bucket using boto3 put_object
def create_error_page(bucket_name):
    error_page = """
    <!DOCTYPE html>
    <html> 
        <head> 
            <title>Custom 404 Page</title>  
        </head> 
        <body> 
            <h1>404 file not found on this server!</h1>
            <p>S Walsh DevOps Assignment</p>
        </body>
    </html>"""
    # Write the error page to a file
    with open("error.html", "w") as f:
        f.write(error_page)
    # Upload the error page to the bucket
    s3_client.put_object(
        Bucket=bucket_name,
        Key="error.html",
        Body=open("error.html", "rb"),
        ContentType="text/html",
    )

# Function to create a home page for the S3 bucket, this function creates a simple HTML page that displays a welcome message
# and an image. The home page is then uploaded to the bucket using boto3 put_object
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
    # Write the home page to a file
    with open("index.html", "w") as f:
        f.write(home_page)
    # Upload the home page to the bucket
    s3_client.put_object(
        Bucket=bucket_name,
        Key="index.html",
        Body=open("index.html", "rb"),
        ContentType="text/html",
    )

# Function to create a bucket with hosting, this function creates a bucket with the specified name and then configures the bucket
# to host a static website. The function also creates a bucket policy to allow public access to the bucket
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
            "ErrorDocument": {"Key": "error.html"},
            "IndexDocument": {"Suffix": "index.html"},
        }
        bucket_website = s3_resource.BucketWebsite(bucket_name)
        bucket_website.put(WebsiteConfiguration=website_configuration)
        #call the create_error_page and create_home_page functions to create the error and home pages
        create_error_page(bucket_name)
        create_home_page(bucket_name)

        return bucket_name
    except Exception as bucket:
        print(f"An error occurred while creating the bucket: {bucket}")
        return None

# Function to copy an image from a URL to an S3 bucket, this function uses requests to get the image from the URL and then
# uses shutil to copy the image to a file. The image is then uploaded to the bucket using boto3 put_object
# source: https://stackoverflow.com/questions/13137817/how-to-download-image-using-requests
def copy_image_to_bucket(bucket_name, image_url):
    try:
        response = requests.get(image_url, stream=True)
        image_name = "logo.jpg"
        with open(image_name, "wb") as out_file:
            shutil.copyfileobj(response.raw, out_file)
        # Upload the image to the bucket
        s3_client.put_object(
            Bucket=bucket_name,
            Key="img/image.jpg",
            Body=open(image_name, "rb"),
            ContentType="image/jpeg",
        )
    except Exception as img:
        print(f"An error occurred while copying the image to the bucket: {img}")

# Function to get the public DNS of an instance, this function uses boto3 to get the instance and then returns the public DNS
def get_instance_public_dns(instance_id):
    return ec2_resource.Instance(instance_id).public_dns_name

# short cut function to populate the ssh command with the instance public DNS, supresses the strict host key checking to allow
# the script to run without user input 
def ssh_helper(instance_id):
    return f"ssh -i shaunskey.pem -o StrictHostKeyChecking=no ec2-user@{get_instance_public_dns(instance_id)}"

# Function to run an SSH command on an instance, this function uses subprocess to run the command on the instance
def ssh_command(instance_id, command="ls"):
    return subprocess.run(f"{ssh_helper(instance_id)} '{command}'", shell=True)

# Function to install the monitoring scripts on an instance, this function uses subprocess to copy the monitoring scripts to the
# instance and then makes the scripts executable
def install_monitoring_scripts(instance_id):
    try:
        result = ssh_command(instance_id)
        # Install the monitoring scripts
        result = subprocess.run(
            f"scp -i shaunskey.pem monitoring.sh ec2-user@{get_instance_public_dns(instance_id)}:/tmp",
            shell=True,
        )
        # The web_logs.sh script is used to get the number of visitors to the web server. This was a simple script that I created
        # to count the number of unique IP addresses in the access log. The script is copied to the instance and made executable rather than
        # being run directly in the ssh command as I encountered issues with the script not running correctly when run directly in the ssh command
        result = subprocess.run(
            f"scp -i shaunskey.pem web_logs.sh ec2-user@{get_instance_public_dns(instance_id)}:/tmp",
            shell=True,
        )
        # Make the monitoring scripts executable
        result = ssh_command(instance_id, "chmod +x /tmp/monitoring.sh")
        result = ssh_command(instance_id, "chmod +x /tmp/web_logs.sh")
    except Exception as mon:
        print(f"An error occurred while installing the monitoring scripts: {mon}")

# Function to run the monitoring script on an instance, this function uses subprocess to run the monitoring script on the instance
def run_monitoring_script(instance_id):
    try:
        result = ssh_command(instance_id, "/tmp/monitoring.sh")
    except Exception as mon:
        print(f"An error occurred while running the monitoring script: {mon}")

#Funcion to ceate the AMI name, this function uses the current date and time to create a unique name for the AMI
def ami_name():
    return f"SW-{datetime.now().strftime('%Y-%m-%d-%f')}"

# Function to create an AMI, this function checks if the user data has completed running before creating the AMI. The function
# uses boto3 to create the AMI and then tags the AMI with the specified tag
# source: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.create_image
def create_ami(instance_id, tag):
    # Check if the user data has completed running
    if user_data_complete(instance_id):
        print("User data completed! Creating AMI")
        try:
            response = ec2_client.create_image(
                InstanceId=instance_id,
                Name=ami_name(),
                Description="AMI created for DevOps Assignment",
                NoReboot=True,
                TagSpecifications=[
                    {
                        "ResourceType": "image",
                        "Tags": [
                            {"Key": "Name", "Value": tag},
                        ],
                    },
                ],
            )
            return response["ImageId"]
        except Exception as ami:
            print(f"An error occurred while creating the AMI: {ami}")
            return None
    else:
        print("User data did not complete")

# Function to check if the user data has completed running, this function uses subprocess to run the cloud-init status command
# on the instance and then checks the return code to determine if the user data has completed. The function returns True if the
# user data has completed and False if it has not. I have included a sleep in the user data to allow time for the user data to
# complete on screen while the script is running.
# source: https://stackoverflow.com/questions/33019093/how-do-detect-that-cloud-init-completed-initialization
def user_data_complete(instance_id):
    try:
        print("Waiting on Cloud Init to finish running User Data")
        result = ssh_command(instance_id, "sudo cloud-init status --wait")
        if result.returncode == 0:
            return True
        else:
            return False
    except Exception as user:
        print(f"An error occurred while checking if the user data ran: {user}")
        return False

# Function to get the web server logs, this function uses subprocess to run the cat command on the access log file
# on the instance and then returns the result
def get_webserver_logs(instance_id):
    try:
        result = ssh_command(instance_id, "sudo cat /var/log/httpd/access_log")
        return result
    except Exception as logs:
        print(f"An error occurred while getting the web server logs: {logs}")
        return None

# Function to get the number of visitors to the web server, this function uses subprocess to run the web_logs.sh script
# on the instance and then returns the result
def get_webserver_vistors(instance_id):
    try:
        result = ssh_command(instance_id, "/tmp/web_logs.sh")
        return result
    except Exception as logs:
        print(f"An error occurred while getting the web server logs: {logs}")
        return None
