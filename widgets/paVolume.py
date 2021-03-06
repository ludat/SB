#!/bin/env python3

import threading
import logging

import subprocess
import re

IS_SAFE = True
NAME = 'pulseAudioStatus'
logger = logging.getLogger('WIDGET')


class mainThread (threading.Thread):
    def __init__(self, codeName, mainQueue, inputQueue=None):
        threading.Thread.__init__(self)
        self.name = NAME
        self.codeName = codeName
        self.mainQueue = mainQueue
        self.lastUpdate = "dsadwa"
        self.inputQueue = inputQueue
        self.inputThread = InputThread(self.name, self.inputQueue)
        self._killed = threading.Event()
        self._killed.clear()

    def run(self):
        if self.inputQueue is not None:
            self.inputThread.start()
        susc = subprocess.Popen(
            ["pactl", "subscribe"],
            stdout=subprocess.PIPE,
            universal_newlines=True)
        stateRegex = re.compile(
            (
                "Mute: (?P<mute>\w+).*?"
                "Volume.*?(?P<left>[0-9]+)%.*?(?P<right>[0-9]+)%.*"
            ),
            re.DOTALL)
        while True:
            statusProc = subprocess.Popen(
                ["pactl", "list", "sinks"],
                stdout=subprocess.PIPE,
                universal_newlines=True)
            statusProc.wait()
            statusOutput = statusProc.stdout.read()
            d = stateRegex.search(statusOutput).groupdict()
            if d['mute'] == 'no':
                result = (
                    "{}% ".format((int(d['left']) + int(d['left'])) // 2) +
                    "^i(icons/xbm/spkr_01.xbm)"
                )
            if d['mute'] == 'yes':
                result = (
                    " ^i(icons/xbm/spkr_02.xbm)"
                )
            if self.killed():
                break
            self.updateContent(self.parse(result))
            while True:
                delta = susc.stdout.readline()[:-1].split(" ")
                if delta == ['']:
                    break
                if delta[3] == "sink"and delta[4] == "#0":
                    break
        susc.terminate()
        self.inputThread.kill()
        return 0

    def updateContent(self, string):
        if string != self.lastUpdate:
            self.mainQueue.put({
                'name': self.name,
                'codeName': self.codeName,
                'content': string})
            self.lastUpdate = string

    def parse(self, string):
        string = "^ca(1, echo " + self.codeName + "@clicked)" + string
        string = string + "^ca()"
        return string

    def killed(self):
        return self._killed.is_set()

    def kill(self):
        self._killed.set()


class InputThread (threading.Thread):
    def __init__(self, codeName, inputQueue):
        threading.Thread.__init__(self)
        self.name = NAME
        self.code = codeName
        self.inputQueue = inputQueue
        self._killed = threading.Event()
        self._killed.clear()

    def run(self):
        stateRegex = re.compile(
            (
                "Mute: (?P<mute>\w+).*?"
                "Volume.*?(?P<left>[0-9]+)%.*?(?P<right>[0-9]+)%.*"
            ),
            re.DOTALL)
        while True:
            if self.killed():
                break
            item = self.inputQueue.get()
            logger.debug(
                "MESSAGE RECIVED: %s", item)
            if item == "clicked":
                statusProc = subprocess.Popen(
                    ["pactl", "list", "sinks"],
                    stdout=subprocess.PIPE,
                    universal_newlines=True)
                statusProc.wait()
                statusOutput = statusProc.stdout.read()
                d = stateRegex.search(statusOutput).groupdict()
                if d['mute'] == 'no':
                    s = "1"
                if d['mute'] == 'yes':
                    s = "0"
                resultProc = subprocess.Popen(
                    ["pactl", "set-sink-mute", "0", s])
                resultProc.wait()
        return 0

    def killed(self):
        return self._killed.is_set()

    def kill(self):
        self._killed.set()

if __name__ == "__main__":
    import queue

    class TestInputThread(threading.Thread):
        def __init__(self, inputQueue):
            threading.Thread.__init__(self)
            self.inputQueue = inputQueue

        def run(self):
            while True:
                self.inputQueue.put(input())

    inputQueue = queue.Queue()
    mainQueue = queue.Queue()

    inputThread = TestInputThread(inputQueue)

    thread = mainThread(
        mainQueue,
        inputQueue=inputQueue)
    thread.start()
    inputThread.start()

    while True:
        print(mainQueue.get()['content'])
