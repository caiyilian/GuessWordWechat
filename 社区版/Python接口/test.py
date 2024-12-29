from queue import Queue

msg_queue = Queue() 

try:
    msg = msg_queue.get(timeout=2)
except:
    print("No message received")