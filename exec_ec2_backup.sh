#!/bin/bash

pushd $(dirname ${0}) > /dev/null

pyenv local ec2_backup

python -m ec2_backup.ec2_backup config.json

popd > /dev/null
