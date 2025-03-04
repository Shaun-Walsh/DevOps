import boto3
import webbrowser
import time
from datetime import datetime
import os
import create
import read

new_instances = create.create_instance()

instance = new_instances[0]
print("Instance ID: in main", instance.id)

token = read.getToken()
print("Token: in main", token)
