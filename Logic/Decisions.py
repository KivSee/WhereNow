import threading
import random


class DecisionEventType:
    WIN_NO_ACTION = 0
    WIN_ACTION_FAIL = 1
    WIN_ACTION_DONE = 2
    NEW_MISSION_NO_ACTION = 3
    NEW_MISSION_ACTION_FAIL = 4
    NEW_MISSION_ACTION_DONE = 5
    VALID_MISSION_NO_ACTION_SONG = 6
    VALID_MISSION_NO_ACTION = 7
    PLAY_START = 8
    PLAY_END = 9
    HB_ALIVE = 10
    HB_DEAD = 11


class DecisionStateType:
    IDLE = 0
    SONG_PLAY = 1
    TRANS_PLAY = 2
    GAME_TRANS = 3
    ASK_FOR_CHIP_TRANS = 4
    WIN_TRANS = 5
    WIN_RANDOM = 6
    MISSION_TRANS = 7


class Decisions(threading.Thread):

    song_list = ["sun.wav", "hakuna.wav", "right_here_right_now.wav"]
    transitions_list = ["laugh.wav", "kivshi.wav"]
    game_transitions_list = ["game_intro.wav"]
    win_random_list = ["win_sex.wav", "win_warmth.wav", "win_drugs.wav"]

    def __init__(self, player_queue, decision_queue, logger):
        threading.Thread.__init__(self, name="Decisions")
        self.decision_queue = decision_queue
        self.player_queue = player_queue
        self.logger = logger
        self.song_flag = False
        self.prev_in_song = False
        self.is_in_song = False
        self.is_in_song_lock = threading.Lock()
        self.state = DecisionStateType.SONG_PLAY
        self.state_token = True
        self.last_played_song = ""
        self.last_played_trans = ""
        self.heartbeat_alive = False

    def run(self):
        while True:
            msg = self.decision_queue.get()
            self.handle_msg(msg)

    def handle_msg(self, msg):
        if msg == DecisionEventType.WIN_NO_ACTION:
            if self.state != DecisionStateType.WIN_RANDOM:
                self.state = DecisionStateType.ASK_FOR_CHIP_TRANS
            self.logger.info("Win tag in song, will wait for song end to play win transition")
        elif msg == DecisionEventType.WIN_ACTION_DONE:
            self.state = DecisionStateType.WIN_TRANS
            self.player_queue.put("STOP")
            self.logger.info("Win tag identified out of song, immediately play win transition and then song")
        elif msg == DecisionEventType.WIN_ACTION_FAIL:
            self.state = DecisionStateType.ASK_FOR_CHIP_TRANS
            self.player_queue.put("STOP")
            self.logger.info("Win tag failed write, immediately ask for chip again and retransition")
        elif msg == DecisionEventType.NEW_MISSION_NO_ACTION:
            if self.state != DecisionStateType.WIN_RANDOM:
                self.state = DecisionStateType.ASK_FOR_CHIP_TRANS
            self.logger.info("Tag with no mission identified during song, ask for the chip again at song end")
        elif msg == DecisionEventType.NEW_MISSION_ACTION_DONE:
            self.state = DecisionStateType.MISSION_TRANS
            self.player_queue.put("STOP")
            self.logger.info("Tag encoded with mission, stop and play call to action transition")
        elif msg == DecisionEventType.NEW_MISSION_ACTION_FAIL:
            self.state = DecisionStateType.ASK_FOR_CHIP_TRANS
            self.player_queue.put("STOP")
            self.logger.info("Mission encoding failed, immediately ask for chip again and retransition")
        elif msg == DecisionEventType.VALID_MISSION_NO_ACTION_SONG:
            if self.state != DecisionStateType.WIN_RANDOM:
                self.state = DecisionStateType.ASK_FOR_CHIP_TRANS
            self.logger.info("Tag with valid mission identified during song, ask for the chip again at song end")
        elif msg == DecisionEventType.VALID_MISSION_NO_ACTION:
            self.state = DecisionStateType.MISSION_TRANS
            self.player_queue.put("STOP")
            self.logger.info("Tag with valid mission already encoded, stop and play mission transition")
        elif msg == DecisionEventType.PLAY_START:
            if self.song_flag:
                self._set_is_in_song(True)
            self.logger.info("Play started, is_in_song is now: " + str(self.is_in_song))
        elif msg == DecisionEventType.PLAY_END:
            self.is_in_song = False
            self.state_token = True
            self.logger.info("Play ended")
        elif msg == DecisionEventType.HB_ALIVE:
            self.heartbeat_alive = True
        elif msg == DecisionEventType.HB_DEAD:
            self.heartbeat_alive = False
            self.logger.info("Heartbeat is dead, no RFID game will be played")


# Execute state
        if self.state_token:
            self.state_token = False
            self.song_flag = False
            if self.state == DecisionStateType.SONG_PLAY:
                song = random.choice(self.song_list)
                while song == self.last_played_song:
                    song = random.choice(self.song_list)
                self.player_queue.put(song)
                self.last_played_song = song
                self.song_flag = True
                self.state = DecisionStateType.TRANS_PLAY
            elif self.state == DecisionStateType.TRANS_PLAY:
                if self.heartbeat_alive:
                    transition = random.choice(self.transitions_list + self.game_transitions_list)
                    while transition == self.last_played_trans:
                        transition = random.choice(self.transitions_list + self.game_transitions_list)
                else:
                    transition = random.choice(self.transitions_list)
                    while transition == self.last_played_trans:
                        transition = random.choice(self.transitions_list)
                self.player_queue.put(transition)
                self.last_played_trans = transition
                self.state = DecisionStateType.SONG_PLAY
            elif self.state == DecisionStateType.GAME_TRANS:
                self.player_queue.put("game_intro.wav")
                self.last_played_trans = "game_intro.wav"
                self.state = DecisionStateType.SONG_PLAY
            elif self.state == DecisionStateType.ASK_FOR_CHIP_TRANS:
                self.player_queue.put("ask_for_chip.wav")
                self.state = DecisionStateType.TRANS_PLAY
            elif self.state == DecisionStateType.WIN_TRANS:
                self.player_queue.put("winning_intro.wav")
                self.song_flag = True
                self.state = DecisionStateType.WIN_RANDOM
            elif self.state == DecisionStateType.WIN_RANDOM:
                self.player_queue.put(random.choice(self.win_random_list))
                self.song_flag = True
                self.state = DecisionStateType.SONG_PLAY
            elif self.state == DecisionStateType.MISSION_TRANS:
                self.player_queue.put("mission.wav")
                self.song_flag = True
                self.state = DecisionStateType.SONG_PLAY

    def _set_is_in_song(self, new_value):
        self.is_in_song_lock.acquire()  # will block if lock is already held
        self.prev_in_song = self.is_in_song
        self.is_in_song = new_value
        self.is_in_song_lock.release()

    def get_is_in_song(self):
        self.is_in_song_lock.acquire()  # will block if lock is already held
        is_in_song_copy = self.is_in_song
        self.is_in_song_lock.release()
        return is_in_song_copy
