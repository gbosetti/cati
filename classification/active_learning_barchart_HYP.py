import json
import ast
import plotly.plotly as py
import plotly.graph_objs as go
import plotly.io as pio
import os
import re

# PARAMS
scenario_number = "4"
logs_path = "/home/stage/experiment/Experiments_for_plotting/experiment_" + scenario_number
output_path = "/home/stage/experiment/figures_" + scenario_number
initial = {"1": "2 events",
           "2": "Full events",
           "3": "All image clusters of 2 events",
           "4": "All image clusters of all events"}

initial_f = {"1": "_2_events",
             "2": "_full_events",
             "3": "_all_image_clusters_of_2_events",
             "4": "_all_image_clusters_of_all_events"}
initial_str = initial[scenario_number]
initial_file = initial_f[scenario_number]


# Functions
def draw_barchart(**kwargs):
    data = []

    for loop_index in kwargs["values_by_loop"]:

        res = []
        all_configs_at_loop = kwargs["values_by_loop"][loop_index]
        # the value of the prop_name in the loop loop_index for each config
        for config_log in all_configs_at_loop:
            res.append(config_log[kwargs["prop_name"]])

        # sort the values so all the charts have the same disposition of the configurations
        [x_values, y_values] = [list(x) for x in zip(*sorted(zip(kwargs["configs"], res), key=lambda pair: pair[0], reverse=True))]
        trace = go.Bar(
            x= x_values, #kwargs["configs"],  # ['giraffes', 'orangutans', 'monkeys']
            y=y_values, #res,  # [0.9, 0.3, 0.7],
            name="at " + loop_index  # at loop 10
        )
        data.append(trace)


    layout = go.Layout(
        title=go.layout.Title(
            text=kwargs["title"],
            xref='paper',
            x=0
        ),
        xaxis=dict(
            title=kwargs["x_axis_title"],
            tickmode='linear',
            ticks='outside',
            tick0=0,
            dtick=0.25,
            ticklen=8,
            tickwidth=4,
            tickangle=45,
            tickcolor='#000'
        ),
        yaxis=dict(
            title=kwargs["y_axis_title"],
            range=[kwargs["min_y_axis_value"], kwargs["max_y_axis_value"]],
            showgrid=True,
            showline=True,
            tickmode='linear',
            ticks='outside',
            tick0=0,
            dtick=kwargs["y_dtick"],
            ticklen=8,
            tickwidth=4,
            tickcolor='#000'
        ),
        barmode='group',
        autosize=False,
        width=1200,
        height=600
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

    #  print(textual_logs)

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
logs_folders = [f.path for f in os.scandir(logs_path) if f.is_dir()]
target_loops = [1, 10, 20, 50, 100]
configs = []
values_by_loop = {}
loop_prefix = "loop "
for loop in target_loops:
    values_by_loop[loop_prefix + str(loop)] = []


def get_config_value(prop_name, full_text):
    start_index = full_text.index(prop_name) + 4
    end_index = start_index + 3

    return full_text[start_index:end_index]


def get_config_name(full_text):
    hyp = re.search(r'HYP', full_text, re.M | re.I)
    if hyp is None:
        cnf = str(int(float(get_config_value("_cnf", full_text)) * 100))
        ret = str(int(float(get_config_value("_ret", full_text)) * 100))
        bgr = str(int(float(get_config_value("_bgr", full_text)) * 100))

        return cnf + "·" + ret + "·" + bgr
    else:
        print("hyp")
        return "HYP"


def get_value_at_loop(prop_name, loop_index, logs):
    target_loop = [log for log in logs if log["loop"] == loop_index]

    return target_loop[0]


# Looping each session to get the HYP results
hyp_results = []
for path in logs_folders:

    # Get all the OUR files for the session
    # session_files = [f for f in os.scandir(path) if not f.is_dir() and "_OUR_" in f.name]
    session_files = [f for f in os.scandir(path) if not f.is_dir()]

    for file in session_files:
        # Get the logs of the only file for HYP
        file_content = read_file(file.path)
        logs = [line for line in file_content if 'loop' in line]

        configs.append(get_config_name(file.name))

        for loop in target_loops:
            values_by_loop[loop_prefix + str(loop)].append(get_value_at_loop("accuracy", loop, logs))

    # Get the values from such file
    # loops_values, accuracies, wrong_answers = process_results(logs)
    # hyp_results.append({ "loops": loops_values, "_total_loops": len(loops_values),
    #                      "accuracies": accuracies,
    #                      "wrong_answers": wrong_answers, "_total_wrong_answers": sum(wrong_answers),
    #                      "scenario_name": "Secnario " + path[-1:], "_max_accuracy": round(max(accuracies), 2)})

# print("hyp_results:\n", json.dumps(hyp_results, indent=4, sort_keys=True))

draw_barchart(title="Evolution of accuracy across loops and configurations " + initial_str,
              values_by_loop=values_by_loop,
              x_axis_title="Configs (hw·dw·bw)", y_axis_title="Accuracy",
              full_path=os.path.join(output_path, 'OUR_accuracies' + initial_file + '.png'), configs=configs,
              target_loops=target_loops, prop_name="accuracy", max_y_axis_value=1, min_y_axis_value=0.65, y_dtick=0.01)

draw_barchart(title="Evolution of the precision on positives across loops and configurations " + initial_str,
              values_by_loop=values_by_loop,
              x_axis_title="Configs (hw·dw·bw)", y_axis_title="Precision on positives",
              full_path=os.path.join(output_path, 'OUR_positive_precision' + initial_file + '.png'), configs=configs,
              target_loops=target_loops, prop_name="positive_precision", max_y_axis_value=1, min_y_axis_value=0.00,
              y_dtick=0.05)

draw_barchart(title="Evolution of the precision across loops and configurations " + initial_str,
              values_by_loop=values_by_loop,
              x_axis_title="Configs (hw·dw·bw)", y_axis_title="Precision",
              full_path=os.path.join(output_path, 'OUR_precision' + initial_file + '.png'), configs=configs,
              target_loops=target_loops, prop_name="precision", max_y_axis_value=1, min_y_axis_value=0.9, y_dtick=0.01)

draw_barchart(title="Evolution of the score across loops and configurations " + initial_str,
              values_by_loop=values_by_loop,
              x_axis_title="Configs (hw·dw·bw)", y_axis_title="F1 Score",
              full_path=os.path.join(output_path, 'OUR_f1_score' + initial_file + '.png'), configs=configs,
              target_loops=target_loops, prop_name="f1", max_y_axis_value=1, min_y_axis_value=0.75, y_dtick=0.01)

draw_barchart(title="Evolution of the recall across loops and configurations " + initial_str,
              values_by_loop=values_by_loop,
              x_axis_title="Configs (hw·dw·bw)", y_axis_title="Recall",
              full_path=os.path.join(output_path, 'OUR_recall' + initial_file + '.png'), configs=configs,
              target_loops=target_loops, prop_name="recall", max_y_axis_value=1, min_y_axis_value=0.6, y_dtick=0.01)

draw_barchart(title="Evolution of the wrong predictions across loops and configurations " + initial_str,
              values_by_loop=values_by_loop,
              x_axis_title="Configs (hw·dw·bw)", y_axis_title="Number of wrong predicitons",
              full_path=os.path.join(output_path, 'OUR_wrong' + initial_file + '.png'), configs=configs,
              target_loops=target_loops, prop_name="wrong_pred_answers", max_y_axis_value=20, min_y_axis_value=0.00,
              y_dtick=5)
