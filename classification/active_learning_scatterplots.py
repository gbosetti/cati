import json
import ast
import plotly.plotly as py
import plotly.graph_objs as go
import plotly.io as pio
import os
import plotly
plotly.io.orca.config.executable = '/home/gabi/dev/miniconda3/bin/orca'  #May be useful in Ubuntu



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

        line = line.replace('", "f1"', ', "f1"')
        line = line.replace('", "recall"', ', "recall"')
        line = line.replace('", "precision"', ', "precision"')
        line = line.replace('", "positive_precision"', ', "positive_precision"')
        line = line.replace('", "wrong_pred_answers"', ', "wrong_pred_answers"')

        logs = logs + line
    logs = logs[:-1]
    logs = logs + ']'
    return json.loads(logs.replace('\n', ','))

def process_results(logs):
    loop_logs = [log for log in logs if 'loop' in log]

    loops_values = [log["loop"] for log in logs if 'loop' in log]  # datetime
    accuracies = [log["accuracy"] for log in logs if 'loop' in log]
    #diff_accuracies = [0 if log["diff_accuracy"] == 'None' else float(log["diff_accuracy"]) for log in logs if 'loop' in log]
    precision = [log["precision"] for log in logs if 'loop' in log]
    positive_precision = [log["positive_precision"] for log in logs if 'loop' in log]
    recall = [log["recall"] for log in logs if 'loop' in log]
    wrong_answers = [log["wrong_pred_answers"] for log in logs if 'loop' in log]

    return loops_values, accuracies, wrong_answers, precision, positive_precision, recall #diff_accuracies, wrong_answers

def print_in_file(content, path):
    file = open(path, "a+")
    file.write(content)
    file.close()

def draw_evolution(var_name, labeled_var_name, res, filename):
    draw_scatterplot(title="Evolution of " + labeled_var_name + " across loops", results=res,
        x_axis_label="Loop", y_axis_label=labeled_var_name,
        x_axis_prop="loops", y_axis_prop=var_name,
        trace_name="scenario_name", full_path=os.path.join(output_path, '_RES_' + filename + '.png'))


# Initialization
#logs_folders = [f.path for f in os.scandir(logs_path) if f.is_dir() ]

#PARAMS
logs_path = "/home/gabi/Bureau/test/session_IMG_2016_FDL_jackard_cnf0_3.txt"
output_path = "/home/gabi/Bureau/"


# Looping each session to get the HYP results
hyp_results = []
#for path in logs_folders:

# Get all the HYP files for the session
#session_files = [f for f in os.scandir(path) if not f.is_dir() and "_OUR_" in f.name]

# Get the logs of the only file for HYP
# logs = read_file(session_files[0].path)
logs = read_file(logs_path)

# Get the values from such file
loops_values, accuracies, wrong_answers, precision, positive_precision, recall = process_results(logs)
hyp_results.append({ "loops": loops_values,
                     "accuracies": accuracies, # "diff_accuracies": diff_accuracies,
                     "precision": precision,
                     "positive_precision": positive_precision,
                     "recall": recall,
                     "wrong_answers": wrong_answers,
                     "_total_wrong_answers": sum(wrong_answers),
                     "_total_loops": len(loops_values),
                     "scenario_name": "Secnario", "_max_accuracy": round(max(accuracies), 2)})

#print("hyp_results:\n", json.dumps(hyp_results, indent=4, sort_keys=True))

filename = logs_path.split("/").pop().split(".")[0]
#filename = os.path.splitext(tmp_path[len(tmp_path)-1])[0]
draw_evolution("accuracies", "accuracy", hyp_results, filename + "_accuracy")
# draw_evolution("diff_accuracies", "diff. accuracy", hyp_results)
draw_evolution("wrong_answers", "wrong answers", hyp_results, filename + "_wanswers")
#draw_evolution("recall", "recall", hyp_results)
draw_evolution("precision", "precision", hyp_results, filename + "_precision")
#draw_evolution("positive_precision", "positive precision", hyp_results)
