from tobas.TobasEventDetection import TobasEventDetection

tobas = TobasEventDetection()
topics = tobas.generate_searching_topics(index="geo_lyon_foot_2015", doc_field="clean-text", num_words=5)
print(topics)