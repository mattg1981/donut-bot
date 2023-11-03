#!/bin/bash

nohup python3.11 main.py > nohup.log 2>&1 &
echo $! > pid.txt