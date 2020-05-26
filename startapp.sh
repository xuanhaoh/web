#!/bin/bash
docker rm web -f
docker rmi web
docker build -t web .
docker run -it -d --name=web -p 80:80 --env IP=$(hostname -I | cut -f 1 -d " ") web
