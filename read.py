#Information on how to use the request module was taken from https://requests.readthedocs.io/en/latest/user/quickstart/#make-a-request
import requests

def getToken():
    url= "http://169.254.169.254/latest/api/token"
    headers = { "X-aws-ec2metadata-token-ttl-seconds": "21600"}
    ec2token = requests.put(url, headers=headers).text
    return ec2token

def getMetadata(ec2token):
    return
