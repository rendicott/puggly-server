FROM ubuntu:22.04
ADD *.csv ./
ADD server.py ./
ENTRYPOINT [ "python3", "server.py" ]
