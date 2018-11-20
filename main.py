import datetime
from Sensors.RFIDTCP import RFIDTCP
from Sensors.Decisions import Decisions
from Sensors.Decisions import DecisionEventType
from Player.playerComm import playerComm
import Queue
import logging

from time import sleep

logging.basicConfig(level=logging.INFO)
logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
rootLogger = logging.getLogger()

fileHandler = logging.FileHandler("{0}/{1}.log".format(r"c:\logs", 'where-now-{:%Y-%m-%d--%H-%M-%S}'.format(datetime.datetime.now())))
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)

# consoleHandler = logging.StreamHandler()
# consoleHandler.setFormatter(logFormatter)
# rootLogger.addHandler(consoleHandler)

rootLogger.info("WhereNow art installation python logic started")

decision_queue = Queue.Queue()
player_queue = Queue.Queue()

player = playerComm(rootLogger)
rfidThread = RFIDTCP(player, decision_queue, rootLogger)
decisionsThread = Decisions(player_queue, decision_queue, rootLogger)


rfidThread.start()
decisionsThread.start()
rootLogger.info("Threads started")

# open comm port to player
player_socket = player.connect("10.0.0.102","2100")

#initialize time vars
MyTime = datetime.datetime.now()
prevTime = MyTime
rfidTime = MyTime

# start us off with an initial decision
decision_queue.put(DecisionEventType.SONG_START)

while True:
    MyTime = datetime.datetime.now()
    sleep(0.5)
    if (MyTime - prevTime > datetime.timedelta(seconds=1)):
        print "XXXXXXXXX"
        player._set_is_in_song()
        print "YYYYYYYYY"
        if player.prev_in_song == False and player.is_in_song == True:
            decision_queue.put(DecisionEventType.SONG_START)
        if player.prev_in_song == True and player.is_in_song == False:
            decision_queue.put(DecisionEventType.SONG_END)
        prevTime = MyTime
    try:
        songname = player_queue.get()
        if (songname):
            player.play(songname)
    except Queue.Empty:
        print "loop"

    # TODO: handle timeout on leds in rfid thread
    # TODO: decide on the transitions and select between them, send to player
    # TODO: decide how to choose between the songs and send song to player

'''
rf = RFIDTCP()
# temperature = Temperature()
# motion = Motion()
# decisions = Decisions()
player = playerComm()

# open comm port to player
# play_sock = player.connect("10.0.0.102","2100")

#initialize time vars
MyTime = datetime.datetime.now()
prevTime = MyTime
rfidTime = MyTime

# transDriver = TransitionsDriver()
song = None
next_song = None
check_num = 0

# prevSachiMeter = 0

# uncomment this to start with sensors
# sleep(2)

last_time = 0
input_type = None
i = 0

print "Starting WhereNow art installation logic"

while True:
    # read sensors data
    
    MyTime = datetime.datetime.now()
    data = rf.process()
    if data != 0 and data is not None:
        print data, i
        i = i + 1
    # curr_temperature = temperature.get_temperature()
    # motion_detected = motion.get_has_motion()
    sleep(0.01)

    # current song is playing
    song_playing = song != None and play_sock != None and player.get_busy()
    print "song != None " + str(song != None)
    print "play_sock != None " + str(play_sock != None)
    print "player.get_busy() " + str(player.get_busy())
    if song_playing:
        print song
        print "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
        player.play(song, 0)
        # song_time = (pygame.mixer.music.get_pos())/ 1000.0
        # song_time = max(song_time, last_time)
        # last_time = song_time
        # if song.is_transition:
            # transDriver.play_animations(curr_temperature, sachiMeter, input_type)
        # else:
            # song.play_animations(song_time, curr_temperature, sachiMeter)

    else: #no song playing
        last_time = 0
        if next_song is not None:
            print "next song is: " + next_song[0]
            song = next_song[0]
            # pygame.mixer.music.load(song.get_audio_file())
            # pygame.mixer.music.play(0, 0)
            if len(next_song) > 1:
                del next_song[0]
            else:
                next_song = None
        else:
            next_song = decisions.decide(curr_temperature, sachiMeter, illusionsFlag, motion_detected)
            input_type = decisions.curr_input
            # if next_song is None:
                # transDriver.play_animations(curr_temperature, sachiMeter, input_type)

    sleep(0.5)
    
'''


