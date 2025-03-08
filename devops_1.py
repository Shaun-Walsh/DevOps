#!/usr/bin/env python3
import utils

# Consistent resource naming
resource_name = f"{utils.random_id()}-swalsh"
print (f"Creating resources with resource name: {resource_name}")

# Create a security group and then create EC2 instance
sg = utils.create_security_group_with_rules(name=resource_name)
instance_id = utils.create_instance(name=resource_name, security_group_id=sg)
print(f"Instance ID: {instance_id}")

# Create an S3 bucket
bucket_name = utils.create_bucket_with_hosting(name=resource_name)
print(f"Bucket name: {bucket_name}")

# Copy the SETU image to the bucket
utils.copy_image_to_bucket(bucket_name=bucket_name,image_url="http://devops.setudemo.net/logo.jpg")
print("Copying image to bucket...")

utils.store_urls(instance_id=instance_id, bucket_name=bucket_name)
print("URLs stored in file in previous step are:")
utils.print_urls()

utils.install_monitoring_scripts(instance_id=instance_id)
print("Monitoring scripts installed...")

# Check if User Data has ran and create AMI
utils.create_ami(instance_id=instance_id, tag=resource_name)
print("AMI created")

# Run monitoring script
print("Running monitoring script...")
utils.run_monitoring_script(instance_id=instance_id)

# Get Visitors and show access logs
utils.get_webserver_vistors(instance_id=instance_id)
utils.get_webserver_logs(instance_id=instance_id)

# Print a link to the Cloudwatch Console for this instance
print("To see Cloudwatch Metrics for this instance visit this URL:")
print(utils.cloudwatch_url(instance_id))

print("To SSH to this instance you can run: ")
print(utils.ssh_helper(instance_id))
