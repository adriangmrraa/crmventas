import socketio

# Initialize Socket.IO server
# cors_allowed_origins='*' is critical for development
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
