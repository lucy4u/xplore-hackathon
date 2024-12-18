import asyncio
import websockets
import json
import logging
import csv
import os
from datetime import datetime

# Import parsing functions from the first script
def parse_timestamp(timestamp_str):
    """
    Parse timestamp string to datetime object with flexible parsing
    """
    try:
        # Try multiple formats
        formats = [
            "%Y-%m-%d %H:%M:%S",  # Standard format
            "%Y-%m-%d %H:%M:%S.%f",  # With microseconds
            "%Y-%m-%d %H:%M"  # Without seconds
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        raise ValueError(f"Unable to parse timestamp: {timestamp_str}")
    except Exception as e:
        logging.error(f"Error parsing timestamp {timestamp_str}: {e}")
        return None

def load_monitoring_log(log_path):
    """
    Load monitoring log timestamps
    """
    monitoring_timestamps = []
    try:
        with open(log_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    timestamp = parse_timestamp(row['Timestamp'])
                    if timestamp:
                        monitoring_timestamps.append({
                            'timestamp': timestamp,
                        })
                except Exception as e:
                    logging.error(f"Error processing log entry: {e}")
    except FileNotFoundError:
        logging.error(f"Monitoring log not found at {log_path}")
    
    return monitoring_timestamps

def process_uploaded_file(file_path, monitoring_timestamps, bus_stops_path):
    """
    Process uploaded file and match timestamps with monitoring log
    """
    matched_bus_stops = []
    
    try:
        with open(file_path, 'r') as f:
            # Assuming the uploaded file has timestamp, latitude, longitude columns
            reader = csv.DictReader(f)
            
            # Prepare bus stops output file
            bus_stops_exists = os.path.exists(bus_stops_path)
            
            with open(bus_stops_path, 'a', newline='') as bus_stops_file:
                bus_stops_writer = csv.writer(bus_stops_file)
                
                # Write headers if file is new
                if not bus_stops_exists:
                    bus_stops_writer.writerow(['Latitude', 'Longitude'])
                
                for row in reader:
                    # Adjust column names as per your uploaded file's structure
                    try:
                        file_timestamp = parse_timestamp(row['Timestamp'])
                        
                        # Check if timestamp is in monitoring log (within a reasonable time window)
                        for log_timestamp in monitoring_timestamps:
                            time_diff = abs((file_timestamp - log_timestamp['timestamp']).total_seconds())
                            
                            # Allow 5-minute window for timestamp match
                            if time_diff <= 300:  # 5 minutes = 300 seconds
                                bus_stops_writer.writerow([
                                    row['Latitude'],  # Adjust column name as needed
                                    row['Longitude']  # Adjust column name as needed
                                ])
                                matched_bus_stops.append(row)
                                break
                    
                    except Exception as e:
                        logging.error(f"Error processing row: {e}")
        
        return matched_bus_stops
    
    except Exception as e:
        logging.error(f"Error processing uploaded file: {e}")
        return []

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global configurations
BASE_DIR = r'D:\xplor\xplore-hackathon\xplore-hackathon\PeopleCounting-ComputerVision-master'
MONITORING_LOG_PATH = os.path.join(BASE_DIR, 'logs', 'monitering_timestamp.csv')
BUS_STOPS_PATH = os.path.join(BASE_DIR, 'logs', 'bus_stops.csv')

# Global variable to store latest counts and monitoring state
latest_counts = {
    'day_count': 0,
    'existing_count': 0,
    'is_monitoring': False,
    'matched_bus_stops': 0
}

# Set to store connected clients
connected_clients = set()

async def broadcast_counts(message):
    """Broadcast counts to all connected clients"""
    logger.info(f"Attempting to broadcast: {message}")
    try:
        await asyncio.gather(*[
            client.send(message) for client in connected_clients
        ])
    except Exception as e:
        logger.error(f"Broadcast error: {e}")

async def handler(websocket, path=None):
    """Handle WebSocket connections"""
    try:
        # Add the client to the set of connected clients
        connected_clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(connected_clients)}")
        
        # Send initial counts and monitoring state immediately upon connection
        initial_message = json.dumps({**latest_counts})
        await websocket.send(initial_message)
        logger.info(f"Sent initial counts: {initial_message}")
        
        # Keep the connection open and listen for messages
        async for message in websocket:
            try:
                # Parse the incoming message
                data = json.loads(message)
                logger.info(f"Received message: {data}")
                
                # Handle bus stop file upload
                if data.get('type') == 'busStopUpload':
                    file_path = data.get('filePath')
                    if file_path:
                        # Load monitoring timestamps
                        monitoring_timestamps = load_monitoring_log(MONITORING_LOG_PATH)
                        
                        # Process bus stop file
                        matched_stops = process_uploaded_file(
                            file_path, 
                            monitoring_timestamps, 
                            BUS_STOPS_PATH
                        )
                        
                        # Update matched bus stops count
                        latest_counts['matched_bus_stops'] = len(matched_stops)
                        
                        # Prepare response
                        response = {
                            'status': 'success',
                            'message': f'Processed {len(matched_stops)} bus stop entries',
                            'matchedStops': len(matched_stops)
                        }
                        
                        await websocket.send(json.dumps(response))
                        
                        # Broadcast updated counts
                        await broadcast_counts(json.dumps(latest_counts))
                
                # Existing message handling remains the same
                elif data.get('type') == 'monitoringToggle':
                    latest_counts['is_monitoring'] = data.get('isMonitoring', latest_counts['is_monitoring'])
                
                # Update latest counts
                latest_counts['day_count'] = data.get('day_count', latest_counts['day_count'])
                latest_counts['existing_count'] = data.get('existing_count', latest_counts['existing_count'])
                
                # Broadcast updated counts to all clients
                broadcast_message = json.dumps(latest_counts)
                await broadcast_counts(broadcast_message)
            
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {message}")
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    except websockets.exceptions.ConnectionClosed:
        logger.info("Client disconnected")
    finally:
        # Remove the client from the set
        connected_clients.remove(websocket)
        logger.info(f"Client removed. Remaining clients: {len(connected_clients)}")

async def main():
    # Start WebSocket server
    server = await websockets.serve(
        handler,
        "localhost", 
        8765,
        ping_interval=10,
        ping_timeout=20
    )
    logger.info("WebSocket server started on ws://localhost:8765")
    
    # Keep server running
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())