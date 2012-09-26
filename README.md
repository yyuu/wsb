# wsb

## Overview

`wsb` is a tool for benchmarking WebSocket servers.

## Requirements

This application requires following python packages on runtime.

* [AutobahnPython](https://github.com/tavendo/AutobahnPython)

## Usage

Start benchmarking with 25 connections and 100 messages.

    % ./app.py -c 25 -n 100 ws://localhost:9000/
