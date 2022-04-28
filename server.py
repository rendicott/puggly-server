"""The Python implementation of the gRPC Uggly server."""

from concurrent import futures
import logging
from textwrap import fill

import grpc
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'uggly', 'python'))
import uggly
import uggly_pb2_grpc
import csv


def genTable(preq: uggly.PageRequest) -> uggly.PageResponse:
    maxHeight = preq.client_height - 4
    presp = uggly.PageResponse()
    cols = {
        0: list(),
    }
    col_widths = {
        0: 0,
    }
    data = list()
    with open('data.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        # first go through and identify lengths for all cells
        for i, row in enumerate(csv_reader):
            if i >= maxHeight:
                break
            data.append(row)
            for i, col in enumerate(row):
                if cols.get(i) is None:
                    cols[i] = list()
                cols[i].append(len(col))
        # generate col length max for every column
        for col, lengths in cols.items():
            col_widths[col] = max(lengths)
        # now actually generate the rows from the saved data
        for line_count, row in enumerate(data):
            if line_count == 0:
                presp = genTableRow(presp, col_widths, True, line_count, *row)
            else:
                presp = genTableRow(presp, col_widths, False, line_count, *row)
    return presp


def genTableRow(presp: uggly.PageResponse, col_widths, header=False, rownum: int=0, *args) -> uggly.PageResponse:
    start_x = 5
    start_y = 1 + rownum
    default_width = 10
    height = 1
    for i, arg in enumerate(args):
        width = col_widths.get(i)
        if width is None:
            width = default_width
        name = "row_%d_col_%d" % (rownum, i)
        bgColor = "dimgrey"
        if header:
            bgColor = "cornsilk"
        if i % 2 == 0:
            bgColor = "lightslategrey"
            if header:
                bgColor = "yellow"
        divBox = newBox(
            name,
            width=width,
            height=height,
            start_x=start_x,
            start_y=start_y,
            fbg=bgColor,
            border=False,
        )
        presp.div_boxes.boxes.append(divBox)
        start_x += width 
        tb = uggly.TextBlob(
            style=style("black", bgColor),
            content=arg,
            wrap = False,
        )
        tb.div_names.append(name)
        presp.elements.text_blobs.append(tb)
    return presp

def style(fg,bg):
    return uggly.Style(fg=fg,bg=bg,attr="4")

def newBox(
        name,
        width=40,
        height=10,
        start_x=5,
        start_y=5,
        border_w=1,
        bfg="blue",
        bbg="black",
        ffg="white",
        fbg="gray",
        fill_char=" ",
        border_char="X",
        border=True) -> uggly.DivBox:
    if len(fill_char) == 1:
        ifill_char = ord(fill_char)
    else:
        ifill_char = ord(" ")
    if len(border_char) == 1:
        iborder_char = ord(border_char)
    else:
        iborder_char = ord("x")
    divBox = uggly.DivBox(
        name=name,
        width=int(width),
        height=int(height),
        start_x=int(start_x),
        start_y=int(start_y),
        fill_st=style(ffg,fbg),
        border=border,
        border_st=style(bfg,bbg),
        border_char=iborder_char,
        fill_char=ifill_char,
        border_w=border_w,
    )
    return divBox


def genResponse(request: uggly.PageRequest) -> uggly.PageResponse:
        #width = request.client_width
        #height = request.client_height
        presp = uggly.PageResponse()
        divName = "nice"
        logging.info("before newbox")
        if request.name == "csv":
            return genTable(request)
        presp.div_boxes.boxes.append(newBox(divName, border_char="-", ffg="white", fbg="red"))
        presp.div_boxes.boxes.append(newBox("two", start_x=30,start_y=15, width=20, border_w=2))
        #divBox = uggly.DivBox(
        #    name=divName,
        #    width=int(10),
        #    height=int(10),
        #    start_x=int(5),
        #    start_y=int(5),
        #    #fill_st=style("white","gray"),
        #    #border=True,
        #    #border_st=style("blue","black"),
        #    #border_char="x",
        #    fill_char=ord("x")
        #)
        #logging.info("after newbox")
        return presp
        #return "hi"


class PageServicer(uggly_pb2_grpc.PageServicer):
    """Provides methods that implement functionality of Page server."""

    #def __init__(self):
        #self.db = uggly_resources.read_uggly_database()

    def GetPage(self, request: uggly.PageRequest, context) -> uggly.PageResponse:
    #def GetPage(self, request, context):
        logging.info(request)
        return genResponse(request)

class FeedServicer(uggly_pb2_grpc.FeedServicer):
    """Provides methods that implement functionality of Feed server."""

    def GetFeed(self, feedRequest: uggly.FeedRequest, context) -> uggly.FeedResponse:
        fresp = uggly.FeedResponse()
        logging.info(feedRequest)
        fresp.pages.append(uggly.PageListing("home"))
        return fresp


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    uggly_pb2_grpc.add_PageServicer_to_server(
        PageServicer(), server)
    uggly_pb2_grpc.add_FeedServicer_to_server(
        FeedServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()




if __name__ == '__main__':
    logging.basicConfig(level="INFO")
    serve()
