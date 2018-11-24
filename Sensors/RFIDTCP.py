import datetime
import threading
import random
import socket
import array
from Logic.Decisions import DecisionEventType

class RFIDTCP(threading.Thread):

    RFID_VERSION            = 0x92
    MSG_LENGTH              = 8

    NO_MSG                  = 0
    TAG_INFO_MSG            = 1
    TAG_RESPONSE_MSG        = 2
    WRITE_STATUS_MSG        = 3
    SHOW_LEDS_MSG           = 4
    HEARTBEAT_MSG           = 5

    WIN_STATE               = 0x80
    VALID_STATE             = 0x40

    NO_COMMAND              = 0
    WIN_AND_ERASE           = 1
    NEW_MISSION             = 2
    WIN_NO_ERASE            = 3
    DISPLAY_MISSION         = 4

    WRITE_FAILED            = 0
    WRITE_SUCCESS           = 1

    EFFECT_TIMEOUT_SEC      = 10
    HEARTBEAT_TIMEOUT_SEC   = 10

    LEDSTATE_OFF            = 0
    LEDSTATE_PATTERN        = 1
    LEDSTATE_MISSION        = 2

    def __init__(self, decisions, decision_queue, logger, chip_id_logger):
        threading.Thread.__init__(self, name="RFIDTCP")
        self.sock = self.create_tcp_listen_sock('', 5007) # no server IP means we are on all available ip interfaces
        self.decisions = decisions
        self.decision_queue = decision_queue
        self.logger = logger
        self.chip_id_logger = chip_id_logger
        self.mytime = datetime.datetime.now()
        self.timer_on_time = datetime.datetime.now()
        self.timer_on_flag = False
        self.prev_in_song = False
        self.accum_msg = ""
        self.out_msg = bytearray([0,0,0,0,0,0,0,0])
        self.conn = None
        self.mission = 0
        self.new_mission = 0
        self.last_heartbeat_time = datetime.datetime.now()
        self.write_status = 0
        self.new_mission_written = False

    def create_tcp_listen_sock(self, address, port):
        tcpSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_addr = (address, port)
        tcpSock.bind(listen_addr)
        tcpSock.listen(1)
        return tcpSock

    def run(self):
        while True:
            self.logger.info("about to accept new tcp connection from client")
            self.conn, addr = self.sock.accept()
            self.conn.settimeout(3.0)
            try:
                while True:
                    curr_buf = self.conn.recv(self.MSG_LENGTH - len(self.accum_msg))
                    if len(curr_buf) == 0:
                        self.logger.info("socket closed. other side closed the socket gracefully. will listen again")
                        self.conn.close()
                        break
                    self.accum_msg = self.accum_msg + curr_buf
                    if len(self.accum_msg) == self.MSG_LENGTH:
                        self.handle_msg(self.accum_msg)
                        self.accum_msg = ""

                    self.mytime = datetime.datetime.now()
                    if self.timer_on_flag and self.mytime - self.timer_on_time > datetime.timedelta(seconds=self.EFFECT_TIMEOUT_SEC):
                        self.send_leds_state(self.LEDSTATE_OFF)
                        self.timer_on_flag = False

                    curr_in_song = self.decisions.get_is_in_song()
                    if curr_in_song and not self.prev_in_song:
                        if self.new_mission_written:
                            self.new_mission_written = False
                            self.send_leds_state(self.LEDSTATE_MISSION)
                        else:
                            self.send_leds_state(self.LEDSTATE_OFF)
                        self.timer_on_flag = False
                    elif not curr_in_song and self.prev_in_song:
                        self.send_leds_state(self.LEDSTATE_PATTERN)
                        self.timer_on_flag = False
                    self.prev_in_song = curr_in_song

                    if self.mytime - self.last_heartbeat_time > datetime.timedelta(seconds=self.HEARTBEAT_TIMEOUT_SEC):
                        self.decision_queue.put(DecisionEventType.HB_DEAD)
                        self.logger.warning("RFID heartbeat timed out. will disconnect socket and listen again")
                        self.conn.close()

            except Exception as e:
                self.logger.warning(str(e))
                self.logger.warning("RFID socket timed out. will disconnect socket and listen again")
                self.conn.close()

    def handle_msg(self, msg):
        byte_arr = array.array('B', msg)
        msg_type = byte_arr[0]
        if msg_type == self.TAG_INFO_MSG:
            print "TAG_INFO_MSG"
            print byte_arr
            self.logger.info("TAG_INFO_MSG " + str([elem.encode("hex") for elem in msg]))
            self.chip_id_logger.info(str([ elem.encode("hex") for elem in msg ]))
            self.handle_tag(byte_arr)
        elif msg_type == self.WRITE_STATUS_MSG:
            self.write_status = byte_arr[1]
            print "WRITE_STATUS_MSG"
            # print byte_arr
            self.logger.info("WRITE_STATUS_MSG " + str([elem.encode("hex") for elem in msg]))
            if self.write_status == self.WRITE_FAILED:
                self.logger.info("Write to tag failed!")
                if self.new_mission:
                    self.decision_queue.put(DecisionEventType.NEW_MISSION_ACTION_FAIL)
                else:
                    self.decision_queue.put(DecisionEventType.WIN_ACTION_FAIL)
            elif self.write_status == self.WRITE_SUCCESS:
                self.logger.info("Write to tag successful")
                self.new_mission_written = True
                if self.new_mission:
                    self.decision_queue.put(DecisionEventType.NEW_MISSION_ACTION_DONE)
                    self.mission = self.new_mission
                else:
                    self.decision_queue.put(DecisionEventType.WIN_ACTION_DONE)
                self.logger.info("Written mission: 0x" + format(self.new_mission, '02x'))
            else:
                self.logger.warning("Undefined write status content!" + str(self.write_status))
        elif msg_type == self.HEARTBEAT_MSG:
            self.last_heartbeat_time = self.mytime
            rfid_version = byte_arr[1]
            if rfid_version != self.RFID_VERSION:
                self.decision_queue.put(DecisionEventType.HB_DEAD)
                self.logger.warning("RFID version mismatch, card reader possibly dead! read version: 0x" + format(rfid_version, '02x'))
            else:
                self.decision_queue.put(DecisionEventType.HB_ALIVE)
            self.conn.send(byte_arr)
        else:
            self.logger.warning("Undefined message type" + str(msg_type))

    def handle_tag(self, byte_arr):
        is_in_song = self.decisions.get_is_in_song()
        self.mission = byte_arr[5]
        power = byte_arr[6]
        power_mask = byte_arr[7]
        if self.mission >= self.WIN_STATE and is_in_song:
            self.logger.info("Winning tag identified when in song, mission: " + format(self.mission, '02x'))
            self.decision_queue.put(DecisionEventType.WIN_NO_ACTION)
            self.send_rfid_response(self.WIN_NO_ERASE, 0)
            self.timer_on_flag = True
            self.timer_on_time = self.mytime
        elif self.mission < self.VALID_STATE and is_in_song:
            self.logger.info("Tag with no mission identified when in song, mission: " + format(self.mission, '02x'))
            self.decision_queue.put(DecisionEventType.NEW_MISSION_NO_ACTION)
            self.send_rfid_response(self.NO_COMMAND, 0)
        elif self.mission >= self.WIN_STATE and not is_in_song:
            self.logger.info("Winning tag identified when not in song, waiting for write before queuing to decision module")
            # dont queue the mission for decisions yet, only after the erase
            self.new_mission = 0
            self.send_rfid_response(self.WIN_AND_ERASE, self.new_mission)
            # we dont set the timer flag because we want the win pattern to keep on until a song is played
        elif self.mission < self.VALID_STATE and not is_in_song:
            self.logger.info("Tag with no mission identified when not in song, waiting for write before queuing to decision module")
            # dont queue the mission for decisions yet, only after the write
            self.new_mission = random.randint(0, 63) & power_mask
            self.new_mission = self.new_mission | power
            self.new_mission = self.new_mission | self.VALID_STATE
            self.send_rfid_response(self.NEW_MISSION, self.new_mission)
            # we dont set the timer flag because we want the mission to keep on until a song is played
        elif is_in_song:    # valid mission case but in song
            self.logger.info("Tag with valid mission identified in song, no write to tag, display mission")
            self.decision_queue.put(DecisionEventType.VALID_MISSION_NO_ACTION_SONG)
            self.send_rfid_response(self.DISPLAY_MISSION, self.mission)
            self.timer_on_flag = True
            self.timer_on_time = self.mytime
        else:
            self.logger.info("Tag with valid mission identified out of song, no write to tag, display mission")
            self.decision_queue.put(DecisionEventType.VALID_MISSION_NO_ACTION)
            self.new_mission_written = True
            self.send_rfid_response(self.DISPLAY_MISSION, self.mission)

    def send_rfid_response(self, command, mission):
        msg = [self.TAG_RESPONSE_MSG, command, mission,0,0,0,0,0]
        print "TAG_RESPONSE_MSG"
        print msg
        out_msg = bytearray(msg)  # type: bytearray
        self.conn.send(out_msg)

    def send_leds_state(self, leds_state):
        print "SHOW_LEDS_MSG"
        msg = [self.SHOW_LEDS_MSG, leds_state, 0,0,0,0,0,0]
        # print msg
        out_msg = bytearray(msg)  # type: bytearray
        self.conn.send(out_msg)
