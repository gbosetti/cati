import json
import ast
import plotly.plotly as py
import plotly.graph_objs as go
import plotly.io as pio
import os

def draw_scatterplot(title, x_axis_label, y_axis_label, x_axis, y_axis, filename):

    trace1 = go.Scatter(
        x=x_axis,
        y=y_axis,
        name='Accuracy'
    )

    data = [trace1]
    layout = go.Layout(
        title=go.layout.Title(
            text=title,
            xref='paper',
            x=0
        ),
        xaxis=go.layout.XAxis(
            title=go.layout.xaxis.Title(
                text=x_axis_label,
                font=dict(
                    size=18,
                    color='#7f7f7f'
                )
            )
        ),
        yaxis=go.layout.YAxis(
            title=go.layout.yaxis.Title(
                text=y_axis_label,
                font=dict(
                    size=18,
                    color='#7f7f7f'
                )
            )
        )
    )
    fig = go.Figure(data=data, layout=layout)

    if not os.path.exists('images'):
        os.mkdir('images')

    pio.write_image(fig, 'images/' + filename + '.png')

logs = json.loads(backend_logger.get_logs().replace('\n', ','))
loop_logs = [log for log in logs if 'loop' in log]

loops_values = [log["loop"] for log in logs if 'loop' in log]  # datetime
accuracies = [log["accuracy"] for log in logs if 'loop' in log]
diff_accuracies = [0 if log["diff_accuracy"]=='None' else float(log["diff_accuracy"]) for log in logs if 'loop' in log]
#diff_accuracies = [float(log["diff_accuracy"]) for log in logs if 'loop' in log if log["diff_accuracy"] != 'None']
wrong_answers = [log["wrong_pred_answers"] for log in logs if 'loop' in log]


draw_scatterplot("Evolution of accuracy across loops", "Loop", "Accuracy", loops_values, accuracies, "accuracy_[" + session + "-" + sampling_strategy + "]")
draw_scatterplot("Evolution of diff. accuracy across loops", "Loop", "Diff. accuracy", loops_values, diff_accuracies, "accuracy_diff_[" + session + "-" + sampling_strategy + "]")
draw_scatterplot("Evolution of wrongly predicted labels across loops", "Loop", "Wrong predictions (max. 20 by loop)", loops_values, wrong_answers, "wrong_predictions_[" + session + "-" + sampling_strategy + "]")


print("\n\n", loop_logs)