"""The Python implementation of the gRPC Uggly server."""

from concurrent import futures
import logging
import argparse
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
                clean_row = [col.replace("  ", "") for col in row ]
                self.Data.append(clean_row)
                for i, col in enumerate(clean_row):
                    if self.Col_widths.get(i) is None:
                        self.Col_widths[i] = set()
                    self.Col_widths[i].add(len(col))
            # generate col length max for every column
            # so our views are consistent
            for col, lengths in self.Col_widths.items():
                self.Col_widths[col] = max(lengths)

# genTableView determin
def genTableView(preq: uggly.PageRequest, td: TableData) -> uggly.PageResponse:
    page_name = preq.name.split("_")[0]
    # build our view frame based on page request name and
    # cookies set from any previous views
    hasHeader = True
    defaultStart = 0
    if hasHeader:
        defaultStart = 1
    buffer = 6
    display_height = preq.client_height - buffer
    display_rows = display_height
    last_viewed = 0
    start = defaultStart
    end = display_rows+1
    # determine what the last viewed record was
    for cookie in preq.send_cookies:
        if cookie.key == "last_viewed":
            last_viewed = int(cookie.value)
    # find out if the client is trying to go backwards or forwards
    # based on the link they clicked
    if preq.name == "%s_n" % page_name:
        start = last_viewed
        end = last_viewed + display_rows
    elif preq.name == "%s_p" % page_name:
        start = last_viewed - 2*display_rows
        end = start + display_rows
    elif preq.name == "%s_end" % page_name:
        end = len(td.Data)
        start = end - display_rows
    # check ranges for the extremes to make sure 
    # we didn't exceed the start or end of the data
    if start < defaultStart:
        start = defaultStart
        end = display_rows
    if end > len(td.Data):
        start = len(td.Data) - display_rows
        end = len(td.Data)
    # now populate our view with data
    presp = uggly.PageResponse()
    presp = genTableRow(presp, td.Col_widths, True, 0, *td.Data[0])
    displayRow = 1
    logging.info("last_viewed=%d, display_rows=%d, start=%d, end=%d, client_height=%d" % (last_viewed, display_rows, start,end, preq.client_height))
    for i in range(start,end):
        row = td.Data[i]
        presp = genTableRow(presp, td.Col_widths, False, displayRow, *row)
        displayRow+=1
    # add a cookie that lets the server know the last record we saw
    # so it can calculate what we should see on a next/previous page
    last_viewed = start + displayRow - 2
    logging.info("last_viewed=%d, display_rows=%d, start=%d, end=%d, client_height=%d" % (last_viewed, display_rows, start,end, preq.client_height))
    presp.set_cookies.append(uggly.Cookie(key="last_viewed",value=str(last_viewed)))
    # add keystroke links to the page response for 'next' and 'previous'
    presp.key_strokes.append(uggly.KeyStroke(
        key_stroke="n",
        link=uggly.Link(
            key_stroke="n",
            page_name="%s_n" % page_name)))
    presp.key_strokes.append(uggly.KeyStroke(
        key_stroke="p",
        link=uggly.Link(
            key_stroke="p",
            page_name="%s_p" % page_name)))
    # add keystroke links to the page response for 'start' and 'end'
    presp.key_strokes.append(uggly.KeyStroke(
        key_stroke="s",
        link=uggly.Link(
            key_stroke="s",
            page_name=page_name)))
    presp.key_strokes.append(uggly.KeyStroke(
        key_stroke="e",
        link=uggly.Link(
            key_stroke="e",
            page_name="%s_end" % page_name)))
    string_width = preq.client_width - 4
    reserved = int(string_width / 3)
    # set up a "you are here" string filling the available width divided by 3
    rmsg = "(n) Next Page"
    cmsg = "Displaying Records %d-%d (Total: %d)" % (start, last_viewed, len(td.Data))
    lmsg = ("(p) Previous Page")
    footer_msg = "{lmsg:<{reserved}}{cmsg:^{reserved}}{rmsg:>{reserved}}".format(lmsg=lmsg, cmsg=cmsg, rmsg=rmsg, reserved=reserved)
    # build footer and add text
    divNameFooter = "footer"
    footerBox = newBox(
        name=divNameFooter,
        width=string_width + 2,
        height=1,
        start_y=preq.client_height - 4,
        start_x=1,
        ffg="white",
        fbg="black",
        fill_char="",
        border=False,
    )    
    presp.div_boxes.boxes.append(footerBox)
    tb_footer = uggly.TextBlob(
            content=footer_msg,
            wrap=False,
            style=style("white","black"),
        )
    tb_footer.div_names.append(divNameFooter)
    presp.elements.text_blobs.append(tb_footer)
    # set up a header message 
    tmsg = "(s) Go to Start        (e) Go to End"
    header_msg = "{tmsg:^{string_width}}".format(tmsg=tmsg, string_width=string_width)
    # build footer and add text
    divNameHeader = "header"
    headerBox = newBox(
        name=divNameHeader,
        width=string_width + 2,
        height=1,
        start_y=0,
        start_x=1,
        ffg="white",
        fbg="black",
        fill_char="",
        border=False,
    )    
    presp.div_boxes.boxes.append(headerBox)
    tb_header = uggly.TextBlob(
            content=header_msg,
            wrap=False,
            style=style("white","black"),
        )
    tb_header.div_names.append(divNameHeader)
    presp.elements.text_blobs.append(tb_header)
    return presp

# genTableRow handles the building of a single table row
# which is comprised of a divBox per cell of the table
# with alternating colors
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

# define a function that helps in setting defaults for new DivBoxes
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
        logging.info("before newbox")
        if "house" or "astro" in request.name:
            return genTableView(request, data)
        else: 
            divName = "nice"
            presp.div_boxes.boxes.append(newBox(divName, border_char="-", ffg="white", fbg="red"))
            presp.div_boxes.boxes.append(newBox("two", start_x=30,start_y=15, width=20, border_w=2))
        return presp

class PageServicer(uggly_pb2_grpc.PageServicer):
    """Provides methods that implement functionality of Page server."""

    def __init__(self):
        self.data_astro = TableData("astro.csv")
        self.data_house= TableData("house.csv")

    def GetPage(self, request: uggly.PageRequest, context) -> uggly.PageResponse:
        logging.info(request)
        if "astro" in request.name:
            return genResponse(request, self.data_astro)
        if "house" in request.name:
            return genResponse(request, self.data_house)
        else:
            return genResponse(request, self.data_astro)

class FeedServicer(uggly_pb2_grpc.FeedServicer):
    """Provides methods that implement functionality of Feed server."""

    def GetFeed(self, feedRequest: uggly.FeedRequest, context) -> uggly.FeedResponse:
        fresp = uggly.FeedResponse()
        logging.info(feedRequest)
        fresp.pages.append(uggly.PageListing("home"))
        return fresp


def serve():
    parser = argparse.ArgumentParser()
    
    # Adding optional argument
    parser.add_argument("-k", "--Key", help = "path to SSL key file")
    parser.add_argument("-c", "--Cert", help = "path to SSL cert file")
    parser.add_argument("-p", "--Port", help = "port to run on", default="4443")
    
    # Read arguments from command line
    args = parser.parse_args()
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    uggly_pb2_grpc.add_PageServicer_to_server(
        PageServicer(), server)
    uggly_pb2_grpc.add_FeedServicer_to_server(
        FeedServicer(), server)
    bind_string = "[::]:%s" % args.Port
    if args.Key:
        with open(args.Key, 'rb') as f:
            private_key = f.read()
        with open(args.Cert, 'rb') as f:
            certificate_chain = f.read()
        server_credentials = grpc.ssl_server_credentials( ( (private_key, certificate_chain), ) )
        print("attempting to listen on '%s' with SSL" % bind_string)
        server.add_secure_port(bind_string, server_credentials)
    else:
        print("attempting to listen on '%s' (no ssl)" % bind_string)
        server.add_insecure_port(bind_string)
    server.start()
    server.wait_for_termination()




if __name__ == '__main__':
    logging.basicConfig(level="INFO")
    serve()
