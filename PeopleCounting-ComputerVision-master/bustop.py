import csv
from datetime import datetime
import os

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
        print(f"Error parsing timestamp {timestamp_str}: {e}")
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
                    print(f"Error processing log entry: {e}")
    except FileNotFoundError:
        print(f"Monitoring log not found at {log_path}")
    
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
                        print(f"Error processing row: {e}")
        
        return matched_bus_stops
    
    except Exception as e:
        print(f"Error processing uploaded file: {e}")
        return []

def main():
    # Paths - adjust these to match your directory structure
    base_dir = r'D:\xplor\xplore-hackathon\xplore-hackathon\PeopleCounting-ComputerVision-master'
    
    monitoring_log_path = os.path.join(base_dir, 'logs', 'monitering_timestamp.csv')
    bus_stops_path = os.path.join(base_dir, 'logs', 'bus_stops.csv')
    
    # Uploaded file path - you might want to modify this to accept file dynamically
    uploaded_file_path = os.path.join(base_dir, 'web', 'uploaded_file.csv')
    
    # Load monitoring timestamps
    monitoring_timestamps = load_monitoring_log(monitoring_log_path)
    
    # Process uploaded file and match with monitoring log
    matched_stops = process_uploaded_file(
        uploaded_file_path, 
        monitoring_timestamps, 
        bus_stops_path
    )
    
    print(f"Processed {len(matched_stops)} bus stop entries")

if __name__ == "__main__":
    main()