import json
import ast
import plotly.plotly as py
import plotly.graph_objs as go
import plotly.io as pio
import os
import re
import numpy as np
import matplotlib.pyplot as plt

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

        text = y_values
        if kwargs["round_values"]:
            text = ["<b>"+str(round(val,4))+"<b>" for val in text]

        if kwargs["show_labels"]:

            trace = go.Bar(
                x= x_values, #kwargs["configs"],  # ['giraffes', 'orangutans', 'monkeys']
                y=y_values, #res,  # [0.9, 0.3, 0.7],
                text = text,
                textfont= dict(family='Arial'),
                textposition='auto',
                name="at " + loop_index  # at loop 10
            )
        else:
            trace = go.Bar(
                x= x_values, #kwargs["configs"],  # ['giraffes', 'orangutans', 'monkeys']
                y=y_values, #res,  # [0.9, 0.3, 0.7],
                textposition='auto',
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
        height=800
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

    return json.loads(textual_logs)

def get_formatted_logs(json_content):
    logs = [line for line in json_content if 'loop' in line]

    return {
        "loops": [line["loop"] for line in logs],
        "accuracies": [line["accuracy"] for line in logs]
    }

def get_graph_title_from_logs(json_content):

    field = [line["field"] for line in json_content if 'field' in line][0]
    vectorizer = [line["vectorizer"] for line in json_content if 'vectorizer' in line][0]
    learner = [line["learner"] for line in json_content if 'learner' in line][0]
    sampler = [line["sampler"] for line in json_content if 'sampler' in line][0]

    return field + " - " + vectorizer + " - " + learner + " - " + sampler

def generate_graphs(input_folder, output_filename, target_field):

    log_files = [f.path for f in os.scandir(input_folder) if
                 "best_config_" in f.path] # Reading all the files
    fig, axs = plt.subplots(nrows=len(log_files))

    for index, path in enumerate(log_files):
        json_content = read_file(path)
        logs = get_formatted_logs(json_content)

        axs[index].plot(logs["loops"], logs["accuracies"])
        axs[index].set_title(get_graph_title_from_logs(json_content))
        axs[index].set(xlabel=target_field, ylabel='loops')
        axs[index].xaxis.set_ticks(logs["loops"])
        # start, end = axs[index].get_xlim()
        # axs[index].xaxis.set_ticks(np.arange(start, end, 1))

    plt.subplots_adjust(hspace=0.75)
    fig.savefig(output_filename, dpi=None, orientation='portrait', transparent=False, pad_inches=0.1,
                frameon=None, metadata=None)

# -------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------

input_folder = os.path.join(os.getcwd(), "classification", "logs")
generate_graphs(input_folder, output_filename="demo.png", target_field="accuracy")
