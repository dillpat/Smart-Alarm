'''
Smart Alarm Clock
'''
from time import strftime
from datetime import datetime
import time
from sched import scheduler
import threading
import json
import logging
from logging.handlers import RotatingFileHandler
from collections import deque
import requests
import pyttsx3
from flask import Flask, Response, render_template, request, redirect


# configuration defults
# Declare a variavel config_file which is intilaized to config.json
config_file: str = "config.json"
config_dict: dict = {}


# Weather Defults
current_city: str = "Exeter"

'''
# stores infomation about set alarms
{"datetime":{"alarm":"string",
             "message":"string",
             "event":none,
             "jingle":ringtone,
             }
}
'''
set_of_alarms: dict = {}

# Creates a list which holds 5 values, the oldest value is removed to allow for a new value
notifications_history: list = deque(5*[], 5)
alarm_list: list = set_of_alarms.values()

# Alarm notification defaults
active_notifications: str = ""

def news_headlines() -> dict:
    '''
    news_headlines retrives the current world news headlines from a website
    and returns a dictionary containing the headlines with a url link
    to the full article.
    '''
    url = config_dict['api_keys']['news']['url'] +\
       'sources=bbc-news&' +\
       'apiKey=' + config_dict['api_keys']['news']['key']
    response = requests.get(url)
    headlines = response.json()
    if headlines["status"] == "ok" and headlines["totalResults"] > 0:
        return headlines["articles"]
    return []

# Intializing scheduler
s = scheduler(time.time, time.sleep)
def notify_user(alarm_key=''):
    '''
    notify_user a callback function called by the scheduler when an alarm event
    has occured and it notifies the user of the event using the text to speech
    engine or an audible sound.

    alarm_key - event key(datetime)
    '''
    global active_notifications
    global notifications_history
    global set_of_alarms
    if alarm_key in set_of_alarms:
        cancelled_alarm = set_of_alarms[alarm_key]
        del set_of_alarms[alarm_key]
        engine = pyttsx3.init()
        if cancelled_alarm["message"]:
            engine.say(cancelled_alarm["message"])
        else:
            print('\a')

        # replaces the oldest value from notification list
        notifications_history.appendleft(cancelled_alarm)

        # Run the text to speech engine
        engine.runAndWait()
        engine.stop()

e = threading.Event()
exit_event_sched = False
def event_sched():
    '''
    event_sched is the scheduler event thread handler, it runs in a loop as
    a background thread that runs the scheduler.
    '''
    while not exit_event_sched:
        if not s.empty():
            next_ev = s.run(False)
            if next_ev is not None:
                time.sleep(min(1, next_ev))
            else:
                time.sleep(1)
        else:
            e.wait()
            e.clear()

# start scheduler event handler
t = threading.Thread(target=event_sched)
t.start()


# Initialise flask framework
app = Flask(__name__)


# Functions to integrate with flask logging.
@app.after_request
def after_request(response):
    '''
    This logs the web page after every request. This avoids duplication
    of every registry in the log since 500 is already logged via
    @app.errorhandler
    '''
    if response.status_code != 500:
        time_stamp = strftime('[%Y-%b-%d %H:%M]')
        logger.info('%s %s %s %s %s %s',
                    time_stamp,
                    request.remote_addr,
                    request.method,
                    request.scheme,
                    request.full_path,
                    response.status)
    return response

@app.errorhandler(404)
def not_found(e) ->str:
    '''
    Handle URL not found exceptions
    '''
    return 'Not Found: The requested URL was not found on the server', 404

@app.errorhandler(Exception)
def exceptions(e) -> [str, int]:
    '''
    Logging after every expection.
    Handle program crash exception. Logs stack back trace
    '''
    time_stamp = strftime('[%Y-%b-%d %H:%M]')
    trace_back = traceback.format_exc()
    logger.info('%s %s %s %s %s 5xx INTERNAL SERVER ERROR\n%s',
                time_stamp,
                request.remote_addr,
                request.method,
                request.scheme,
                request.full_path,
                trace_back)
    return "Internal Server Error", 500

@app.route('/')
def clock() ->str:
    '''
    Home endpoint: query parameter(s) city

    Displays the home page using the flask framework.
    '''
    global current_city
    # Looking for city variable in the http request
    new_city = request.args.get("city")
    if new_city:
        current_city = new_city
    else:
        # If user has incorrect city value use default
        new_city = current_city
    if new_city:
        base_url = config_dict['api_keys']['weather']['url']
        api_key = config_dict['api_keys']['weather']['key']
        complete_url = base_url + "appid=" + api_key + "&q=" + new_city + "&units=metric"
        # Request to the weather web service for current weather updates
        response = requests.get(complete_url)
        reply = response.json()
        if reply['cod'] == 200: # Ok
            main = reply["main"]
            temperature = main["temp"]
            pressure = main["pressure"]
            humidity = main["humidity"]
            weather = reply["weather"]
            description = weather[0]["description"]
            cloud = reply['clouds']['all']
            wind = reply['wind']['speed']
            icon = weather[0]['icon']
            home_template = config_dict['file_paths']['html']['home_page']
            return render_template(home_template,
                                   city=new_city.title(),
                                   temperature=temperature,
                                   pressure=pressure,
                                   humidity=humidity,
                                   description=description.title(),
                                   cloud=cloud,
                                   wind=wind,
                                   icon=icon,
                                   # Passing the news headlines as articles to the render template
                                   articles=news_headlines())
    home_template = config_dict['file_paths']['html']['home_page']
    return render_template(home_template)

@app.route('/alarm')
def alarm() ->str:
    '''
    Alarm actions endpoints; query parameter(s): 'Set', 'Cancel'.

    Retrives the value for the alarm parameter from the http Get request.
    '''
    alarm = request.args.get("alarm")
    if alarm == 'Set':
        datetime_now = datetime.now().strftime("%Y-%m-%dT%H:%M")
        set_alarm = config_dict['file_paths']['html']['set_alarm']
        return render_template(set_alarm, datetime_now=datetime_now)

    if alarm == 'Cancel':
        cancel_alarm = config_dict['file_paths']['html']['cancel_alarm']
        return render_template(cancel_alarm, alarms=alarm_list)
    return "Oops --- something has gone wrong!"


@app.route('/setalarm', methods=['POST', 'GET'])
def set_alarm() ->str:
    '''
    set_alarm endpoints; query parameter(s): 'alarm', 'message'.
    '''
    global set_of_alarms
    alarm = request.args.get("alarm")
    msg = request.args.get("message")
    if alarm:
        # Convert time to seconds
        alarm_time = datetime.fromisoformat(alarm).timestamp()
        # Gets delta for event in seconds
        alarm_in_seconds = alarm_time - datetime.now().timestamp()
        if alarm_in_seconds < 0:
            alarm_in_seconds = 0
        # Schedule event
        evt = s.enter(alarm_in_seconds, priority=1, action=notify_user, argument=(alarm,))
        # Saves the event for reference
        set_of_alarms[alarm] = {"alarm":alarm,
                                "message":msg,
                                "event":evt,
                                "jingle":None,
                                }
        # Wakes up the scheduler
        if not e.is_set():
            e.set()

        # Takes user back to home page
        return redirect('/')

    datetime_now = datetime.now().strftime("%Y-%m-%dT%H:%M")
    set_alarm = config_dict['file_paths']['html']['set_alarm']
    return render_template(set_alarm, datetime_now=datetime_now)

@app.route('/cancelalarm', methods=['Post', 'Get'])
def cancel_alarm() ->str:
    '''
    Cancel alarm endpoint; query parameter(s): 'alarm'

    cancel_alarm displays all the set alarms and allows user to cancel
    one of the set alarms.
    '''
    global set_of_alarms
    alarm = request.args.get('alarm')
    if alarm:
        # Remove event from set_of_alarms database
        cancelled_alarm = set_of_alarms[alarm]
        del set_of_alarms[alarm]

        # Remove event from scheduler queue
        s.cancel(cancelled_alarm["event"])

        # Takes user back to home page
        return redirect('/')

    cancel_alarm = config_dict['file_paths']['html']['cancel_alarm']
    return render_template(cancel_alarm, alarms=alarm_list)


@app.route('/time_feed')
def time_feed() ->str:
    '''
    time_feed endpoint;

    Renders html to display current time and list of past notifications in
    reverse chronological order.
    '''
    d_time = datetime.now().strftime("%Y.%m.%d|%H:%M:%S")
    history = [x for x in notifications_history]
    notification_list = config_dict['file_paths']['html']['alert_list']
    alerts = render_template(notification_list, dt=d_time, notifications=history)
    def generate():
        yield alerts
    return Response(generate(), mimetype='text')

def load_config(filename):
    '''
    Loads a json format configuration file.

    filename - configuration file name
    '''
    config = {}
    # load json config file
    with open(filename, 'r') as file:
        config = json.load(file)
        print(config)
    return config


if __name__ == '__main__':
    # Load config
    config_dict = load_config(config_file)

    # Initialize logger
    log_file = config_dict['logging']['log_file']
    log_level = int(config_dict['logging']['log_level'])
    handler = RotatingFileHandler(log_file,
                                  maxBytes=100000,
                                  backupCount=3)
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    logger.addHandler(handler)

    # Start up flask framework
    app.run(debug=True, threaded=True)

    # Clear flags so threads can exit
    exit_event_shced = True
    e.set()

    # Wait for threads to finish
    t.join()
