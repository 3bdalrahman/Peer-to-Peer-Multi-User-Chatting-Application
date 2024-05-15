import socket
import threading
import tkinter as tk
from tkinter import messagebox

# Dictionary to store references to open private chat windows
private_chat_windows = {}

# Dictionary to store offline messages
offline_messages = {}

# Set to store senders for whom notifications have been shown
notification_shown = set()

# Variable to store the current user's name
name = ""

# Client socket variable
client_socket = None

user_data = []

# Colors
background_color = "#ECE5DD"
input_field_color = "#FFFFFF"
button_color = "#25D366"
button_hover_color = "#128C7E"
text_color_self = "#075E54"
text_color_other = "#128C7E"

# Dictionary to store user credentials
user_credentials = {}

# Variable to store the current room
current_room = None


def receive_messages():
    global client_socket, name

    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            if message:
                print("Received message:", message)  # Debug print

                if message.startswith("[ACTIVE_USERS]"):
                    update_active_users(message[14:].split(','))
                elif message.startswith("[ROOM_LIST]"):
                    update_room_list(message[11:].split(','))
                elif message.startswith("[PRIVATE]"):
                    sender, private_message = message[9:].split(':', 1)
                    if sender in private_chat_windows:
                        print("Updating private chat window")  # Debug print
                        private_chat_window = private_chat_windows[sender]
                        private_chat_text_widget = private_chat_window.children['!text']
                        private_chat_text_widget.config(state=tk.NORMAL)
                        private_chat_text_widget.insert(tk.END, f"{sender}: {private_message}\n", 'other_message')
                        private_chat_text_widget.config(state=tk.DISABLED)
                        private_chat_text_widget.see(tk.END)
                    else:
                        print("Showing notification")  # Debug print
                        if sender not in notification_shown:
                            messagebox.showinfo("New Message", f"New message from {sender}")
                            notification_shown.add(sender)
                        if sender not in offline_messages:
                            offline_messages[sender] = []
                        offline_messages[sender].append((sender, private_message))
                else:
                    chat_text.config(state=tk.NORMAL)
                    if message.startswith(name):  # Check if the message starts with the current user's name
                        chat_text.insert(tk.END, f"{message}\n", 'self_message')
                    else:
                        chat_text.insert(tk.END, f"{message}\n", 'other_message')
                    chat_text.config(state=tk.DISABLED)
                    chat_text.see(tk.END)
        except Exception as e:
            print(f"Error receiving message: {e}")
            break


def send_message(message_entry):
    global client_socket, current_room
    message = message_entry.get()
    if message.lower() == 'exit':
        client_socket.close()
        return
    try:
        if current_room:
            client_socket.send(f"[ROOM]{current_room}:{message}".encode('utf-8'))
        else:
            client_socket.send(message.encode('utf-8'))
    except Exception as e:
        print(f"Error sending message: {e}")
    message_entry.delete(0, tk.END)


# Dictionary to store message history for each private chat session
private_chat_history = {}


# Dictionary to store message history for each private chat session
private_chat_history = {}


def open_private_chat(recipient, initial_message=None):
    global private_chat_windows, offline_messages, private_chat_history

    private_chat_window = tk.Toplevel()
    private_chat_window.title(f"Private Chat with {recipient}")

    private_chat_text = tk.Text(private_chat_window, state=tk.DISABLED, bg=input_field_color, width=50, height=20)
    private_chat_text.pack(expand=True, fill=tk.BOTH)

    message_frame = tk.Frame(private_chat_window, bg=background_color)
    message_frame.pack(fill=tk.X)

    private_message_entry = tk.Entry(message_frame, bg=input_field_color)
    private_message_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, pady=5)

    def send_private_message():
        message = private_message_entry.get()
        if message.lower() == 'exit':
            client_socket.close()
            return
        try:
            client_socket.send(f"[PRIVATE]{recipient}:{message}".encode('utf-8'))
            private_chat_text.config(state=tk.NORMAL)
            private_chat_text.insert(tk.END, f"{name}: {message}\n", 'self_message')
            private_chat_text.config(state=tk.DISABLED)
            private_chat_text.see(tk.END)
            private_message_entry.delete(0, tk.END)

            # Update message history
            if (name, recipient) in private_chat_history:
                private_chat_history[(name, recipient)].append((name, message))
            else:
                private_chat_history[(name, recipient)] = [(name, message)]

            # If the chat window is not open, display a notification
            if recipient not in private_chat_windows:
                messagebox.showinfo("New Message", f"You have a new message from {recipient}")
        except Exception as e:
            print(f"Error sending private message: {e}")

    send_private_button = tk.Button(message_frame, text="Send", command=send_private_message, bg=button_color,
                                    fg="white")
    send_private_button.pack(side=tk.RIGHT, padx=5, pady=5)

    private_chat_windows[recipient] = private_chat_window

    private_chat_text.tag_configure('self_message', foreground=text_color_self, justify='right',background="light green")
    private_chat_text.tag_configure('other_message', foreground=text_color_other, justify='left',background="light gray")

    # Concatenate offline messages with existing chat history
    message_history = offline_messages.get(recipient, []) + private_chat_history.get((name, recipient), [])

    # Display entire message history
    for sender, message in message_history:
        tag = 'self_message' if sender == name else 'other_message'
        private_chat_text.config(state=tk.NORMAL)
        if sender == name:
            private_chat_text.insert(tk.END, f"{sender}: {message}\n", 'self_message')
            private_chat_text.insert(tk.END, f"{recipient}: {message}\n", 'other_message')
        else:
            private_chat_text.insert(tk.END, f"{recipient}: {message}\n", 'other_message')
        private_chat_text.config(state=tk.DISABLED)
        private_chat_text.see(tk.END)

    # Clear offline messages for the recipient
    if recipient in offline_messages:
        del offline_messages[recipient]


def show_user_list_popup():
    user_list_popup = tk.Toplevel()
    user_list_popup.title("Active Users")

    active_user_list = tk.Listbox(user_list_popup, bg=input_field_color)
    active_user_list.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

    for user in user_data:
        active_user_list.insert(tk.END, user)

    active_user_list.bind('<Double-Button-1>',
                          lambda event: open_private_chat(user_data[active_user_list.curselection()[0]]))


def update_active_users(active_users):
    global user_data
    user_data = active_users


def update_room_list(rooms):
    room_listbox.delete(0, tk.END)
    for room in rooms:
        room_listbox.insert(tk.END, room)


def create_room():
    global client_socket, current_room
    room_name = room_name_entry.get()
    if room_name:
        try:
            client_socket.send(f"[CREATE_ROOM]{room_name}".encode('utf-8'))
            current_room = room_name
            room_name_entry.delete(0, tk.END)
        except Exception as e:
            print(f"Error creating room: {e}")


def join_room():
    global client_socket, current_room
    selected_room = room_listbox.get(tk.ACTIVE)
    if selected_room:
        try:
            client_socket.send(f"[JOIN_ROOM]{selected_room}".encode('utf-8'))
            current_room = selected_room
        except Exception as e:
            print(f"Error joining room: {e}")


def list_rooms():
    global client_socket
    try:
        client_socket.send("[LIST_ROOMS]".encode('utf-8'))
    except Exception as e:
        print(f"Error listing rooms: {e}")


def on_login():
    global name, client_socket

    name = login_name_entry.get()
    if not name:
        messagebox.showerror("Error", "Name cannot be empty")
        return

    password = login_password_entry.get()

    if not password:
        messagebox.showerror("Error", "Password cannot be empty")
        return

    if name not in user_credentials:
        messagebox.showerror("Error", "User does not exist. Please register.")
        return

    if user_credentials[name] != password:
        messagebox.showerror("Error", "Incorrect password")
        return

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('127.0.0.1', 5555))
    client_socket.send(name.encode('utf-8'))

    threading.Thread(target=receive_messages).start()

    login_frame.pack_forget()
    chat_frame.pack(expand=True, fill=tk.BOTH)


def on_register():
    name = signup_name_entry.get()
    password = signup_password_entry.get()

    if not name or not password:
        messagebox.showerror("Error", "Name and password cannot be empty")
        return

    if name in user_credentials:
        messagebox.showerror("Error", "Username already exists")
        return

    # Check if the password is already used by another user
    if password in user_credentials.values():
        messagebox.showerror("Error", "Password already in use. Please choose a different one.")
        return

    user_credentials[name] = password
    messagebox.showinfo("Success", "Registration successful")

    signup_frame.pack_forget()


root = tk.Tk()
root.title("Chat Application")

signup_frame = tk.Frame(root, bg=background_color)
signup_frame.pack(padx=10, pady=10)

signup_label = tk.Label(signup_frame, text="Sign Up", bg=background_color, font=("Helvetica", 16))
signup_label.grid(row=0, column=0, columnspan=2, pady=10)

signup_name_label = tk.Label(signup_frame, text="Name:", bg=background_color, font=("Helvetica", 12))
signup_name_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")

signup_name_entry = tk.Entry(signup_frame, bg=input_field_color, font=("Helvetica", 12))
signup_name_entry.grid(row=1, column=1, padx=10, pady=5)

signup_password_label = tk.Label(signup_frame, text="Password:", bg=background_color, font=("Helvetica", 12))
signup_password_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")

signup_password_entry = tk.Entry(signup_frame, bg=input_field_color, font=("Helvetica", 12), show="*")
signup_password_entry.grid(row=2, column=1, padx=10, pady=5)

signup_button = tk.Button(signup_frame, text="Sign Up", width=10, bg=button_color, fg="white", font=("Helvetica", 12),
                          activebackground=button_hover_color, activeforeground="white", command=on_register)
signup_button.grid(row=3, column=1, padx=10, pady=5)


login_frame = tk.Frame(root, bg=background_color)
login_frame.pack(padx=10, pady=10)

login_label = tk.Label(login_frame, text="Login", bg=background_color, font=("Helvetica", 16))
login_label.grid(row=0, column=0, columnspan=2, pady=10)

login_name_label = tk.Label(login_frame, text="Name:", bg=background_color, font=("Helvetica", 12))
login_name_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")

login_name_entry = tk.Entry(login_frame, bg=input_field_color, font=("Helvetica", 12))
login_name_entry.grid(row=1, column=1, padx=10, pady=5)

login_password_label = tk.Label(login_frame, text="Password:", bg=background_color, font=("Helvetica", 12))
login_password_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")

login_password_entry = tk.Entry(login_frame, bg=input_field_color, font=("Helvetica", 12), show="*")
login_password_entry.grid(row=2, column=1, padx=10, pady=5)

login_button = tk.Button(login_frame, text="Login", width=10, bg=button_color, fg="white", font=("Helvetica", 12),
                         activebackground=button_hover_color, activeforeground="white", command=on_login)
login_button.grid(row=3, column=1, padx=10, pady=5)

chat_frame = tk.Frame(root, bg=background_color)
chat_frame.pack_forget()

chat_text = tk.Text(chat_frame, state=tk.DISABLED, bg=input_field_color, width=50, height=20)
chat_text.pack(expand=True, fill=tk.BOTH)

chat_text.tag_configure('self_message', foreground=text_color_self, justify='right',background="light green")
chat_text.tag_configure('other_message', foreground=text_color_other, justify='left',background="light gray")

message_frame = tk.Frame(chat_frame, bg=background_color)
message_frame.pack(fill=tk.X)

message_entry = tk.Entry(message_frame, bg=input_field_color)
message_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, pady=5)

send_button = tk.Button(message_frame, text="Send", command=lambda: send_message(message_entry), bg=button_color,
                        fg="white")
send_button.pack(side=tk.RIGHT, padx=5, pady=5)

# Room management frame
room_frame = tk.Frame(chat_frame, bg=background_color)
room_frame.pack(fill=tk.X)

room_name_entry = tk.Entry(room_frame, bg=input_field_color)
room_name_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, pady=5)

create_room_button = tk.Button(room_frame, text="Create Room", command=create_room, bg=button_color, fg="white")
create_room_button.pack(side=tk.LEFT, padx=5, pady=5)

join_room_button = tk.Button(room_frame, text="Join Room", command=join_room, bg=button_color, fg="white")
join_room_button.pack(side=tk.LEFT, padx=5, pady=5)

list_rooms_button = tk.Button(room_frame, text="List Rooms", command=list_rooms, bg=button_color, fg="white")
list_rooms_button.pack(side=tk.LEFT, padx=5, pady=5)

room_listbox = tk.Listbox(room_frame, bg=input_field_color)
room_listbox.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=5, pady=5)

user_list_button = tk.Button(chat_frame, text="User List", command=show_user_list_popup, bg=button_color, fg="white")
user_list_button.pack(side=tk.RIGHT, padx=5, pady=5)

root.mainloop()
