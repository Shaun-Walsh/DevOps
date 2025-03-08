#!/usr/bin/bash
#
# Some basic monitoring functionality; Tested on Amazon Linux 2023.
#
TOKEN=`curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600"`
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
PUBLIC_HOSTNAME=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-hostname)
MEMORYUSAGE=$(free -m | awk 'NR==2{printf "%.2f%%", $3*100/$2 }')
MEMORY_TOTAL=$(free -m | awk 'NR==2{printf $2 }')
MEMORY_USED=$(free -m | awk 'NR==2{printf $3 }')
MEMORY_FREE=$(free -m | awk 'NR==2{printf $4 }')
PROCESSES=$(expr $(ps -A | grep -c .) - 1)
HTTPD_PROCESSES=$(ps -A | grep -c httpd)

echo "Instance ID: $INSTANCE_ID"
echo "Public Hostname: $PUBLIC_HOSTNAME"
# Insert current timestamp
echo "Timestamp: $(date)"

echo -e "\nMemory Information: \n"
echo "Memory utilisation: $MEMORYUSAGE"
echo "Total System Memory: $MEMORY_TOTAL"
echo "Used System Memory: $MEMORY_USED"
echo "Free System Memory: $MEMORY_FREE"

echo -e "\nDisk Information: \n"
df -h

echo -e "\nProcess Information: \n"
echo "No of processes: $PROCESSES"
if [ $HTTPD_PROCESSES -ge 1 ]
then
    echo "Web server is running"
else
    echo "Web server is NOT running"
fi

# Cloud Init Output
cat /var/log/cloud-init-output.log
