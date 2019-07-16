import csv
import pandas as pd

input_path="D:/IDENUM/data-to-import/passau/enriched_filtered_data_plus.csv"  # enriched_filtered_data_plus
output_path="D:/IDENUM/data-to-import/passau/output.csv"

data = pd.read_csv(input_path, engine = 'python', comment='"', sep=',').dropna(subset = ['text'])

chars_to_remove='"\'\n'
target_props=["user_name", "text_translated_en", "latitude", "longitude", "date"]

input_data=open(input_path, encoding="utf8")
reader=csv.DictReader(input_data)
csv_columns = reader.fieldnames

with open(output_path, 'w', encoding="utf8", newline='') as output_data:

    writer = csv.DictWriter(output_data, fieldnames=csv_columns, quoting=csv.QUOTE_ALL)  #, quotechar='"', delimiter=',', escapechar='\\')
    writer.writeheader()

    for line in reader:

        try:
            for prop in line:
                # if prop == "text" and line["id"] == "11":
                #      print("check")

                if prop in target_props:
                    line[prop] = ''.join(c for c in str(line[prop]) if c not in chars_to_remove)
                    #line[prop] = line[prop].replace("\n", " ")
                    #line[prop] = line[prop].replace("\\", "")
                    #line[prop] = line[prop].replace('"', '\'')
                    #line[prop] = line[prop].replace("\\", "")
                    # line[prop] = line[prop].replace("'", "\\'")
                else:
                    line[prop]=""

            writer.writerow(line)

        except Exception as err:
            print("Error: ", err)

    input_data.close()