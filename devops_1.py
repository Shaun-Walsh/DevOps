import boto3
import webbrowser
import time
from datetime import datetime
import os
from create import create_instance

new_instances = create_instance()

instance = new_instances[0]
print("Instance ID: in main", instance.id)