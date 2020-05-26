#!/bin/bash
docker docker service rm web
docker docker service create --name web -p 80:80 --env IP=$(hostname -I | cut -f 1 -d " ") --replicas 4 web
