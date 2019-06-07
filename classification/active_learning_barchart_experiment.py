import json
import ast
import plotly.plotly as py
import plotly.graph_objs as go
import plotly.io as pio
import os
import re

#PARAMS
logs_path = "C:\\Users\\gbosetti\\Desktop\\experiments_2015_moving_repeated"
output_path = "C:\\Users\\gbosetti\\Desktop"


# Functions
def draw_barchart(**kwargs):

    data = []

    for loop_index in kwargs["values_by_loop"]:

        res = []
        all_configs_at_loop = kwargs["values_by_loop"][loop_index]
        for config_log in all_configs_at_loop:
            res.append(config_log[kwargs["prop_name"]])

        text = res
        if kwargs["round_values"]:
            text = ["<b>" + str(round(val, 5)) + "<b>" for val in text]

        if kwargs["show_labels"]:
            trace = go.Bar(
                x=kwargs["configs"],  # ['giraffes', 'orangutans', 'monkeys']
                y=res,  # [0.9, 0.3, 0.7],
                text=text,
                textfont=dict(
                    family='Arial'
                ),
                textposition='auto',
                name="at " + loop_index # at loop 10
            )
        else:
            trace = go.Bar(
                x=kwargs["configs"],  # ['giraffes', 'orangutans', 'monkeys']
                y=res,  # [0.9, 0.3, 0.7],
                textposition='auto',
                name="at " + loop_index  # at loop 10
            )
        data.append(trace)

    layout = go.Layout(
        # title=go.layout.Title( text=kwargs["title"], xref='paper', x=0 ),
        xaxis=dict(
            title=kwargs["x_axis_title"],
            tickmode='linear',
            ticks='outside',
            tick0=0,
            dtick=0.25,
            ticklen=8,
            tickwidth=4,
            tickangle=0,
            tickcolor='#000'
        ),
        yaxis=dict(
            title=kwargs["y_axis_title"],
            range=[kwargs["min_y_axis_value"], 1],
            showgrid=True,
            showline=True,
            tickmode='linear',
            ticks='outside',
            tick0=0,
            dtick=kwargs["dtick"],
            ticklen=8,
            tickwidth=4,
            tickcolor='#000'
        ),
        barmode='group',
        autosize=False,
        width=1500,
        height=350
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
target_loops = [10, 20, 50, 100]
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
    scenario = full_text[full_text.index("test_")+6:full_text.index("test_")+7]  # .index(element) 'session_lyon2017_test_01_HYP_500_mda0.005_smss[500].txt'

    if hyp is None:
        cnf = str(int(float(get_config_value("_cnf", full_text))*100))
        ret = str(int(float(get_config_value("_ret", full_text))*100))
        bgr = str(int(float(get_config_value("_bgr", full_text))*100))

        return cnf + "·" + ret + "·" + bgr + " (" + scenario + ")"
    else:
        return "HYP (" + scenario + ")"

def get_value_at_loop(prop_name, loop_index, logs):

    target_loop = [log for log in logs if log["loop"] == loop_index]

    return target_loop[0]


# Looping each session to get the HYP results
hyp_results = []
for path in logs_folders:

    scenario_name = os.path.basename(os.path.normpath(path))

    # Get all the OUR files for the session
    # session_files = [f for f in os.scandir(path) if not f.is_dir() and "_OUR_" in f.name]
    session_files = [f for f in os.scandir(path) if not f.is_dir() ]

    for file in session_files:
        # Get the logs of the only file for HYP
        file_content = read_file(file.path)
        logs = [line for line in file_content if 'loop' in line]

        configs.append(get_config_name(file.name))

        for loop in target_loops:
            values_by_loop[loop_prefix + str(loop)].append(get_value_at_loop("accuracy", loop, logs))

    draw_barchart(title="Evolution of accuracy across loops and configurations", values_by_loop=values_by_loop,
                  x_axis_title="Configs (hw·dw·bw)", y_axis_title="Accuracy", round_values=True, show_labels=True,
                  full_path=os.path.join(output_path, scenario_name + '_OUR_accuracies' + '.png'), configs=configs,
                  target_loops=target_loops, prop_name="accuracy", dtick=0.01, min_y_axis_value=0.87) # 2015 = 0.70) # 2017 = 0.85)

    draw_barchart(title="Evolution of the precision across loops and configurations", values_by_loop=values_by_loop,
                  x_axis_title="Configs (hw·dw·bw)", y_axis_title="Precision", round_values=True, show_labels=True,
                  full_path=os.path.join(output_path, scenario_name + '_OUR_precision' + '.png'), configs=configs,
                  target_loops=target_loops, prop_name="precision", dtick=0.01, min_y_axis_value=0.98) # 0.96) # 2017 = 0.92)
