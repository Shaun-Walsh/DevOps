#!/usr/bin/bash
sudo awk -F'[ "]+' '{ print $1 }' /var/log/httpd/access_log | uniq
