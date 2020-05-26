#!/bin/bash
docker rm web -f
docker rmi web
docker build -t web .