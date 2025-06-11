import grpc
import mysql.connector
import bcrypt
from concurrent import futures
import time
import chat_pb2
import chat_pb2_grpc
from datetime import datetime
import threading
import queue

class ChatServicer(chat_pb2_grpc.ChatServiceServicer):
    def __init__(self):
        self.active_users = {}  # username -> stream
        self.message_queues = {}  # username -> queue
        self.db = None
        self.cursor = None
        self.connect_db()
        print("Chat server initialized")

    def connect_db(self):
        try:
            if self.db is not None:
                try:
                    self.db.close()
                except:
                    pass
            
            self.db = mysql.connector.connect(
                host="localhost",
                user="root",
                password="root",
                database="chat_db",
                autocommit=True,
                pool_name="mypool",
                pool_size=5,
                connect_timeout=60,
                connection_timeout=60
            )
            self.db.ping(reconnect=True, attempts=3, delay=5)
            self.cursor = self.db.cursor(dictionary=True)
            print("Database connected successfully")
        except Exception as e:
            print(f"Error connecting to database: {e}")
            raise

    def ensure_db_connection(self):
        try:
            self.db.ping(reconnect=True, attempts=3, delay=5)
        except Exception as e:
            print(f"Lost connection to database, reconnecting... Error: {e}")
            self.connect_db()

    def execute_query(self, query, params=None):
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                self.ensure_db_connection()
                if params:
                    self.cursor.execute(query, params)
                else:
                    self.cursor.execute(query)
                return True
            except mysql.connector.Error as err:
                print(f"Database error (attempt {retry_count + 1}/{max_retries}): {err}")
                retry_count += 1
                if retry_count == max_retries:
                    raise
                time.sleep(1)  # Wait before retrying

    def fetch_one(self, query, params=None):
        self.execute_query(query, params)
        return self.cursor.fetchone()

    def fetch_all(self, query, params=None):
        self.execute_query(query, params)
        return self.cursor.fetchall()

    def Register(self, request, context):
        try:
            # Check if username exists
            user = self.fetch_one("SELECT id FROM users WHERE username = %s", (request.username,))
            if user:
                return chat_pb2.RegisterResponse(success=False, message="Username already exists")

            # Hash password
            password_hash = bcrypt.hashpw(request.password.encode(), bcrypt.gensalt())
            
            # Insert new user
            self.execute_query(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (request.username, password_hash)
            )
            self.db.commit()
            
            return chat_pb2.RegisterResponse(success=True, message="Registration successful")
        except Exception as e:
            return chat_pb2.RegisterResponse(success=False, message=str(e))

    def Login(self, request, context):
        try:
            user = self.fetch_one(
                "SELECT id, password_hash FROM users WHERE username = %s",
                (request.username,)
            )
            
            if not user:
                return chat_pb2.LoginResponse(success=False, message="User not found")
            
            if bcrypt.checkpw(request.password.encode(), user['password_hash'].encode()):
                return chat_pb2.LoginResponse(success=True, message="Login successful")
            else:
                return chat_pb2.LoginResponse(success=False, message="Invalid password")
        except Exception as e:
            return chat_pb2.LoginResponse(success=False, message=str(e))

    def CreateGroup(self, request, context):
        try:
            print(f"Creating group: {request.group_name} by {request.creator}")
            # Get user ID
            user = self.fetch_one("SELECT id FROM users WHERE username = %s", (request.creator,))
            if not user:
                print(f"User {request.creator} not found")
                return chat_pb2.CreateGroupResponse(success=False, message="User not found")

            # Create group
            self.execute_query(
                "INSERT INTO groups (group_name, creator_id) VALUES (%s, %s)",
                (request.group_name, user['id'])
            )
            group_id = self.cursor.lastrowid

            # Add creator as member
            self.execute_query(
                "INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)",
                (group_id, user['id'])
            )
            self.db.commit()
            print(f"Group created successfully with ID: {group_id}")

            return chat_pb2.CreateGroupResponse(
                success=True,
                group_id=str(group_id),
                message="Group created successfully"
            )
        except Exception as e:
            print(f"Error creating group: {e}")
            return chat_pb2.CreateGroupResponse(success=False, message=str(e))

    def JoinGroup(self, request, context):
        try:
            # Get user ID
            user = self.fetch_one("SELECT id FROM users WHERE username = %s", (request.username,))
            if not user:
                return chat_pb2.JoinGroupResponse(success=False, message="User not found")

            # Check if group exists
            group = self.fetch_one("SELECT id FROM groups WHERE id = %s", (int(request.group_id),))
            if not group:
                return chat_pb2.JoinGroupResponse(success=False, message="Group not found")

            # Check if user is already a member
            membership = self.fetch_one("""
                SELECT id FROM group_members WHERE group_id = %s AND user_id = %s
            """, (int(request.group_id), user['id']))
            if membership:
                return chat_pb2.JoinGroupResponse(success=False, message="Already a member of this group")

            # Add user to group
            self.execute_query(
                "INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)",
                (int(request.group_id), user['id'])
            )
            self.db.commit()

            return chat_pb2.JoinGroupResponse(success=True, message="Joined group successfully")
        except Exception as e:
            return chat_pb2.JoinGroupResponse(success=False, message=str(e))

    def LeaveGroup(self, request, context):
        try:
            # Get user ID
            user = self.fetch_one("SELECT id FROM users WHERE username = %s", (request.username,))
            if not user:
                return chat_pb2.LeaveGroupResponse(success=False, message="User not found")

            # Remove user from group
            self.execute_query(
                "DELETE FROM group_members WHERE group_id = %s AND user_id = %s",
                (int(request.group_id), user['id'])
            )
            self.db.commit()

            return chat_pb2.LeaveGroupResponse(success=True, message="Left group successfully")
        except Exception as e:
            return chat_pb2.LeaveGroupResponse(success=False, message=str(e))

    def GetUserGroups(self, request, context):
        try:
            print(f"Getting groups for user: {request.username}")
            # Get user ID
            user = self.fetch_one("SELECT id FROM users WHERE username = %s", (request.username,))
            if not user:
                print(f"User {request.username} not found")
                return chat_pb2.GetUserGroupsResponse(success=False, message="User not found")

            # Get all groups the user is a member of
            groups = self.fetch_all("""
                SELECT g.id as group_id, g.group_name 
                FROM groups g 
                JOIN group_members gm ON g.id = gm.group_id 
                WHERE gm.user_id = %s
            """, (user['id'],))
            
            group_infos = []
            for row in groups:
                group_infos.append(chat_pb2.GroupInfo(
                    group_id=str(row['group_id']),
                    group_name=row['group_name']
                ))
            print(f"Found {len(group_infos)} groups for user {request.username}")

            return chat_pb2.GetUserGroupsResponse(
                success=True,
                groups=group_infos
            )
        except Exception as e:
            print(f"Error getting user groups: {e}")
            return chat_pb2.GetUserGroupsResponse(success=False, message=str(e))

    def GetGroupHistory(self, request, context):
        try:
            # Get messages for the group
            messages = self.fetch_all("""
                SELECT m.content, m.timestamp, u.username as sender
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE m.group_id = %s
                ORDER BY m.timestamp ASC
            """, (int(request.group_id),))
            
            message_infos = []
            for row in messages:
                message_infos.append(chat_pb2.MessageInfo(
                    content=row['content'],
                    sender=row['sender'],
                    timestamp=int(row['timestamp'].timestamp())
                ))

            return chat_pb2.GetGroupHistoryResponse(
                success=True,
                messages=message_infos
            )
        except Exception as e:
            return chat_pb2.GetGroupHistoryResponse(success=False, message=str(e))

    def Chat(self, request_iterator, context):
        username = None
        print("New chat connection established")
        
        def send_message(message):
            try:
                # Skip processing for heartbeat messages
                if message.type == chat_pb2.HEARTBEAT:
                    return

                print(f"Processing message from {message.sender} to group {message.group_id}")
                
                # Get sender's user ID
                sender = self.fetch_one("SELECT id FROM users WHERE username = %s", (message.sender,))
                if not sender:
                    print(f"Error: Sender {message.sender} not found")
                    return

                # Nếu là tin nhắn hệ thống, gửi cho tất cả người dùng đang online
                if message.sender == "System":
                    print("Processing system message")
                    for username in self.active_users:
                        try:
                            print(f"Sending system message to {username}")
                            self.active_users[username].put(message)
                        except Exception as e:
                            print(f"Error sending system message to {username}: {e}")
                    return

                # Check if sender is a member of the group
                membership = self.fetch_one("""
                    SELECT gm.id, g.group_name 
                    FROM group_members gm 
                    JOIN groups g ON g.id = gm.group_id
                    WHERE gm.group_id = %s AND gm.user_id = %s
                """, (int(message.group_id), sender['id']))
                
                if not membership:
                    print(f"Error: {message.sender} is not a member of group {message.group_id}")
                    return

                # Save message to database with transaction
                try:
                    self.execute_query("START TRANSACTION")
                    self.execute_query(
                        "INSERT INTO messages (sender_id, content, message_type, group_id, timestamp) VALUES (%s, %s, %s, %s, NOW())",
                        (
                            sender['id'],
                            message.content,
                            message.type,
                            int(message.group_id)
                        )
                    )
                    self.db.commit()
                    print(f"Message saved to database: {message.content}")
                except Exception as e:
                    self.db.rollback()
                    print(f"Error saving message to database: {e}")
                    return

                # Get all current group members
                members = self.fetch_all("""
                    SELECT DISTINCT u.username 
                    FROM users u 
                    JOIN group_members gm ON u.id = gm.user_id 
                    WHERE gm.group_id = %s
                """, (int(message.group_id),))
                
                print(f"Sending group message to {len(members)} members")

                # Send message to all online members except sender
                for member in members:
                    username = member['username']
                    if username in self.active_users and username != message.sender:
                        try:
                            print(f"Sending to group member: {username}")
                            self.active_users[username].put(message)
                            print(f"Message queued for {username}")
                        except Exception as e:
                            print(f"Error sending message to {username}: {e}")

            except Exception as e:
                print(f"Error in send_message: {e}")
                try:
                    self.db.rollback()
                except:
                    pass

        # Handle incoming messages
        for message in request_iterator:
            try:
                if not username:
                    username = message.sender
                    print(f"User {username} connected")
                    # Tạo queue mới cho user
                    self.active_users[username] = queue.Queue()
                    print(f"Active users: {list(self.active_users.keys())}")
                    
                    # Gửi tin nhắn thông báo kết nối thành công
                    connect_msg = chat_pb2.ChatMessage(
                        sender="System",
                        content="Connected to chat server",
                        type=chat_pb2.GROUP,
                        group_id=""
                    )
                    self.active_users[username].put(connect_msg)
                    
                    # Trigger cập nhật danh sách group
                    update_msg = chat_pb2.ChatMessage(
                        sender="System",
                        content="UPDATE_GROUPS",
                        type=chat_pb2.GROUP,
                        group_id=""
                    )
                    self.active_users[username].put(update_msg)
                
                # Skip processing for empty/heartbeat messages
                if message.type == chat_pb2.HEARTBEAT:
                    print(f"Received heartbeat from {message.sender}")
                elif message.content:
                    print(f"Received message from {message.sender}: {message.content}")
                    send_message(message)

                # Yield any messages for this user
                try:
                    while True:  # Thay đổi từ not self.active_users[username].empty()
                        try:
                            msg = self.active_users[username].get_nowait()
                            print(f"Yielding message to {username}: {msg.content}")
                            yield msg
                        except queue.Empty:
                            break
                except Exception as e:
                    print(f"Error yielding messages: {e}")
                
            except Exception as e:
                print(f"Error processing message: {e}")
            
            # Small delay to prevent CPU overuse
            time.sleep(0.1)
        
        # Remove user from active users when they disconnect
        if username and username in self.active_users:
            print(f"User {username} disconnected")
            del self.active_users[username]

    def InviteUser(self, request, context):
        try:
            print(f"Inviting user {request.invitee} to group {request.group_id} by {request.inviter}")
            
            # Check if inviter is a member of the group
            inviter_data = self.fetch_one("""
                SELECT u.id, g.group_name FROM users u
                JOIN group_members gm ON u.id = gm.user_id
                JOIN groups g ON g.id = gm.group_id
                WHERE u.username = %s AND gm.group_id = %s
            """, (request.inviter, int(request.group_id)))
            if not inviter_data:
                print(f"User {request.inviter} is not a member of group {request.group_id}")
                return chat_pb2.InviteUserResponse(success=False, message="You are not a member of this group")

            # Check if invitee exists
            invitee = self.fetch_one("SELECT id FROM users WHERE username = %s", (request.invitee,))
            if not invitee:
                print(f"User {request.invitee} not found")
                return chat_pb2.InviteUserResponse(success=False, message="User not found")

            # Check if invitee is already a member
            membership = self.fetch_one("""
                SELECT id FROM group_members 
                WHERE group_id = %s AND user_id = %s
            """, (int(request.group_id), invitee['id']))
            if membership:
                print(f"User {request.invitee} is already a member of group {request.group_id}")
                return chat_pb2.InviteUserResponse(success=False, message="User is already a member of this group")

            # Start transaction
            self.execute_query("START TRANSACTION")
            try:
                # Add invitee to group
                self.execute_query(
                    "INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)",
                    (int(request.group_id), invitee['id'])
                )
                
                # Get group name for notifications
                group_name = inviter_data['group_name']
                
                # Commit transaction
                self.db.commit()
                print(f"User {request.invitee} added to group {request.group_id}")

                # Gửi thông báo cho người được mời
                if request.invitee in self.active_users:
                    invite_notification = chat_pb2.ChatMessage(
                        sender="System",
                        content=f"You have been invited to group '{group_name}' by {request.inviter}",
                        type=chat_pb2.GROUP,
                        group_id=request.group_id
                    )
                    self.active_users[request.invitee].put(invite_notification)

                    # Gửi thêm một message đặc biệt để trigger cập nhật danh sách group
                    update_trigger = chat_pb2.ChatMessage(
                        sender="System",
                        content="UPDATE_GROUPS",
                        type=chat_pb2.GROUP,
                        group_id=""
                    )
                    self.active_users[request.invitee].put(update_trigger)

                # Thông báo cho các thành viên khác trong group
                members = self.fetch_all("""
                    SELECT u.username FROM users u
                    JOIN group_members gm ON u.id = gm.user_id
                    WHERE gm.group_id = %s AND u.username != %s
                """, (int(request.group_id), request.invitee))
                
                member_notifications = []
                for member in members:
                    if member['username'] in self.active_users:
                        member_notifications.append(chat_pb2.ChatMessage(
                            sender="System",
                            content=f"{request.invitee} has joined the group '{group_name}'",
                            type=chat_pb2.GROUP,
                            group_id=request.group_id
                        ))
                        self.active_users[member['username']].put(member_notifications[-1])

                return chat_pb2.InviteUserResponse(success=True, message=f"User {request.invitee} has been invited to the group")

            except Exception as e:
                self.db.rollback()
                print(f"Database error while inviting user: {e}")
                return chat_pb2.InviteUserResponse(success=False, message=f"Failed to invite user: {str(e)}")

        except Exception as e:
            print(f"Error inviting user: {e}")
            return chat_pb2.InviteUserResponse(success=False, message=str(e))

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat_pb2_grpc.add_ChatServiceServicer_to_server(ChatServicer(), server)
    port = 50051
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    print(f"Server started on port {port}")
    print("Press Ctrl+C to stop the server")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop(0)
        print("Server stopped")

if __name__ == '__main__':
    serve() 