import time

class BackendLogger:

    def __init__(self):
        self.logs = []


    def add_log(self, message):
        curr_timestamp = time.time()
        self.logs.append({"timestamp": curr_timestamp, "content": message})
        print(curr_timestamp, message)

    def clear_logs(self):
        self.logs = []

    def get_logs(self):
        return self.logs
