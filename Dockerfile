FROM python:3-slim

WORKDIR /usr/src/app

RUN apt update
RUN apt install rcs
RUN apt install patch

COPY backport.py formats.py ./

ENTRYPOINT [ "python", "./backport.py" ]
