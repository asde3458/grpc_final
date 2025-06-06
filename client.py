import grpc
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import chat_pb2
import chat_pb2_grpc
import threading
import queue
import time
from datetime import datetime
from ttkthemes import ThemedTk

class ChatClient:
    def __init__(self):
        self.window = ThemedTk(theme="arc")  # Modern theme
        self.window.title("Modern Chat Application")
        self.window.geometry("1200x700")
        self.window.configure(bg="#f5f6f7")
        
        # Configure custom colors
        self.colors = {
            'primary': '#2196f3',      # Blue
            'secondary': '#e3f2fd',    # Light Blue
            'accent': '#1976d2',       # Dark Blue
            'background': '#f5f6f7',   # Light Gray
            'text': '#263238',         # Dark Gray
            'success': '#4caf50',      # Green
            'error': '#f44336'         # Red
        }
        
        # Configure style
        self.style = ttk.Style()
        self.style.configure("TFrame", background=self.colors['background'])
        self.style.configure("TLabelframe", background=self.colors['background'])
        self.style.configure("TLabelframe.Label", 
                           font=("Segoe UI", 12, "bold"), 
                           background=self.colors['background'],
                           foreground=self.colors['text'])
        
        # Custom button styles
        self.style.configure("Primary.TButton",
                           font=("Segoe UI", 10),
                           padding=8,
                           background=self.colors['primary'])
        
        self.style.configure("Secondary.TButton",
                           font=("Segoe UI", 10),
                           padding=8,
                           background=self.colors['secondary'])
        
        self.style.configure("TLabel",
                           font=("Segoe UI", 10),
                           background=self.colors['background'],
                           foreground=self.colors['text'])
        
        self.style.configure("Header.TLabel",
                           font=("Segoe UI", 14, "bold"),
                           background=self.colors['background'],
                           foreground=self.colors['primary'])
        
        # Create main frame with padding and rounded corners
        self.main_frame = ttk.Frame(self.window, padding="30", style="TFrame")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        
        # Login frame with enhanced styling
        self.login_frame = ttk.LabelFrame(self.main_frame, text="Welcome Back", padding="30", style="TLabelframe")
        self.login_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=20)
        
        # Center the login frame
        self.main_frame.columnconfigure(0, weight=1)
        
        # Username field with icon
        ttk.Label(self.login_frame, text="Username", style="TLabel").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.username_var = tk.StringVar()
        username_entry = ttk.Entry(self.login_frame,
                                 textvariable=self.username_var,
                                 width=30,
                                 font=("Segoe UI", 11))
        username_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15), padx=5)
        
        # Password field with icon
        ttk.Label(self.login_frame, text="Password", style="TLabel").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(self.login_frame,
                                 textvariable=self.password_var,
                                 show="•",
                                 width=30,
                                 font=("Segoe UI", 11))
        password_entry.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 20), padx=5)
        
        # Login and Register buttons frame
        button_frame = ttk.Frame(self.login_frame, style="TFrame")
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        login_button = ttk.Button(button_frame,
                                text="Login",
                                command=self.login,
                                style="Primary.TButton",
                                width=15)
        login_button.grid(row=0, column=0, padx=5)
        
        register_button = ttk.Button(button_frame,
                                   text="Register",
                                   command=self.show_register_dialog,
                                   style="Secondary.TButton",
                                   width=15)
        register_button.grid(row=0, column=1, padx=5)
        
        # Chat frame (initially hidden)
        self.chat_frame = ttk.Frame(self.main_frame, style="TFrame")
        
        # Left panel for groups with enhanced styling
        self.left_panel = ttk.Frame(self.chat_frame, style="TFrame", width=300)
        self.left_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 20))
        self.left_panel.grid_propagate(False)
        
        # Group list frame with modern styling
        self.group_list_frame = ttk.LabelFrame(self.left_panel,
                                             text="My Groups",
                                             padding="15",
                                             style="TLabelframe")
        self.group_list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Modern group list
        self.group_list = tk.Listbox(self.group_list_frame,
                                   height=18,
                                   width=35,
                                   font=("Segoe UI", 11),
                                   selectmode=tk.SINGLE,
                                   activestyle='none',
                                   bg=self.colors['secondary'],
                                   fg=self.colors['text'],
                                   selectbackground=self.colors['primary'],
                                   selectforeground='white',
                                   bd=0,
                                   highlightthickness=0)
        self.group_list.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.group_list.bind('<<ListboxSelect>>', self.on_group_select)
        
        # Modern scrollbar
        group_scrollbar = ttk.Scrollbar(self.group_list_frame,
                                      orient="vertical",
                                      command=self.group_list.yview)
        group_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.group_list.configure(yscrollcommand=group_scrollbar.set)
        
        # Group management buttons with modern styling
        self.group_buttons_frame = ttk.Frame(self.left_panel, style="TFrame")
        self.group_buttons_frame.grid(row=1, column=0, pady=10, sticky=(tk.W, tk.E))

        self.create_group_btn = ttk.Button(self.group_buttons_frame,
                                         text="Create Group",
                                         command=self.create_group,
                                         style="Primary.TButton")
        self.create_group_btn.grid(row=0, column=0, padx=2)

        self.join_group_btn = ttk.Button(self.group_buttons_frame,
                                       text="Join Group",
                                       command=self.join_group,
                                       style="Secondary.TButton")
        self.join_group_btn.grid(row=0, column=1, padx=2)

        # Right panel for chat with modern styling
        self.right_panel = ttk.Frame(self.chat_frame, style="TFrame")
        self.right_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Enhanced user info frame
        self.user_frame = ttk.Frame(self.right_panel, style="TFrame")
        self.user_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        
        self.user_label = ttk.Label(self.user_frame,
                                  text="Not logged in",
                                  style="Header.TLabel")
        self.user_label.grid(row=0, column=0, sticky=tk.W)
        
        self.current_group_label = ttk.Label(self.user_frame,
                                           text="",
                                           font=("Segoe UI", 12),
                                           style="TLabel")
        self.current_group_label.grid(row=0, column=1, sticky=tk.W, padx=(20, 0))

        # Modern group action buttons
        self.invite_user_btn = ttk.Button(self.user_frame,
                                        text="Invite User",
                                        command=self.invite_user,
                                        style="Secondary.TButton")
        self.invite_user_btn.grid(row=0, column=2, padx=5)
        
        self.leave_group_btn = ttk.Button(self.user_frame,
                                        text="Leave Group",
                                        command=self.leave_group,
                                        style="Secondary.TButton")
        self.leave_group_btn.grid(row=0, column=3, padx=5)

        # Enhanced message display
        self.message_display = scrolledtext.ScrolledText(
            self.right_panel,
            wrap=tk.WORD,
            width=70,
            height=20,
            font=("Segoe UI", 11),
            bg='white',
            fg=self.colors['text'],
            padx=10,
            pady=10,
            bd=0,
            highlightthickness=1,
            highlightcolor=self.colors['primary'],
            highlightbackground=self.colors['secondary']
        )
        self.message_display.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        self.message_display.config(state=tk.DISABLED)
        
        # Modern message input frame
        input_frame = ttk.Frame(self.right_panel, style="TFrame")
        input_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=10)
        
        self.message_var = tk.StringVar()
        self.message_entry = ttk.Entry(
            input_frame,
            textvariable=self.message_var,
            width=50,
            font=("Segoe UI", 11)
        )
        self.message_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        send_button = ttk.Button(
            input_frame,
            text="Send",
            command=self.send_message,
            style="Primary.TButton"
        )
        send_button.grid(row=0, column=1, sticky=tk.E)
        
        # Configure grid weights
        self.chat_frame.columnconfigure(1, weight=1)
        self.chat_frame.rowconfigure(0, weight=1)
        self.right_panel.columnconfigure(0, weight=1)
        self.right_panel.rowconfigure(1, weight=1)
        input_frame.columnconfigure(0, weight=1)
        
        # Initialize gRPC
        self.channel = grpc.insecure_channel('localhost:50051')
        self.stub = chat_pb2_grpc.ChatServiceStub(self.channel)
        
        # Message queue for receiving messages
        self.message_queue = queue.Queue()
        
        # Start message receiver thread
        self.receiver_thread = None
        self.is_running = False
        
        # Store current group info
        self.current_group = None
        self.user_groups = {}  # group_id -> group_name
        
        # Bind Enter key to send message
        self.message_entry.bind('<Return>', lambda e: self.send_message())

        # Modern sign out button
        self.signout_frame = ttk.Frame(self.window, style="TFrame")
        self.signout_frame.grid(row=1, column=0, sticky=(tk.SE, tk.E), padx=30, pady=20)
        sign_out_button = ttk.Button(
            self.signout_frame,
            text="Sign Out",
            command=self.sign_out,
            style="Secondary.TButton"
        )
        sign_out_button.grid(row=0, column=0, sticky=tk.E)

    def login(self):
        username = self.username_var.get()
        password = self.password_var.get()
        
        try:
            response = self.stub.Login(chat_pb2.LoginRequest(username=username, password=password))
            if response.success:
                messagebox.showinfo("Success", "Login successful!")
                self.login_frame.grid_remove()
                self.chat_frame.grid()
                self.user_label.config(text=f"Logged in as: {username}")
                self.start_chat(username)
                self.load_user_groups()
            else:
                messagebox.showerror("Error", response.message)
        except Exception as e:
            messagebox.showerror("Error", f"Login failed: {str(e)}")

    def start_chat(self, username):
        self.is_running = True
        self.receiver_thread = threading.Thread(target=self.receive_messages, args=(username,))
        self.receiver_thread.daemon = True
        self.receiver_thread.start()
        
        # Send initial connection message
        initial_message = chat_pb2.ChatMessage(
            sender=username,
            content="",
            type=chat_pb2.HEARTBEAT
        )
        self.message_queue.put(initial_message)

    def receive_messages(self, username):
        try:
            print(f"Starting message receiver for {username}")
            for message in self.stub.Chat(self.generate_messages(username)):
                print(f"Received message: {message.content} from {message.sender}")
                # Luôn xử lý System message
                if message.sender == "System":
                    self.window.after_idle(self.display_message, message)
                elif message.content:
                    # Chỉ hiển thị message group nếu đúng group đang chọn
                    if message.type == chat_pb2.GROUP and str(message.group_id) == str(self.current_group):
                        self.window.after_idle(self.display_message, message)
                        print(f"Displaying message in chat window: {message.content}")
        except Exception as e:
            print(f"Error receiving messages: {e}")
            self.is_running = False

    def generate_messages(self, username):
        while self.is_running:
            try:
                # Try to get a message from the queue
                try:
                    message = self.message_queue.get(block=False)
                    if message:
                        print(f"Generating message: {message.content}")
                        yield message
                except queue.Empty:
                    # Send a heartbeat message to keep the stream alive
                    heartbeat = chat_pb2.ChatMessage(
                        sender=username,
                        content="",
                        type=chat_pb2.HEARTBEAT
                    )
                    yield heartbeat
                    
                # Add a small delay to prevent CPU overuse
                time.sleep(0.1)
            except Exception as e:
                print(f"Error in generate_messages: {e}")
                time.sleep(0.1)

    def load_user_groups(self):
        try:
            response = self.stub.GetUserGroups(chat_pb2.GetUserGroupsRequest(
                username=self.username_var.get()
            ))
            if response.success:
                self.group_list.delete(0, tk.END)
                self.user_groups.clear()
                for group in response.groups:
                    self.user_groups[group.group_id] = group.group_name
                    self.group_list.insert(tk.END, group.group_name)
        except Exception as e:
            print(f"Error loading groups: {e}")

    def on_group_select(self, event):
        selection = self.group_list.curselection()
        if selection:
            group_name = self.group_list.get(selection[0])
            group_id = next((gid for gid, name in self.user_groups.items() if name == group_name), None)
            if group_id:
                self.current_group = group_id
                self.current_group_label.config(text=f"Current Group: {group_name}")
                self.load_group_history(group_id)

    def load_group_history(self, group_id):
        try:
            response = self.stub.GetGroupHistory(chat_pb2.GetGroupHistoryRequest(
                group_id=group_id
            ))
            if response.success:
                self.message_display.config(state=tk.NORMAL)
                self.message_display.delete(1.0, tk.END)
                for message in response.messages:
                    timestamp = datetime.fromtimestamp(message.timestamp).strftime("%H:%M:%S")
                    self.message_display.insert(tk.END, f"[{timestamp}] {message.sender}: {message.content}\n")
                self.message_display.config(state=tk.DISABLED)
                self.message_display.see(tk.END)
        except Exception as e:
            print(f"Error loading group history: {e}")

    def create_group(self):
        group_name = simpledialog.askstring("Create Group", "Enter group name:")
        if not group_name:
            return
            
        try:
            response = self.stub.CreateGroup(chat_pb2.CreateGroupRequest(
                creator=self.username_var.get(),
                group_name=group_name
            ))
            if response.success:
                messagebox.showinfo("Success", f"Group '{group_name}' created successfully!")
                self.load_user_groups()
            else:
                messagebox.showerror("Error", response.message)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create group: {str(e)}")

    def join_group(self):
        group_id = tk.simpledialog.askstring("Join Group", "Enter group ID:")
        if not group_id:
            return
            
        try:
            response = self.stub.JoinGroup(chat_pb2.JoinGroupRequest(
                username=self.username_var.get(),
                group_id=group_id
            ))
            if response.success:
                messagebox.showinfo("Success", "Joined group successfully!")
                self.load_user_groups()
            else:
                messagebox.showerror("Error", response.message)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to join group: {str(e)}")

    def leave_group(self):
        if not self.current_group:
            messagebox.showerror("Error", "Please select a group first")
            return
            
        # Confirm before leaving
        if not messagebox.askyesno("Confirm", "Are you sure you want to leave this group?"):
            return
            
        try:
            response = self.stub.LeaveGroup(chat_pb2.LeaveGroupRequest(
                username=self.username_var.get(),
                group_id=self.current_group
            ))
            if response.success:
                messagebox.showinfo("Success", "Left group successfully!")
                # Clear current group
                self.current_group = None
                self.current_group_label.config(text="")
                # Clear message display
                self.message_display.config(state=tk.NORMAL)
                self.message_display.delete(1.0, tk.END)
                self.message_display.config(state=tk.DISABLED)
                # Reload groups list
                self.load_user_groups()
            else:
                messagebox.showerror("Error", response.message)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to leave group: {str(e)}")
            print(f"Error leaving group: {e}")  # Add debug logging

    def invite_user(self):
        if not self.current_group:
            messagebox.showerror("Error", "Please select a group first")
            return
            
        username = simpledialog.askstring("Invite User", "Enter username to invite:")
        if not username:
            return
            
        if username == self.username_var.get():
            messagebox.showerror("Error", "You cannot invite yourself")
            return
            
        try:
            response = self.stub.InviteUser(chat_pb2.InviteUserRequest(
                group_id=self.current_group,
                inviter=self.username_var.get(),
                invitee=username
            ))
            if response.success:
                messagebox.showinfo("Success", response.message)
            else:
                messagebox.showerror("Error", response.message)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to invite user: {str(e)}")
            print(f"Error inviting user: {e}")  # Add debug logging

    def send_message(self):
        if not self.current_group:
            messagebox.showerror("Error", "Please select a group first")
            return
            
        message = self.message_var.get()
        if message:
            try:
                chat_message = chat_pb2.ChatMessage(
                    sender=self.username_var.get(),
                    content=message,
                    type=chat_pb2.GROUP,
                    group_id=self.current_group
                )
                
                # Check if we are a member of the group
                if self.current_group not in self.user_groups:
                    messagebox.showerror("Error", "You are not a member of this group")
                    return
                    
                self.message_queue.put(chat_message)
                self.display_sent_message(chat_message)
                self.message_var.set("")  # Clear input field
            except Exception as e:
                messagebox.showerror("Error", f"Failed to send message: {str(e)}")

    def display_message(self, message):
        try:
            # Luôn reload nhóm nếu là System message
            if message.sender == "System":
                self.load_user_groups()
                return

            # Chỉ hiển thị message group nếu đúng group đang chọn
            if message.type == chat_pb2.GROUP and str(message.group_id) == str(self.current_group):
                self.message_display.config(state=tk.NORMAL)
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.message_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
                self.message_display.insert(tk.END, f"{message.sender}: ", "sender")
                self.message_display.insert(tk.END, f"{message.content}\n", "content")
                self.message_display.tag_configure("timestamp", foreground="#666666")
                self.message_display.tag_configure("sender", foreground="#0000FF", font=("Helvetica", 10, "bold"))
                self.message_display.tag_configure("content", foreground="#000000")
                self.message_display.see(tk.END)
                self.message_display.update_idletasks()
                self.message_display.config(state=tk.DISABLED)
        except Exception as e:
            print(f"Error displaying message: {e}")

    def display_sent_message(self, message):
        try:
            self.message_display.config(state=tk.NORMAL)
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            self.message_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
            self.message_display.insert(tk.END, f"You: ", "sender")
            self.message_display.insert(tk.END, f"{message.content}\n", "content")
            
            self.message_display.tag_configure("timestamp", foreground="#666666")
            self.message_display.tag_configure("sender", foreground="#008000", font=("Helvetica", 10, "bold"))
            self.message_display.tag_configure("content", foreground="#000000")
            
            self.message_display.see(tk.END)
            self.message_display.update_idletasks()
            
            self.message_display.config(state=tk.DISABLED)
        except Exception as e:
            print(f"Error displaying sent message: {e}")

    def show_register_dialog(self):
        # Create a new top-level window for registration
        register_window = tk.Toplevel(self.window)
        register_window.title("Register New Account")
        register_window.geometry("400x250")
        register_window.configure(bg="#f0f0f0")
        
        # Make the window modal
        register_window.transient(self.window)
        register_window.grab_set()
        
        # Center the window
        register_window.update_idletasks()
        width = register_window.winfo_width()
        height = register_window.winfo_height()
        x = (register_window.winfo_screenwidth() // 2) - (width // 2)
        y = (register_window.winfo_screenheight() // 2) - (height // 2)
        register_window.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
        # Create and configure the registration form
        frame = ttk.Frame(register_window, padding="20", style="TFrame")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Username field
        ttk.Label(frame, text="Username:", style="TLabel").grid(row=0, column=0, sticky=tk.W, pady=5)
        username_var = tk.StringVar()
        username_entry = ttk.Entry(frame, textvariable=username_var, width=30, font=("Helvetica", 10))
        username_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        # Password field
        ttk.Label(frame, text="Password:", style="TLabel").grid(row=1, column=0, sticky=tk.W, pady=5)
        password_var = tk.StringVar()
        password_entry = ttk.Entry(frame, textvariable=password_var, show="*", width=30, font=("Helvetica", 10))
        password_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        # Confirm password field
        ttk.Label(frame, text="Confirm Password:", style="TLabel").grid(row=2, column=0, sticky=tk.W, pady=5)
        confirm_password_var = tk.StringVar()
        confirm_password_entry = ttk.Entry(frame, textvariable=confirm_password_var, show="*", width=30, font=("Helvetica", 10))
        confirm_password_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        # Status label
        status_label = ttk.Label(frame, text="", style="TLabel")
        status_label.grid(row=3, column=0, columnspan=2, pady=10)
        
        def register():
            username = username_var.get()
            password = password_var.get()
            confirm_password = confirm_password_var.get()
            
            # Validate input
            if not username or not password or not confirm_password:
                status_label.config(text="Please fill in all fields", foreground="red")
                return
                
            if password != confirm_password:
                status_label.config(text="Passwords do not match", foreground="red")
                return
                
            if len(password) < 6:
                status_label.config(text="Password must be at least 6 characters", foreground="red")
                return
            
            try:
                response = self.stub.Register(chat_pb2.RegisterRequest(
                    username=username,
                    password=password
                ))
                
                if response.success:
                    messagebox.showinfo("Success", "Registration successful! Please login.")
                    register_window.destroy()
                else:
                    status_label.config(text=response.message, foreground="red")
            except Exception as e:
                status_label.config(text=f"Registration failed: {str(e)}", foreground="red")
        
        # Register button
        register_button = ttk.Button(frame, text="Register", command=register, style="TButton", width=15)
        register_button.grid(row=4, column=0, columnspan=2, pady=10)
        
        # Bind Enter key to register
        register_window.bind('<Return>', lambda e: register())
        
        # Focus on username field
        username_entry.focus()

    def sign_out(self):
        try:
            # Stop the message receiver thread
            self.is_running = False
            if self.receiver_thread:
                self.receiver_thread.join(timeout=1.0)
            
            # Clear all data
            self.current_group = None
            self.user_groups.clear()
            self.group_list.delete(0, tk.END)
            self.message_display.config(state=tk.NORMAL)
            self.message_display.delete(1.0, tk.END)
            self.message_display.config(state=tk.DISABLED)
            self.current_group_label.config(text="")
            
            # Clear message queue
            while not self.message_queue.empty():
                try:
                    self.message_queue.get_nowait()
                except queue.Empty:
                    break
            
            # Show login frame and hide chat frame
            self.chat_frame.grid_remove()
            self.login_frame.grid()
            
            # Clear login fields
            self.username_var.set("")
            self.password_var.set("")
            
            messagebox.showinfo("Success", "Signed out successfully!")
        except Exception as e:
            print(f"Error during sign out: {e}")
            messagebox.showerror("Error", f"Error during sign out: {str(e)}")

    def run(self):
        self.window.mainloop()

def main():
    client = ChatClient()
    client.run()

if __name__ == '__main__':
    main() 