import time
import os
from flask import jsonify

class BackendLogger:

    def __init__(self, filename="cati-logs.txt"):
        #self.logs = []
        self.filename = filename

        # folder = os.path.dirname(filename)
        #if not os.path.exists(folder):
        #    os.makedirs(folder)

    def add_log(self, message):
        curr_timestamp = time.time()
        #self.logs.append({"timestamp": curr_timestamp, "content": message})
        message = message.replace('\r', '').replace('\n', '')
        print(curr_timestamp, message)
        file = open(self.filename, "a+")
        file.write('{"timestamp": ' + str(curr_timestamp) + ', "content": "' + message + '"},')
        file.close()

    def add_raw_log(self, message):
        file = open(self.filename, "a+")
        file.write(message)
        file.close()
        print(message)

    def clear_logs(self):
        print("Removing ", self.filename)
        if os.path.isfile(self.filename):
            os.remove(self.filename)

    def get_logs(self):

        try:
            file = open(self.filename, "r")
            logs = '['
            for line in file:
                logs = logs + line

            logs = logs[:-1]
            logs = logs + ']'

            #print('logs', logs)
            return logs

        except IOError as err:
            # print(self.filename + ": the file was not found.", err)
            return '[]'

