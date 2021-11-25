from flask import Flask, request
import os
import datetime
import shelve
import requests
import logging
import threading
import atexit

POOL_TIME = 6  # Seconds

shelf = shelve.open("requests_shelf")
dataLock = threading.Lock()
backgroundThread = threading.Thread()


MIN_RETRY_DELAY_SECONDS = {
    requests.codes.bad_gateway: 5,
    requests.codes.too_many: 10
}


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
            if shelf[message]['last_status_code'] == requests.codes.ok:
                crypto_response = shelf[message]
                remove_from_shelf(message)
                return crypto_response
            return update_message_retry_times(message)

        app.logger.info("calling real thing")

        crypto_response = crypto_sign_call(message)
        if crypto_response['last_status_code'] != requests.codes.ok:
            shelf[message] = crypto_response

        return crypto_response

    def crypto_sign_call(message):
        payload = {'message': message}
        headers = {'Authorization': 'ed98eecf8e94d2629cd7979c059c74b8'}
        r = requests.get('https://hiring.api.synthesia.io/crypto/sign', params=payload, headers=headers)

        if r.status_code == requests.codes.ok:
            app.logger.info("success")
            remove_from_shelf(message)
            return response(True, r.text, requests.codes.ok)
        elif r.status_code == requests.codes.too_many:
            app.logger.info("too_many")
            return response(False, None, requests.codes.too_many)
        elif r.status_code == requests.codes.bad_gateway:
            app.logger.info("bad_gateway")
            return response(False, None, requests.codes.bad_gateway)

    def response(success, value, last_status_code):
        r = {
            'success': success,
            'value': value,
            'last_status_code': last_status_code,

        }
        if last_status_code is not requests.codes.ok:
            retry_info = calculate_retry_info()
            r['scheduled_retry'] = retry_info['scheduled_retry']
            r['retry_in_seconds'] = retry_info['retry_in_seconds']
        return r

    def remove_from_shelf(message):
        if message in shelf:
            app.logger.info("deleting from dict")
            del shelf[message]

    def update_message_retry_times(message):
        app.logger.info("in shelf!")
        current_time = datetime.datetime.now()
        shelved_message = shelf[message]
        app.logger.info(shelved_message)
        app.logger.info(current_time)
        app.logger.info(shelved_message['scheduled_retry'] > current_time)
        if shelved_message['scheduled_retry'] > current_time:
            app.logger.info("not yet time to retry, update retry time!")
            # not yet time to retry, update retry time
            shelved_message['retry_in_seconds'] = (shelved_message['scheduled_retry'] - current_time).total_seconds()
        else:
            retry_info = calculate_retry_info()
            shelved_message['scheduled_retry'] = retry_info['scheduled_retry']
            shelved_message['retry_in_seconds'] = retry_info['retry_in_seconds']

        app.logger.info(shelved_message)
        shelf[message] = shelved_message
        return shelf[message]

    def calculate_retry_info():
        message_keys = list(shelf.keys())
        # TODO count only not_ok responses (there can be responses that were not picked up yet by clients
        delay = POOL_TIME * len(message_keys)
        retry_info = {
            'scheduled_retry': datetime.datetime.now() + datetime.timedelta(seconds=delay),
            'retry_in_seconds': delay
        }
        return retry_info

    def interrupt():
        global backgroundThread
        backgroundThread.cancel()

    def background_thread_execute():
        global shelf
        global backgroundThread
        with dataLock:
            message_keys = list(shelf.keys())
            message_keys.sort()
            for message_key in message_keys:
                # call crypto API for the response that is the soonest to retry
                # this is hard - which request to retry?
                app.logger.info(f'Message: {message_key}, Status: {shelf[message_key]}')

        backgroundThread = threading.Timer(POOL_TIME, background_thread_execute, ())
        backgroundThread.start()

    def background_thread_start():
        global backgroundThread
        backgroundThread = threading.Timer(POOL_TIME, background_thread_execute, ())
        backgroundThread.start()

    background_thread_start()
    # When you kill Flask (SIGTERM), clear the trigger for the next thread
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


if __name__ == '__main__':
    app = crypto_app()
    app.run()
