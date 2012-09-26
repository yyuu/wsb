#!/usr/bin/env python

from __future__ import print_function, with_statement
import autobahn.websocket
import collections
import functools
import math
import optparse
import os
import sys
import time
import twisted.internet.reactor

table = collections.Counter({
    'started': 0,
    'done': 0,
    'bad': 0,
    'totalread': 0,
    'totalposted': 0,
    'err_conn': 0,
    'err_recv': 0,
    'err_length': 0,
    'err_except': 0,
})

stats = collections.deque()

class WebSocketBenchClientProtocol(autobahn.websocket.WebSocketClientProtocol):
    def __init__(self):
        self._start = None
        self._done = None

    def onOpen(self):
        self.doBench()

    def onMessage(self, msg, binary):
        global table, stats
        table['totalread'] += len(msg)

        if msg == table['message']:
            table['done'] += 1
        else:
            table['bad'] += 1
            if len(msg) != len(table['message']):
                table['err_length'] += 1

        if table['done'] < table['messages']:
            self._done = time.time()
            data = (self._start, 0, 0, max(0, self._done-self._start)) # tuple(starttime, waittime, ctime, time)
            stats.append(data)

            heartbeatres = 10000
            if table['done'] % heartbeatres == 0:
                print("Completed %d messages" % (table['done'],), file=sys.stderr)
                sys.stderr.flush()
        self.doBench()

    def doBench(self):
        global table
        if table['started'] < table['messages']:
            self._start = time.time()
            self.sendMessage(table['message'])
            table['started'] += 1
            table['totalposted'] += len(table['message'])
        else:
            self.sendClose()

    def failConnection(self, *args, **kwargs):
        global table
        table['bad'] += 1
        table['err_conn'] += 1
        autobahn.websocket.WebSocketClientProtocol.failConnection(self, *args, **kwargs)

    def protocolViolation(self, reason):
        global table
        table['bad'] += 1
        table['err_except'] += 1
        autobahn.websocket.WebSocketClientProtocol.protocolViolation(self, reason)

    def invalidPayload(self, reason):
        global table
        table['bad'] += 1
        table['err_except'] += 1
        autobahn.websocket.WebSocketClientProtocol.invalidPayload(self, reason)

    def failHandshake(self, reason):
        global table
        table['bad'] += 1
        table['err_except'] += 1
        autobahn.websocket.WebSocketClientProtocol.failHandshake(self, reason)

class WebSocketBenchClientFactory(autobahn.websocket.WebSocketClientFactory):
    protocol = WebSocketBenchClientProtocol

start = time.time()

def stop_reactor(reactor=None):
    if reactor is None:
        reactor = twisted.internet.reactor
    if reactor.running:
        global table
        if table['done'] + table['bad'] < table['messages']:
            reactor.callLater(1.0, functools.partial(stop_reactor, reactor))
        else:
            reactor.stop()

            global start
            timetaken = time.time() - start

            print("")
            print("")
            print("WebSocket URL: %s" % (table['websocket_server'],))
            print("")
            print("Message Body: %s" % (repr(table['message']),))
            print("Message Length: %d bytes" % (len(table['message']),))
            print("")
            print("Concurrency Level: %d" % (table['concurrency'],))
            print("Time taken for tests: %.3f seconds" % (timetaken,))
            print("Complete messages: %d" % (table['done'],))
            print("Failed messages: %d" % (table['bad'],))
            if 0 < table['bad']:
                print("    (Content: %d, Receive: %d, Length: %d, Exceptions: %d)" % (table['err_conn'], table['err_recv'], table['err_length'], table['err_except']))
            print("Write errors: %d" % (table['epipe'],))
            print("Total transferred: %d bytes" % (table['totalread'],))

            if 0 < timetaken and 0 < table['done']:
                print("Messages per second: %.2f [#/sec] (mean)" % (table['done'] / timetaken,))
                print("Time per message: %.3f [ms] (mean)" % (table['concurrency'] * timetaken * 1000 / table['done'],))
                print("Time per message: %.3f [ms] (mean, across all concurrent messages)" % (timetaken * 1000 / table['done'],))
                print("Transfer rate: %.2f [Kbytes/sec] received" % (table['totalread'] / 1024 / timetaken,))
                print("               %.2f kb/s sent" % (table['totalposted'] / timetaken / 1024,))
                print("               %.2f kb/s total" % ((table['totalread'] + table['totalposted']) / timetaken / 1024,))

            global stats

            if 0 < table['done']:
                total = 0
                mintot = 0xFFFFFFFF
                maxtot = 0
                for (_starttime, _waittime, _ctime, _time) in stats:
                    mintot = min(mintot, _time)
                    maxtot = max(maxtot, _time)
                    total += _time
                meantot = total / table['done']

                sdtot = 0
                for (_starttime, _waittime, _ctime, _time) in stats:
                    a = _time - meantot
                    sdtot += a * a

                sdtot = math.sqrt(sdtot / (table['done'] - 1)) if table['done'] > 1 else 0

                _stats = sorted(stats, cmp=lambda (a1, a2, a3, a_time), (b1, b2, b3, b_time): cmp(a_time, b_time))
                _starttime, _waittime, _ctime, _time = _stats[table['done'] / 2]
                mediantot = _time

                print("")
                print("Connection Times (ms)")
                print("              min  mean[+/-sd] median   max")
                print("Total:        %3d   %3d  %0.1f      %3d   %3d" % (mintot, meantot, sdtot, mediantot, maxtot))


def start_reactor(reactor=None):
    if reactor is None:
        reactor = twisted.internet.reactor

    reactor.callWhenRunning(functools.partial(stop_reactor, reactor))
    reactor.run()

def main(args):
    parser = optparse.OptionParser()
    parser.add_option("-c", dest="concurrency", default=1, type="int")
    parser.add_option("-n", dest="messages", default=100, type="int")
    parser.add_option("-m", dest="message", default="hello, world", type="string")
    (options, args) = parser.parse_args(args)

    if len(args) < 2:
        raise(RuntimeError("insufficient argument"))

    global table

    table['concurrency'] = options.concurrency
    table['messages'] = options.messages
    table['message'] = options.message

    table['websocket_server'] = args[1]

    for _ in xrange(table['concurrency']):
        factory = WebSocketBenchClientFactory(table['websocket_server'])
        factory.setProtocolOptions(version=13)
        autobahn.websocket.connectWS(factory)

    print("This is WebSocketBench, Version 0.1")
    print("Copyright 2012 Geisha Tokyo Entertainment Inc., http://www.geishatokyo.com/")
    print("Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/")
    print("Licensed to The Apache Software Foundation, http://www.apache.org/")
    print("")
    print("Benchmarking %s (be patient)" % (table['websocket_server'],))

    start_reactor()

if __name__ == '__main__':
    main(sys.argv)
