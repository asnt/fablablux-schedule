#!/bin/sh

DATA="{\"table\": [
[false, false, false, false, false, false, false, false, false],
[false, false, true, true, false, false, false, false, false],
[false, false, false, false, false, false, true, true, false],
[false, false, false, false, false, false, false, false, false],
[false, false, true, false, false, false, false, false, false],
[false, false, false, false, false, false, false, false, false],
[true, false, false, false, false, false, false, false, false]]}"

DATA1="{\"table\": [
[false, false, false, false, false, false, false, false, false],
[false, false, false, false, false, false, false, false, false],
[false, false, false, false, false, false, false, false, false],
[false, false, false, false, false, false, false, false, false],
[false, false, false, false, false, false, false, false, false],
[false, false, false, false, false, false, false, false, false],
[false, false, false, false, false, false, false, false]]}"

curl -H "Content-Type: application/json" -X PUT \
    http://localhost:5000/api/occupation \
    -d "${DATA}"

#curl -H "Content-Type: application/json" -X PUT \
#    http://localhost:5000/api/occupation \
#    -d "${DATA1}"
