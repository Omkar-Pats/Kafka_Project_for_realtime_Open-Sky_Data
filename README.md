# Kafka_Project_for_realtime_Open-Sky_Data

## 1. Workflow

![Workflow](https://github.com/Omkar-Pats/Kafka_Project_for_realtime_Open-Sky_Data/blob/main/assets/Workflow.png)

Used Go lang to create a Kafka producer which queries the Open Sky API and sends out data to the Kafka server, The Kafka server was hosted in a docker container, whenever a new packet is received, the JSON packet is unmarshaled and then sent sequentially to the Kafka Topic, (data is sent sequentially because the packet is too large and I don't wanna overwhelm the the API by continuosly calling since it has a request limit and I don't want to exhaust it) the reason the producer was created in Go was so that the producer could write to the Kafka server faster, later a seperate Kafka consumer was created in Python which pulls data from the Kafka server and aggregate metrics are saved to SQL server, live data is provided to the plotly dashboard which is updated as data is received.

Key Components:

Kafka Producer (Go): The main.go file contains the Go-based Kafka producer. It queries the OpenSky Network API to retrieve real-time aviation data, processes the JSON responses, and publishes the data to a Kafka topic.​

Kafka Consumer (Python): The call_consumer.py script serves as the Python-based Kafka consumer. It subscribes to the Kafka topic, consumes the incoming aviation data, and processes it for further analysis or visualization.​

Docker Compose Setup: The docker-compose.yml file orchestrates the setup of the Kafka broker and Zookeeper services, facilitating communication between the producer and consumer within a containerized environment.

## 2. Screenshots and format of the data received

![Kafka Server](https://github.com/Omkar-Pats/Kafka_Project_for_realtime_Open-Sky_Data/blob/main/assets/Kafka%20server.png)

The OpenSky API response provides real-time flight data, returning a timestamp and a list of aircraft states. Each state includes details such as the aircraft’s unique ICAO24 transponder address, call sign, origin country, position coordinates (latitude, longitude, and altitude), velocity, heading, vertical rate, and whether the aircraft is on the ground. The response allows tracking of live air traffic, with updates on the aircraft’s movement, last contact time, and transponder status. 

![Dashboard](https://github.com/Omkar-Pats/Kafka_Project_for_realtime_Open-Sky_Data/blob/main/assets/Screenshot.png)
(Each triangle is an aerial object)
