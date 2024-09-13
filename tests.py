import time
from processboard import *

pb = ProcessBoard()

items = [
    BasicLoading("Basic", description="This is a basic progress item", status=Status.WORKING),
    BatchLoading("Batch", value = 0, end = 100, description="This is a batch progress item"),
    TimeLoading("Time", "00:00:00", "00:00:10", description="This is a time progress item", tag="New"),
    BasicLoading("Information", description=""),
]

while True:
    x = input("Enter 'q' to quit, 't' to start server, 's' to stop, 'p' to populate, 'u' to simulate user: ")

    if x == 'q':
        print("Exiting")

        pb.stop()
        exit()

    if x == 't':
        print("Starting server...")
        pb.start()

    if x == 's':
        print("Stopping server...")
        pb.stop()

    if x == 'u':
        print("Updating...")

        pb.items.setStatus(items[0].getId(), Status.COMPLETE)

        time.sleep(1)

        pb.items.setStatus(items[1].getId(), Status.WORKING)

        for i in range(101):
            time.sleep(0.05)
            pb.items.setValue(items[1].getId(), i)

        pb.items.setStatus(items[1].getId(), Status.COMPLETE)

        time.sleep(1)

        pb.items.setStatus(items[2].getId(), Status.WORKING)

        for i in range(11):
            time.sleep(1)
            pb.items.setValue(items[2].getId(), "00:00:" + ("0" if i < 10 else '') + str(i))

        pb.items.setStatus(items[2].getId(), Status.COMPLETE)

        time.sleep(1)

        pb.items.setStatus(items[3].getId(), Status.INFORMATION)
        pb.items.setParam(items[3].getId(), 'description', "This is some important information with <b>bold text</b> and <i>italic text</i>.")

    if x == 'p':
        print("Populating server page...")
        pb.items.add(items)
