from flask import Flask, request
import os
import shelve
import requests
import logging
import threading
import atexit
from collections import deque


SYNTHESIA_CRYPTO_SIGN_API_ENDPOINT = 'https://hiring.api.synthesia.io/crypto/sign'
POOL_TIME = 6  # Seconds

shelf = shelve.open("responses_shelf")
queue = deque(shelf.keys())
dataLock = threading.Lock()
backgroundThread = threading.Thread()


def crypto_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    if test_config is None:
        app.config.from_pyfile('application.cfg.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.route('/crypto/sign')
    def crypto_sign_wrapper():
        """The Wrapping API handling method."""

        message = request.args.get('message')

        if message in shelf:
            crypto_response = shelf[message]
            if crypto_response['last_status_code'] == requests.codes.ok:
                remove_from_shelf(message)
            return crypto_response

        crypto_response = crypto_sign_call(message)
        return crypto_response

    def crypto_sign_call(message, store_when_success=False):
        """Synthesia Crypto API client and response processing"""

        payload = {'message': message}
        headers = {'Authorization': app.config['CRYPTO_API_KEY']}
        r = requests.get(SYNTHESIA_CRYPTO_SIGN_API_ENDPOINT, params=payload, headers=headers)

        if r.status_code != requests.codes.ok:
            wrapped_r = prepare_response(False, r.text, r.status_code)
            shelf[message] = wrapped_r
            queue.append(message)
        else:
            wrapped_r = prepare_response(True, r.text, r.status_code)
            if store_when_success:
                shelf[message] = wrapped_r
        return wrapped_r

    def prepare_response(success, value, last_status_code):
        r = {
            'success': success,
            'value': value,
            'last_status_code': last_status_code
        }
        if last_status_code is not requests.codes.ok:
            r['retry_in_seconds'] = (len(queue) + 1) * POOL_TIME
        return r

    def remove_from_shelf(message):
        if message in shelf:
            app.logger.info(f'removing response from shelve: {message}s')
            del shelf[message]

    def interrupt():
        global backgroundThread
        backgroundThread.cancel()

    def background_thread_execute():
        """Periodically check messages queue and call Synthesia Crypto API for leftmost message"""

        global shelf
        global backgroundThread
        with dataLock:
            try:
                top_message = queue.popleft()
                app.logger.info(f'going to retry message: {top_message}s')
                crypto_sign_call(top_message, True)
            except IndexError:
                app.logger.info(f'empty queue, going to retry again in: {POOL_TIME}s')

        backgroundThread = threading.Timer(POOL_TIME, background_thread_execute, ()).start()

    def background_thread_start():
        global backgroundThread
        backgroundThread = threading.Timer(POOL_TIME, background_thread_execute, ()).start()

    if app.config['CRYPTO_API_KEY']:
        background_thread_start()
        atexit.register(interrupt)

    @app.before_first_request
    def initialize():
        """Utility to display logs"""

        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            """%(levelname)s in %(module)s [%(pathname)s:%(lineno)d]:%(message)s"""
        )
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return app
