import os
import datetime
import Logic.Decisions
import Player.playerComm
import Sensors.RFIDTCP
import Queue
import logging

from time import sleep

logging.basicConfig(level=logging.INFO)
logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s] %(message)s")
rootLogger = logging.getLogger("root logger")
chipLogFormatter = logging.Formatter("%(asctime)s,[%(threadName)-12.12s],[%(levelname)-5.5s],%(message)s")
chipIdLogger = logging.getLogger("Chip ID logger")

logdir = os.path.join(os.curdir, "logs")
fileHandler = logging.FileHandler("{0}/{1}.log".format(logdir, 'where-now-{:%Y-%m-%d--%H-%M-%S}'.format(datetime.datetime.now())))
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)
chipIdFileHandler = logging.FileHandler("{0}/{1}.csv".format(logdir, 'where-now-{:%Y-%m-%d--%H-%M-%S}'.format(datetime.datetime.now())))
chipIdFileHandler.setFormatter(chipLogFormatter)
chipIdLogger.addHandler(chipIdFileHandler)

# consoleHandler = logging.StreamHandler()
# consoleHandler.setFormatter(logFormatter)
# rootLogger.addHandler(consoleHandler)

rootLogger.info("WhereNow art installation python logic started")

decision_queue = Queue.Queue()
player_queue = Queue.Queue()

player = Player.playerComm.playerComm(rootLogger)
decisionsThread = Logic.Decisions.Decisions(player_queue, decision_queue, rootLogger)
decisionsThread.start()

rfidThread = Sensors.RFIDTCP.RFIDTCP(decisionsThread, decision_queue, rootLogger, chipIdLogger)
rfidThread.start()

rootLogger.info("Threads started")

# open comm port to player
player_socket = player.connect("10.0.0.102","2100") #raspberry
# player_socket = player.connect("10.0.0.37","2100") #amir laptop

#initialize time vars
MyTime = datetime.datetime.now()
prevTime = MyTime
rfidTime = MyTime

# start us off with an initial decision
decision_queue.put(Logic.Decisions.DecisionEventType.PLAY_START)

while True:
    MyTime = datetime.datetime.now()
    sleep(0.5)
    if (MyTime - prevTime > datetime.timedelta(seconds=1)):
        player._set_is_playing()
        if player.is_playing and not player.prev_is_playing:
            decision_queue.put(Logic.Decisions.DecisionEventType.PLAY_START)
        if player.prev_is_playing and not player.is_playing:
            decision_queue.put(Logic.Decisions.DecisionEventType.PLAY_END)
        prevTime = MyTime
    try:
        songname = player_queue.get(False)
        if (songname == "STOP"):
            player.stop()
        elif (songname):
            player.play(songname)
    except Queue.Empty:
        # print "no new orders"
        pass

    # TODO: log all the chip IDs to csv

