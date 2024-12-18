import asyncio
import websockets
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variable to store latest counts
latest_counts = {
    'day_count': 0,
    'existing_count': 0
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
        
        # Send initial counts immediately upon connection
        initial_message = json.dumps(latest_counts)
        await websocket.send(initial_message)
        logger.info(f"Sent initial counts: {initial_message}")
        
        # Keep the connection open and listen for messages
        async for message in websocket:
            try:
                # Parse the incoming message
                data = json.loads(message)
                logger.info(f"Received message: {data}")
                
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
        handler,  # Note: removed the 'path' requirement 
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