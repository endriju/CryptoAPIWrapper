from flask import Flask, request
import os
import shelve
import requests
import logging
import threading
import atexit
from collections import deque


POOL_TIME = 6  # Seconds

shelf = shelve.open("responses_shelf")
queue = deque(shelf.keys())
dataLock = threading.Lock()
backgroundThread = threading.Thread()


def crypto_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.route('/crypto/sign')
    def crypto_sign_wrapper():
        message = request.args.get('message')

        if message in shelf:
            crypto_response = shelf[message]
            if crypto_response['last_status_code'] == requests.codes.ok:
                remove_from_shelf(message)
            return crypto_response

        crypto_response = crypto_sign_call(message)

        return crypto_response

    def crypto_sign_call(message, store_when_success=False):
        payload = {'message': message}
        headers = {'Authorization': 'ed98eecf8e94d2629cd7979c059c74b8'}
        r = requests.get('https://hiring.api.synthesia.io/crypto/sign', params=payload, headers=headers)

        if r.status_code != requests.codes.ok:
            wrapped_r = response(False, r.text, r.status_code)
            shelf[message] = wrapped_r
            queue.append(message)
        else:
            wrapped_r = response(True, r.text, r.status_code)
            if store_when_success:
                shelf[message] = wrapped_r
        return wrapped_r

    def response(success, value, last_status_code):
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
            app.logger.info("deleting from dict")
            del shelf[message]

    def interrupt():
        global backgroundThread
        backgroundThread.cancel()

    def background_thread_execute():
        global shelf
        global backgroundThread
        with dataLock:
            try:
                top_message = queue.popleft()
                crypto_sign_call(top_message, True)
            except IndexError:
                app.logger.info(f'empty queue, going to retry again in: {POOL_TIME}s')

        backgroundThread = threading.Timer(POOL_TIME, background_thread_execute, ()).start()

    def background_thread_start():
        global backgroundThread
        backgroundThread = threading.Timer(POOL_TIME, background_thread_execute, ()).start()

    background_thread_start()
    atexit.register(interrupt)

    @app.before_first_request
    def initialize():
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


# if __name__ == '__main__':
#     app = crypto_app()
#     app.run()
