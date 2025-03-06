#!/usr/bin/env python3

import boto3
import webbrowser
import time
from datetime import datetime
import os
import create
import read

# consistent resource naming
resource_name = f"{create.random_id()}-swalsh"

print (f"Creating resources with resource name: {resource_name}")

# sg = create.create_security_group_with_rules(name=resource_name)
# instance = create.create_instance(name=resource_name, security_group_id=sg)
# print(f"Instance ID: {instance.id}")
# print("To see Cloudwatch Metrics for this instance visit this URL:")
# print(create.cloudwatch_url(instance.id))

bucket = create.create_bucket_with_hosting(name=resource_name)
print(f"Bucket name: {bucket}")

print(create.copy_image_to_bucket(bucket_name=bucket,image_url="http://devops.setudemo.net/logo.jpg"))
