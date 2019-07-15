import json

def read_file(path):
    file = open(path, "r")
    logs = '['
    for line in file:

        # This is fixing the bug for the first printed results
        line = line.replace('", "f1"', ', "f1"')
        line = line.replace('", "recall"', ', "recall"')
        line = line.replace('", "precision"', ', "precision"')
        line = line.replace('", "positive_precision"', ', "positive_precision"')
        line = line.replace('", "wrong_pred_answers"', ', "wrong_pred_answers"')

        logs = logs + line

    logs = logs[:-1]
    logs = logs + ']'
    textual_logs = logs.replace('\n', ',')

    return json.loads(textual_logs)


logs_path = "C:\\Users\\gbosetti\\Desktop\\foot_2015_selected\\logs_07\\"

# Get the logs of the only file for HYP
filename = "session_2015_football_05_OUR_500__cnf0.0_ret0.4_bgr0.6_mda0.005_smss[500]"
initial_clicks=16
target_loops=[10,20,50,100]
file_content = read_file(logs_path + filename + ".txt")
logs = [line for line in file_content if 'loop' in line]


for target_loop in target_loops:

    accum_clicks = 0
    for loop in logs:
        accum_clicks += loop["wrong_pred_answers"]
        if(loop["loop"] >= target_loop):
            break

    print("Accum clicks at loop ", target_loop, ":", accum_clicks + initial_clicks)
