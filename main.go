package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/segmentio/kafka-go"
)

type Response struct {
	Time   int     `json:"time"`
	States [][]any `json:"states"`
}

type FlightData struct {
	Icao24       string   `json:"icao24"`
	Callsign     *string  `json:"callsign"`
	Time         int      `json:"time"`
	Orig_Country *string  `json:"orig_country"`
	Lat          *float64 `json:"latitude"`
	Lon          *float64 `json:"longitude"`
	Alt          *string  `json:"altitude"`
}

const Kafkaserver string = "localhost:9092"
const KafkaTopic string = "Experiment"

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	w := &kafka.Writer{
		Addr:     kafka.TCP(Kafkaserver),
		Topic:    KafkaTopic,
		Balancer: &kafka.LeastBytes{},
	}
	defer w.Close()

	ticker := time.NewTicker(1 * time.Minute)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			fetchAndSendData(ctx, w)
		case <-ctx.Done():
			return
		}
	}
}

func fetchAndSendData(ctx context.Context, w *kafka.Writer) {
	url := "https://opensky-network.org/api/states/all?lamin=45.8389&lomin=5.9962&lamax=47.8229&lomax=10.5226"
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		log.Printf("Error creating request: %v", err)
		return
	}

	response, err := http.DefaultClient.Do(req)
	if err != nil {
		log.Printf("Error fetching data: %v", err)
		return
	}
	defer response.Body.Close()

	var resp Response
	if err := json.NewDecoder(response.Body).Decode(&resp); err != nil {
		log.Printf("Error decoding response: %v", err)
		return
	}

	for _, state := range resp.States {
		Icao24 := state[0]
		Callsign := state[1]
		Country := state[2]
		UTC_time := time.Unix(int64(state[3].(float64)), 0)
		longitude := state[5]
		latitude := state[6]
		Baro_Altitude := state[7]

		// Create FlightData object from the fetched data
		flightData := FlightData{
			Icao24: Icao24.(string),
			Time:   int(UTC_time.Unix()),
		}

		// Safely handle Callsign which might be nil
		if Callsign != nil {
			if CallsignStr, ok := Callsign.(string); ok {
				flightData.Callsign = &CallsignStr
			}
		}

		// Safely handle Country which might be nil
		if Country != nil {
			if countryStr, ok := Country.(string); ok {
				flightData.Orig_Country = &countryStr
			}
		}

		// Safely handle latitude which might be nil
		if latitude != nil {
			if lat, ok := latitude.(float64); ok {
				flightData.Lat = &lat
			}
		}

		// Safely handle longitude which might be nil
		if longitude != nil {
			if lon, ok := longitude.(float64); ok {
				flightData.Lon = &lon
			}
		}

		// Safely handle Baro_Altitude which might be nil
		if Baro_Altitude != nil {
			if alt, ok := Baro_Altitude.(string); ok {
				flightData.Alt = &alt
			} else if altFloat, ok := Baro_Altitude.(float64); ok {
				// Handle case where altitude might be a float
				altStr := fmt.Sprintf("%f", altFloat)
				flightData.Alt = &altStr
			}
		}

		send_to_broker, _ := json.Marshal(flightData)

		msg := kafka.Message{
			Key:   []byte(flightData.Icao24),
			Value: []byte(send_to_broker),
		}

		err := w.WriteMessages(ctx, msg)
		if err != nil {
			log.Printf("Failed to write message: %v\n", err)
			continue
		}

		log.Printf("Delivered message to topic %s\n", KafkaTopic)
	}
}
