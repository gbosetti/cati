import json
import ast
import plotly.plotly as py
import plotly.graph_objs as go
import plotly.io as pio
import os

#PARAMS
logs_path = "C:\\Users\\gbosetti\\Desktop\\experiments"
output_path = "C:\\Users\\gbosetti\\Desktop"


# Functions
def draw_barchart(**kwargs):

    data = []

    for res in kwargs["results"]:

        trace = go.Bar(
            x=res[kwargs["configs"]],  # ['0-0-1', '1-0-0', '2-2-6'],
            y=res[kwargs["max_var_value_by_config"]],  # [0.9, 0.3, 0.7],
            name=res[kwargs["trace_name"]] # at loop 10
        )
        data.append(trace)

    layout = go.Layout(
        title=go.layout.Title(
            text=kwargs["title"],
            xref='paper',
            x=0
        ),
        barmode='group'
    )
    fig = go.Figure(data=data, layout=layout)
    pio.write_image(fig, kwargs["full_path"])

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

    print(textual_logs)

    return json.loads(textual_logs)

def process_results(logs):
    loop_logs = [log for log in logs if 'loop' in log]

    loops_values = [log["loop"] for log in logs if 'loop' in log]  # datetime
    accuracies = [log["accuracy"] for log in logs if 'loop' in log]
    # diff_accuracies = [float(log["diff_accuracy"]) for log in logs if 'loop' in log if log["diff_accuracy"] != 'None']
    wrong_answers = [log["wrong_pred_answers"] for log in logs if 'loop' in log]

    return loops_values, accuracies, wrong_answers

def print_in_file(content, path):
    file = open(path, "a+")
    file.write(content)
    file.close()




# Initialization
logs_folders = [f.path for f in os.scandir(logs_path) if f.is_dir() ]


# Looping each session to get the HYP results
hyp_results = []
for path in logs_folders:

    # Get all the HYP files for the session
    session_files = [f for f in os.scandir(path) if not f.is_dir() and "_HYP_" in f.name]

    # Get the logs of the only file for HYP
    logs = read_file(session_files[0].path)

    # Get the values from such file
    loops_values, accuracies, wrong_answers = process_results(logs)
    hyp_results.append({ "loops": loops_values, "_total_loops": len(loops_values),
                         "accuracies": accuracies,
                         "wrong_answers": wrong_answers, "_total_wrong_answers": sum(wrong_answers),
                         "scenario_name": "Secnario " + path[-1:], "_max_accuracy": round(max(accuracies), 2)})

print("hyp_results:\n", json.dumps(hyp_results, indent=4, sort_keys=True))

draw_barchart(title="Evolution of accuracy across loops", results=hyp_results,
                trace_name="at loop 10", full_path=os.path.join(output_path, 'OUR_accuracies' +  + '.png'),
                configs=['0-0-1', '1-0-0', '2-2-6'],
                max_var_value_by_config=[0.9, 0.3, 0.7])
