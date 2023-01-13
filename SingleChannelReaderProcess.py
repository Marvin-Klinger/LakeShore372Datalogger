from multiprocessing import Process, Queue


def visualize_single_channel(queue):
    """Read from the queue; this spawns as a separate Process"""
    while True:
        msg = queue.get()  # Read from the queue and do nothing
        print(msg)
        if msg == "DONE":
            break


def read_single_channel(queue):
    """Write data to the queue"""
    count = 10
    for ii in range(0, count):
        queue.put(ii)  # Put 'count' numbers into queue


    ### Tell the reader to stop
    queue.put("DONE")


def start_data_visualizer(qq,):
    """Start the reader processes and return all in a list to the caller"""
    all_reader_procs = list()
    ### reader_p() reads from qq as a separate process...
    ###    you can spawn as many reader_p() as you like
    ###    however, there is usually a point of diminishing returns
    reader_p = Process(target=visualize_single_channel, args=(qq,))
    reader_p.daemon = True
    reader_p.start()  # Launch reader_p() as another proc

    return reader_p


if __name__ == "__main__":
    ls_data_queue = Queue()  # writer() writes to qq from _this_ process
    visualizer_process = start_data_visualizer(ls_data_queue)

    read_single_channel(ls_data_queue)  # Queue stuff to all reader_p()
    visualizer_process.join()
    print("main end")