import json
import ast
import plotly.plotly as py
import plotly.graph_objs as go
import plotly.io as pio
import os
import numpy as np

#PARAMS
logs_path = "/home/stage/experiment/final_experiment"
output_path = "/home/stage/experiment/figures"


# Functions
def draw_scatterplot(**kwargs):

    data = []
    annotations = []

    for res in kwargs["results"]:

        x = res[kwargs['x_axis_prop']]
        y = res[kwargs['y_axis_prop']]
        a,x_markers,y_markers = annotate_extrema(y, 5, 3.5, 0.75, x)
        annotations = annotations + a

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

    # add annotations
    layout.update(dict(annotations=annotations))

    fig = go.Figure(data=data, layout=layout)
    pio.write_image(fig, kwargs["full_path"])


def inflexion_points(y,x):
    # a state machine to find inflexion points
    last_y = None
    points = []
    state = 0
    for x_val,y_val in zip(x,y):
        if state == 0:
            last_y = y_val
            last_x = x_val
            state = 1
        elif state == 1:
            if last_y > y_val:
                state = 2
                last_y = y_val
                last_x = x_val
                points.append({"x":last_x,"y":last_y, "inflexion": False})
            else:
                last_y = y_val
                last_x = x_val
                points.append({"x":last_x,"y":last_y, "inflexion": False})
                state = 3
        elif state == 2:
            if last_y < y_val:
                # change state because found an inflexion point
                state = 3
                # the last one was an inflexion point, annotate using the previous values
                points.append({"x":last_x,"y":last_y, "inflexion": True})
                last_y = y_val
                last_x = x_val
            else:
                # stay on the same state until the next inflexion point
                points.append({"x":last_x,"y":last_y, "inflexion": False})
                last_y = y_val
                last_x = x_val
        elif state == 3:
            if last_y > y_val:
                state = 2
                # annotate
                points.append({"x":last_x,"y":last_y, "inflexion": True})
                last_y = y_val
                last_x = x_val
            else:
                # stay on the same state until the next inflexion point
                points.append({"x":last_x,"y":last_y, "inflexion": False})
                last_y = y_val
                last_x = x_val
    # the last point can be tagged if needed
    points.append({"x":last_x,"y":last_y, "inflexion": True})
    return np.asarray(points)


def annotate_extrema(y, lag, threshold, influence,x):
    ip = inflexion_points(x=x,y=y)
    th = threshold_points(y,lag,threshold,influence)
    state = 0
    annotations = []
    markers_x = []
    markers_y = []
    for signal,inflexion in zip(th["signals"], ip):
        if state == 0:
            if signal == 0:
                # go to the next
                state = 0
            else:
                state = 1
                if inflexion["inflexion"]:
                    state = 0
                    annotations.append(go.layout.Annotation(text="("+"{:12.2f}".format(inflexion["x"]).strip()+";"+"{:12.2f}".format(inflexion["y"]).strip()+")", x=inflexion["x"], y=inflexion["y"],align="center", valign='bottom', showarrow=False))
                    markers_x.append(inflexion["x"])
                    markers_y.append(inflexion["y"])
        elif state == 1:
            if inflexion["inflexion"]:
                state = 0
                annotations.append(go.layout.Annotation(text="("+"{:12.2f}".format(inflexion["x"]).strip()+";"+"{:12.2f}".format(inflexion["y"]).strip()+")", x=inflexion["x"], y=inflexion["y"],align="center", valign='bottom', showarrow=False))
                markers_x.append(inflexion["x"])
                markers_y.append(inflexion["y"])
            else:
                # keep looking
                state = 1
    return annotations,markers_x,markers_y


# https://stackoverflow.com/questions/22583391/peak-signal-detection-in-realtime-timeseries-data/43512887#43512887
def threshold_points(y, lag, threshold, influence):
    signals = np.zeros(len(y))
    filteredY = np.array(y)
    avgFilter = [0]*len(y)
    stdFilter = [0]*len(y)
    avgFilter[lag - 1] = np.mean(y[0:lag])
    stdFilter[lag - 1] = np.std(y[0:lag])
    for i in range(lag, len(y)):
        if abs(y[i] - avgFilter[i-1]) > threshold * stdFilter [i-1]:
            if y[i] > avgFilter[i-1]:
                signals[i] = 1
            else:
                signals[i] = -1

            filteredY[i] = influence * y[i] + (1 - influence) * filteredY[i-1]
            avgFilter[i] = np.mean(filteredY[(i-lag+1):i+1])
            stdFilter[i] = np.std(filteredY[(i-lag+1):i+1])
        else:
            signals[i] = 0
            filteredY[i] = y[i]
            avgFilter[i] = np.mean(filteredY[(i-lag+1):i+1])
            stdFilter[i] = np.std(filteredY[(i-lag+1):i+1])

    return dict(signals = np.asarray(signals),
                avgFilter = np.asarray(avgFilter),
                stdFilter = np.asarray(stdFilter))

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

def draw_evolution(var_name, labeled_var_name, res):
    draw_scatterplot(title="Evolution of " + labeled_var_name + " across loops", results=res,
        x_axis_label="Loop", y_axis_label=labeled_var_name,
        x_axis_prop="loops", y_axis_prop=var_name,
        trace_name="scenario_name", full_path=os.path.join(output_path, '_ANNOTATED_EXT_HYP_' + labeled_var_name + '.png'))


# Initialization
logs_folders = [f.path for f in os.scandir(logs_path) if f.is_dir() ]


# Looping each session to get the HYP results
hyp_results = []
for path in logs_folders:

    # Get all the HYP files for the session
    session_files = [f for f in os.scandir(path) if not f.is_dir() and "_OUR_" in f.name]

    # Get the logs of the only file for HYP
    logs = read_file(session_files[0].path)

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
                         "scenario_name": "Secnario " + path[-1:], "_max_accuracy": round(max(accuracies), 2)})

print("hyp_results:\n", json.dumps(hyp_results, indent=4, sort_keys=True))

draw_evolution("accuracies", "accuracy", hyp_results)
# draw_evolution("diff_accuracies", "diff. accuracy", hyp_results)
draw_evolution("wrong_answers", "wrong answers", hyp_results)
draw_evolution("recall", "recall", hyp_results)
draw_evolution("precision", "precision", hyp_results)
draw_evolution("positive_precision", "positive precision", hyp_results)
