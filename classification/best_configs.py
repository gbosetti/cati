import json
import ast
import plotly.plotly as py
import plotly.graph_objs as go
import plotly.io as pio
import os
import re
import statistics
import operator

#PARAMS
logs_path = "/home/gabi/Bureau/test/"


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

def process_results(logs):
    loop_logs = [log for log in logs if 'loop' in log]

    loops_values = [log["loop"] for log in logs if 'loop' in log]  # datetime
    accuracies = [log["accuracy"] for log in logs if 'loop' in log]
    # diff_accuracies = [float(log["diff_accuracy"]) for log in logs if 'loop' in log if log["diff_accuracy"] != 'None']
    wrong_answers = [log["wrong_pred_answers"] for log in logs if 'loop' in log]

    return loops_values, accuracies, wrong_answers



# Initialization
logs_folders = [f.path for f in os.scandir(logs_path) if f.is_dir() ]
configs = []
loop_prefix = "loop "


def get_config_value(prop_name, full_text):
    start_index = full_text.index(prop_name) + 4
    end_index = start_index + 3

    return full_text[start_index:end_index]

def get_config_name(full_text):

    hyp = re.search(r'HYP', full_text, re.M | re.I)
    if hyp is None:
        cnf = str(int(float(get_config_value("_cnf", full_text))*100))
        ret = str(int(float(get_config_value("_ret", full_text))*100))
        bgr = str(int(float(get_config_value("_bgr", full_text))*100))

        return cnf + "·" + ret + "·" + bgr
    else:
        return "HYP"

def get_value_at_loop(prop_name, loop_index, logs):

    target_loop = [log for log in logs if log["loop"] == loop_index]

    return target_loop[0]

def get_config_name(full_text):

    hyp = re.search(r'HYP', full_text, re.M | re.I)
    if hyp is None:
        cnf = str(int(float(get_config_value("_cnf", full_text))*100))
        ret = str(int(float(get_config_value("_ret", full_text))*100))
        bgr = str(int(float(get_config_value("_bgr", full_text))*100))
        return str(cnf + "·" + ret + "·" + bgr)
    else:
        return "HYP"


# Looping each session to get the HYP results
full_scenario_results = []
top_accuracy_scenario_results = []
top_precision_scenario_results = []

meta_measurements = []

for scenario_path in logs_folders:

    scenario_name = os.path.basename(os.path.normpath(scenario_path))

    # Get all the OUR files for the session
    # session_files = [f for f in os.scandir(path) if not f.is_dir() and "_OUR_" in f.name]
    session_files = [f for f in os.scandir(scenario_path) if not f.is_dir() ]

    # GET THE AVERAGES AND STDEVS (MEASUREMENTS) FOR EACH CONFIGURATION

    measurements = []
    for config_file in session_files:

        # For each configuration
        # Get the logs of the only file for HYP
        config = read_file(config_file.path)
        config_name = get_config_name(config_file.name)
        print("CONFIG: ", config_name)
        loops = [line for line in config if 'loop' in line]

        accuracies = [log["accuracy"] for log in loops]
        accuracy_average = statistics.mean(accuracies)
        accuracy_stdev = statistics.stdev(accuracies)

        precisions = [log["precision"] for log in loops]
        precision_average = statistics.mean(precisions)
        precision_stdev = statistics.stdev(precisions)

        clicks = [log["wrong_pred_answers"] for log in loops]
        clicks_average = statistics.mean(clicks)
        clicks_stdev = statistics.stdev(clicks)

        measurements.append({
            "name": config_name,
            "accuracy_average": accuracy_average,
            "accuracy_stdev": accuracy_stdev,
            "precision_average": precision_average,
            "precision_stdev": precision_stdev,
            "clicks_average": clicks_average,
            "clicks_stdev": clicks_stdev
        })

    # SORT THE CONFIGS BY HIGER AVERAGE AND LOWER STDEV
    measurements.sort(key=lambda i: (i['accuracy_average'], -i['accuracy_stdev']), reverse=True)
    top_accuracy = measurements[0]
    top_accuracy_configs = [config["name"] for config in measurements if config["accuracy_average"] == top_accuracy["accuracy_average"] and config["accuracy_stdev"] == top_accuracy["accuracy_stdev"]]

    measurements.sort(key=lambda i: (i['precision_average'], -i['precision_stdev']), reverse=True)
    top_precision = measurements[0]
    top_precision_configs = [config["name"] for config in measurements if config["precision_average"] == top_precision["precision_average"] and config["precision_stdev"] == top_precision["precision_stdev"]]

    measurements.sort(key=lambda i: (i['precision_average']+i['accuracy_average'], -(i['precision_stdev']+i['accuracy_stdev'])), reverse=True)
    top_both = measurements[0]
    top_both_configs = [config["name"] for config in measurements
                             if config["precision_average"]+config["accuracy_average"] == top_both["precision_average"]+top_both["accuracy_average"]
                             and config["precision_stdev"]+config[ "accuracy_stdev"] == top_both["precision_stdev"]+top_both["accuracy_stdev"]]

    measurements.sort(key=lambda i: (-i['clicks_average'], -i['clicks_stdev']), reverse=True)
    top_clicks = measurements[0]
    top_clicks_configs = [config["name"] for config in measurements if
                             config["clicks_average"] == top_clicks["clicks_average"] and config[
                                 "clicks_stdev"] == top_clicks["clicks_stdev"]]

    #full_ranking_top_click = [config["name"] for config in measurements]
    meta_measurements.append(measurements)

    print("MEASUREMENTS (", scenario_name, ")")
    print(json.dumps(measurements, indent=4, sort_keys=True, ensure_ascii=False))
    # ("TOP BOTH FULL RANKING", measurements[0])
    full_scenario_results.append({
        "scenario": scenario_name,
        # "measurements": measurements,
        "top_accuracy": {
            "value": top_accuracy,
            "matching_configs": top_accuracy_configs
        },
        "top_precision": {
            "value": top_precision,
            "matching_configs": top_precision_configs
        },
        "top_accuracy_and_precision":{
            "value": top_both,
            "matching_configs": top_both_configs
        },
        "top_clicks": {
            "value": top_clicks,
            "matching_configs": top_clicks_configs
        }
    })





# PRINT THE BEST CONFIGURATIONS
print("BEST CONFIGS:", json.dumps(full_scenario_results, indent=4, sort_keys=True, ensure_ascii=False))

# PRINT THE MOST COMMON IN THE 4 SCENARIOS
full_configs_names_accuracy = [x for sub_list in [scenario["top_accuracy"]["matching_configs"] for scenario in full_scenario_results] for x in sub_list]
unique_configs_names_accuracy = list(set(full_configs_names_accuracy))
sorted_configs_accuracy = []
for config in unique_configs_names_accuracy:
    sorted_configs_accuracy.append({ "count": full_configs_names_accuracy.count(config), "name": config })

sorted_configs_accuracy.sort(key=lambda i: (i['count']), reverse=True)
#print("SORTED TOP CONFIGS FOR ACCURACY:", json.dumps(sorted_configs_accuracy, indent=4, sort_keys=True, ensure_ascii=False))


full_configs_names_precision = [x for sub_list in [scenario["top_precision"]["matching_configs"] for scenario in full_scenario_results] for x in sub_list]
unique_configs_names_precision = list(set(full_configs_names_precision))
sorted_configs_precision = []
for config in unique_configs_names_precision:
    sorted_configs_precision.append({ "count": full_configs_names_precision.count(config), "name": config })

sorted_configs_precision.sort(key=lambda i: (i['count']), reverse=True)
#print("SORTED TOP CONFIGS FOR PRECISION:", json.dumps(sorted_configs_precision, indent=4, sort_keys=True, ensure_ascii=False))



print("META")
meta_measurements
all_configs = [config["name"] for config in meta_measurements[0]]
accum_meta_configs =[]

for config in all_configs:
    avg=0
    stdev = 0
    for meta_config in meta_measurements:
        config_avg = [c["clicks_average"] for c in meta_config if c["name"] == config]
        avg+=config_avg[0]
        config_stdev = [c["clicks_stdev"] for c in meta_config if c["name"] == config]
        stdev += config_stdev[0]

    accum_meta_configs.append({"name": config, "avg": avg, "stdev": stdev})

accum_meta_configs.sort(key=lambda i: (-i['avg'], -i['stdev']), reverse=True)

print("META")
print(json.dumps(accum_meta_configs, indent=4, sort_keys=True, ensure_ascii=False))