import zmq
import player_command_pb2
import random

class playerComm:

    def __init__(self, logger):
        self.context = zmq.Context()
        self.socket = None
        self.logger = logger
        self.prev_is_playing = False
        self.is_playing = False
        self.guid = random.randint(0, 1000000)
        self.req_cookie = 1

    def connect(self, ip, port):

        #  Socket to talk to server
        self.logger.info("Connecting to player")
        self.socket = self.context.socket(zmq.REQ)
        connect_str = "tcp://"+ip+":"+port
        self.socket.connect(connect_str)
        self.logger.info(connect_str)
        return self.socket

    def _fill_req_identifier(self, msg):
        msg.req_identifier.cookie = self.req_cookie
        msg.req_identifier.requestor_guid = self.guid
        msg.req_identifier.requestor_name = "where-now-control-python"
        self.req_cookie += 1

    def get_busy(self):

        msg = player_command_pb2.PlayerCommandMsg()
        self._fill_req_identifier(msg)

        self.socket.send(msg.SerializeToString())
        message = self.socket.recv()
        response = player_command_pb2.PlayerCommandReplyMsg()
        response.ParseFromString(message)
        return response.is_song_playing

    def play(self, song_name, position_in_ms = 0):

        msg = player_command_pb2.PlayerCommandMsg()
        self._fill_req_identifier(msg)

        msg.new_song_request.song_name = song_name
        msg.new_song_request.position_in_ms = position_in_ms

        self.socket.send(msg.SerializeToString())
        message = self.socket.recv()
        response = player_command_pb2.PlayerCommandReplyMsg()
        response.ParseFromString(message)
        return response.req_status

    def stop(self):

        msg = player_command_pb2.PlayerCommandMsg()
        self._fill_req_identifier(msg)

        msg.stop_play = True

        self.socket.send(msg.SerializeToString())
        message = self.socket.recv()
        response = player_command_pb2.PlayerCommandReplyMsg()
        response.ParseFromString(message)
        return response.req_status


    def _set_is_playing(self):
        self.prev_is_playing = self.is_playing
        self.is_playing = self.get_busy()
