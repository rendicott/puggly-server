"""The Python implementation of the gRPC Uggly server."""

from concurrent import futures
import logging

import grpc
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'uggly', 'python'))
import uggly
import uggly_pb2_grpc

def genResponse():
    return uggly.PageResponse()

class PageServicer(uggly_pb2_grpc.PageServicer):
    """Provides methods that implement functionality of Page server."""

    #def __init__(self):
        #self.db = uggly_resources.read_uggly_database()

    def GetPage(self, request, context):
        presp = uggly.PageResponse()
        logging.info(request)
        divBox = uggly.DivBox()
        if request.name == "home":
            divName = "nice"
            logging.info("you got it dude")
            divBox.name = divName
            divBox.width = 20
            divBox.height = 10
            divBox.start_x = 10
            divBox.start_y = 10
            divBox.fill_st = uggly.Style(fg="blue", bg="red")
            tb = uggly.TextBlob()
            tb.content = "Hello World"
            tb.div_names.append(divName)
            tb.wrap = True
            presp.elements.text_blobs.append(tb)
        presp.div_boxes.boxes.append(divBox)
        return presp


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    uggly_pb2_grpc.add_PageServicer_to_server(
        PageServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig(level="INFO")
    serve()
