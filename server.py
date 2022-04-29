"""The Python implementation of the gRPC Uggly server."""

from concurrent import futures
import logging
from operator import contains
from textwrap import fill

import grpc
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'uggly', 'python'))
import uggly
import uggly_pb2_grpc
import csv


class TableData():
    def __init__(self,filename):
        # set up a registry of column widths
        self.Col_widths = {}
        self.Data = list()
        # load all data into class
        with open(filename) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            # first go through and identify lengths for all cells
            for i, row in enumerate(csv_reader):
                self.Data.append(row)
                for i, col in enumerate(row):
                    if self.Col_widths.get(i) is None:
                        self.Col_widths[i] = set()
                    self.Col_widths[i].add(len(col))
            # generate col length max for every column
            # so our views are consistent
            for col, lengths in self.Col_widths.items():
                self.Col_widths[col] = max(lengths)

def genTableView(preq: uggly.PageRequest, td: TableData) -> uggly.PageResponse:
    # build our view frame based on page request name and
    # cookies set from any previous views
    start = 0
    end = preq.client_height - 4
    start_next = 0
    start_previous = 0
    end_next = 0
    end_previous = 0
    for cookie in preq.send_cookies:
        if cookie.key=="start_previous":
            start_previous = int(cookie.value)
        if cookie.key=="start_next":
            start_next = int(cookie.value)
        if cookie.key=="end_next":
            end_next = int(cookie.value)
        if cookie.key=="end_previous":
            end_previous = int(cookie.value)
    if "next" in preq.name:
        start = start_next
        end = end_next
    if "previous" in preq.name:
        start = start_previous
        end = end_previous
    if start < 0:
        start = 0
        end = preq.client_height - 4
    if end > len(td.Data):
        end = len(td.Data)
        start = end - preq.client_height -4

    # now populate our view with data
    presp = uggly.PageResponse()
    presp = genTableRow(presp, td.Col_widths, True, 0, *td.Data[0])
    displayRow = 1
    for i in range(start+1,end):
        row = td.Data[i]
        presp = genTableRow(presp, td.Col_widths, False, displayRow, *row)
        displayRow+=1
    presp.set_cookies.append(uggly.Cookie(key="start_previous",value=str(start-displayRow)))
    presp.set_cookies.append(uggly.Cookie(key="end_previous",value=str(start)))
    presp.set_cookies.append(uggly.Cookie(key="start_next",value=str(end)))
    presp.set_cookies.append(uggly.Cookie(key="end_next",value=str(end+preq.client_height-4)))
    presp.key_strokes.append(uggly.KeyStroke(
        key_stroke="n",
        link=uggly.Link(
            key_stroke="n",
            page_name="csv_next")))
    presp.key_strokes.append(uggly.KeyStroke(
        key_stroke="p",
        link=uggly.Link(
            key_stroke="p",
            page_name="csv_previous")))
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


def genResponse(request: uggly.PageRequest, data: TableData) -> uggly.PageResponse:
        presp = uggly.PageResponse()
        divName = "nice"
        logging.info("before newbox")
        if "csv" in request.name:
            return genTableView(request, data)
        presp.div_boxes.boxes.append(newBox(divName, border_char="-", ffg="white", fbg="red"))
        presp.div_boxes.boxes.append(newBox("two", start_x=30,start_y=15, width=20, border_w=2))
        return presp

class PageServicer(uggly_pb2_grpc.PageServicer):
    """Provides methods that implement functionality of Page server."""

    def __init__(self):
        self.data_astro = TableData("data.csv")

    def GetPage(self, request: uggly.PageRequest, context) -> uggly.PageResponse:
        logging.info(request)
        return genResponse(request, self.data_astro)

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
