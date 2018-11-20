
import select, socket, sys, Queue
from time import sleep

def create_tcp_listen_sock(address, port):
    tcpSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_addr = (address, port)
    tcpSock.bind(listen_addr)
    tcpSock.listen(1)
    return tcpSock

# def read_non_blocking_tcp(TCPSock):
    # inputs = [TCPSock]
    # outputs = []
    # # client_addr = None
    # data_accum = ''
    # # message_queues = {}
    # readable, writable, exceptional = select.select(inputs, outputs, inputs, 0)
    # for s in readable:
        # if s is TCPSock:
            # connection, client_address = s.accept()
            # # if client_addr is not None:
            # print client_address
            # connection.setblocking(0)
            # # inputs.append(connection)
            # # message_queues[connection] = Queue.Queue()
        # # else:
            # sleep (0.05)
            # try:
                # data = connection.recv(16)
                # while (data):
            # # print data.strip()
            # # if data:
                # # message_queues[s].put(data)
                    # data_accum = data_accum + data.strip()
                    # data = connection.recv(16)
                # # if s not in outputs:
                    # # outputs.append(s)
            # # else:
                # # if s in outputs:
                    # # outputs.remove(s)
                # # inputs.remove(s)
                # connection.close()
                # return data_accum
                # # del message_queues[s]
            # except:
                # print "exception"
                # # return None
    # return None
    
def read_non_blocking_tcp(TCPSock):
    # try using the select.select thing with the socket on both the read/write lists so hopefully it returns all the time
    data_accum = ''
    try:
        connection, client_addr = TCPSock.accept() # this is a blocking function figure out what to do here
        connection.setblocking(0)
        print client_addr
        sleep(0.022)
        while True: # consider having this be according to number of bytes received so we dont need to close the connection..
            data = connection.recv(16) # data is 0 only when client closes connection, blocking function, figure out what to do
            if data:
                data_accum = data_accum + data.strip()
                # print data, client_addr
            else:
                connection.close()
                # print 'no more data from', client_addr
                # print 'full data recevied', data_accum
                return data_accum
    except:
        # print "exception"
        return None
    # finally:
        # Clean up the connection
        # print "close connection"
        



