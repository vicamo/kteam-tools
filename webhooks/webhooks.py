#!/usr/bin/python3

import sys

from flask import Flask, request, Response

app = Flask(__name__)

@app.route('/webhooks', methods=['POST'])
def respond():
    print("APW", request.json);
    sys.stdout.flush()
    return Response(status=200)
