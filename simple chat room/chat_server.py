import socket
import threading

# Maintain a list of connected clients and rooms
clients = []
rooms = {}
offline_private_messages = {}

def handle_client(client_socket):
    global clients, rooms
    try:
        name = client_socket.recv(1024).decode('utf-8')
        clients.append((client_socket, name))
        update_active_users()
        while True:
            message = client_socket.recv(1024).decode('utf-8')
            if message.lower() == 'exit':
                break
            if message.startswith("[PRIVATE]"):
                recipient, private_message = message[9:].split(':', 1)
                send_private_message(name, recipient, private_message)
            elif message.startswith("[CREATE_ROOM]"):
                room_name = message[13:].strip()
                create_room(room_name, client_socket, name)
            elif message.startswith("[JOIN_ROOM]"):
                room_name = message[11:].strip()
                join_room(room_name, client_socket, name)
            elif message.startswith("[LIST_ROOMS]"):
                list_rooms(client_socket)
            else:
                broadcast_message(name, message)
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_socket.close()
        clients = [(c_socket, c_name) for c_socket, c_name in clients if c_socket != client_socket]
        for room in rooms.values():
            room[:] = [(c_socket, c_name) for c_socket, c_name in room if c_socket != client_socket]
        update_active_users()

def update_active_users():
    active_users = [name for _, name in clients]
    active_users_msg = "[ACTIVE_USERS]" + ",".join(active_users)
    for client_socket, _ in clients:
        try:
            client_socket.send(active_users_msg.encode('utf-8'))
        except Exception as e:
            print(f"Error updating active users for client: {e}")

def broadcast_message(sender_name, message, recipient=None, room=None):
    if room:
        if room in rooms:
            target_clients = rooms[room]
        else:
            return
    else:
        target_clients = clients

    for client_socket, client_name in target_clients:
        if recipient is None:  # If no recipient specified, broadcast to all
            try:
                formatted_message = f"{sender_name}: {message}"
                client_socket.send(formatted_message.encode('utf-8'))
            except Exception as e:
                print(f"Error broadcasting message to {client_name}: {e}")
        elif client_name == recipient:  # If recipient matches, send the message
            try:
                formatted_message = f"{sender_name}: {message}"
                client_socket.send(formatted_message.encode('utf-8'))
            except Exception as e:
                print(f"Error sending private message to {recipient}: {e}")

def send_private_message(sender_name, recipient, message):
    global offline_private_messages
    recipient_found = False
    for client_socket, client_name in clients:
        if client_name == recipient:
            recipient_found = True
            try:
                formatted_message = f"[PRIVATE]{sender_name}: {message}"
                client_socket.send(formatted_message.encode('utf-8'))
            except Exception as e:
                print(f"Error sending private message to {recipient}: {e}")
    if not recipient_found:
        if recipient not in offline_private_messages:
            offline_private_messages[recipient] = []
        offline_private_messages[recipient].append((sender_name, message))

def create_room(room_name, client_socket, name):
    if room_name not in rooms:
        rooms[room_name] = [(client_socket, name)]
        client_socket.send(f"Room {room_name} created and joined.".encode('utf-8'))
    else:
        client_socket.send(f"Room {room_name} already exists.".encode('utf-8'))

def join_room(room_name, client_socket, name):
    if room_name in rooms:
        rooms[room_name].append((client_socket, name))
        client_socket.send(f"Joined room {room_name}.".encode('utf-8'))
    else:
        client_socket.send(f"Room {room_name} does not exist.".encode('utf-8'))

def list_rooms(client_socket):
    room_list = list(rooms.keys())
    room_list_msg = "[ROOM_LIST]" + ",".join(room_list)
    try:
        client_socket.send(room_list_msg.encode('utf-8'))
    except Exception as e:
        print(f"Error sending room list to client: {e}")

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('127.0.0.1', 5555))
    server_socket.listen(5)
    print("Server is listening for connections...")
    while True:
        client_socket, _ = server_socket.accept()
        client_thread = threading.Thread(target=handle_client, args=(client_socket,))
        client_thread.start()

if __name__ == "__main__":
    start_server()
