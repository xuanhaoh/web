FROM python:3.7

COPY proxy.conf /etc/apt/apt.conf.d
COPY ./app /app
WORKDIR /app

RUN apt-get update
RUN apt-get install -y nginx supervisor
RUN pip install -r requirements.txt --proxy=http://wwwproxy.unimelb.edu.au:8000/
RUN rm /etc/nginx/sites-enabled/default
RUN rm -r /root/.cache

COPY nginx.conf /etc/nginx/conf.d/
COPY supervisord.conf /etc/

CMD ["/usr/bin/supervisord"]
