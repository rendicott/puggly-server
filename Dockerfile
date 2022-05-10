FROM ubuntu:22.04
RUN apt-get update
RUN apt-get install python3 python3-pip git -y
RUN pip install grpcio
RUN pip install betterproto
RUN git clone https://github.com/rendicott/uggly.git
ADD *.csv ./
ADD server.py ./
ENTRYPOINT [ "python3", "server.py" ]
