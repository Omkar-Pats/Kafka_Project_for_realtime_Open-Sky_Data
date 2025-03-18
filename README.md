# Kafka_Project_for_realtime_Open-Sky_Data

## 1. Workflow

![Workflow](https://github.com/Omkar-Pats/Kafka_Project_for_realtime_Open-Sky_Data/blob/main/assets/Workflow.png)

Use Go lang to create a Kafka producer which queries the Open Sky API and sends out data to the Kafka server whenever a new packet is received, the JSON packet is unmarshaled and then sent sequentially to the Kafka Topic, (data is sent sequentially because the packet is too large and I don't wanna over whelm the process, another reason is the API has a request limit, so we don't want to exhaust it) the reason the producer was created in Go was so that the producer could write to the Kafka server faster, later a seperate Kafka consumer was created in Python which pulls data from the Kafka server and this is provided to the plotly dashboard which is updated as data is received which makes it (almost!) real-time.


