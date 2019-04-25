import json
import ast
import plotly.plotly as py
import plotly.graph_objs as go
import plotly.io as pio
import os

#PARAMS
logs_path = "C:\\Users\\gbosetti\\Desktop\\Experiments"
output_path = "C:\\Users\\gbosetti\\Desktop"


# Functions
def draw_scatterplot(**kwargs):

    data = []

    for res in kwargs["results"]:

        trace = go.Scatter(
            x=res[kwargs["x_axis_prop"]],
            y=res[kwargs["y_axis_prop"]],
            name=res[kwargs["trace_name"]]
        )
        data.append(trace)

    layout = go.Layout(
        title=go.layout.Title(
            text=kwargs["title"],
            xref='paper',
            x=0
        ),
        xaxis=go.layout.XAxis(
            title=go.layout.xaxis.Title(
                text=kwargs["x_axis_label"],
                font=dict(
                    size=18,
                    color='#7f7f7f'
                )
            )
        ),
        yaxis=go.layout.YAxis(
            title=go.layout.yaxis.Title(
                text=kwargs["y_axis_label"],
                font=dict(
                    size=18,
                    color='#7f7f7f'
                )
            )
        )
    )
    fig = go.Figure(data=data, layout=layout)
    pio.write_image(fig, kwargs["full_path"])

def read_file(path):
    file = open(path, "r")
    logs = '['
    for line in file:
        logs = logs + line
    logs = logs[:-1]
    logs = logs + ']'
    return json.loads(logs.replace('\n', ','))

def process_results(logs):
    loop_logs = [log for log in logs if 'loop' in log]

    loops_values = [log["loop"] for log in logs if 'loop' in log]  # datetime
    accuracies = [log["accuracy"] for log in logs if 'loop' in log]
    diff_accuracies = [0 if log["diff_accuracy"] == 'None' else float(log["diff_accuracy"]) for log in logs if
                       'loop' in log]
    # diff_accuracies = [float(log["diff_accuracy"]) for log in logs if 'loop' in log if log["diff_accuracy"] != 'None']
    wrong_answers = [log["wrong_pred_answers"] for log in logs if 'loop' in log]

    return loops_values, accuracies, diff_accuracies, wrong_answers

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
    loops_values, accuracies, diff_accuracies, wrong_answers = process_results(logs)
    hyp_results.append({ "loops": loops_values, "_total_loops": len(loops_values),
                         "accuracies": accuracies, "diff_accuracies": diff_accuracies,
                         "wrong_answers": wrong_answers, "_total_wrong_answers": sum(wrong_answers),
                         "scenario_name": "Secnario " + path[-1:], "_max_accuracy": round(max(accuracies), 2)})

print("hyp_results:\n", json.dumps(hyp_results, indent=4, sort_keys=True))

draw_scatterplot(title="Evolution of accuracy across loops", results=hyp_results,
    x_axis_label="Loop", y_axis_label="Accuracy",
    x_axis_prop="loops", y_axis_prop="accuracies",
    trace_name="scenario_name", full_path=os.path.join(output_path, 'HYP_accuracies.png'))

draw_scatterplot(title="Evolution of diff. accuracy across loops", results=hyp_results,
    x_axis_label="Loop", y_axis_label="Diff. accuracy",
    x_axis_prop="loops", y_axis_prop="diff_accuracies",
    trace_name="scenario_name", full_path=os.path.join(output_path, 'HYP_diff_accuracies.png'))

draw_scatterplot(title="Evolution of wrongly predicted labels across loops", results=hyp_results,
    x_axis_label="Loop", y_axis_label="Wrong predictions (max. 20 by loop)",
    x_axis_prop="loops", y_axis_prop="wrong_answers",
    trace_name="scenario_name", full_path=os.path.join(output_path, 'HYP_req_clicks.png'))

