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
        self.db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",  # Set your MySQL password here
            database="chat_db"
        )
        self.cursor = self.db.cursor(dictionary=True)
        print("Chat server initialized")

    def Register(self, request, context):
        try:
            # Check if username exists
            self.cursor.execute("SELECT id FROM users WHERE username = %s", (request.username,))
            if self.cursor.fetchone():
                return chat_pb2.RegisterResponse(success=False, message="Username already exists")

            # Hash password
            password_hash = bcrypt.hashpw(request.password.encode(), bcrypt.gensalt())
            
            # Insert new user
            self.cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (request.username, password_hash)
            )
            self.db.commit()
            
            return chat_pb2.RegisterResponse(success=True, message="Registration successful")
        except Exception as e:
            return chat_pb2.RegisterResponse(success=False, message=str(e))

    def Login(self, request, context):
        try:
            self.cursor.execute("SELECT id, password_hash FROM users WHERE username = %s", (request.username,))
            user = self.cursor.fetchone()
            
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
            self.cursor.execute("SELECT id FROM users WHERE username = %s", (request.creator,))
            user = self.cursor.fetchone()
            if not user:
                print(f"User {request.creator} not found")
                return chat_pb2.CreateGroupResponse(success=False, message="User not found")

            # Create group
            self.cursor.execute(
                "INSERT INTO groups (group_name, creator_id) VALUES (%s, %s)",
                (request.group_name, user['id'])
            )
            group_id = self.cursor.lastrowid

            # Add creator as member
            self.cursor.execute(
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
            self.cursor.execute("SELECT id FROM users WHERE username = %s", (request.username,))
            user = self.cursor.fetchone()
            if not user:
                return chat_pb2.JoinGroupResponse(success=False, message="User not found")

            # Check if group exists
            self.cursor.execute("SELECT id FROM groups WHERE id = %s", (int(request.group_id),))
            if not self.cursor.fetchone():
                return chat_pb2.JoinGroupResponse(success=False, message="Group not found")

            # Check if user is already a member
            self.cursor.execute(
                "SELECT id FROM group_members WHERE group_id = %s AND user_id = %s",
                (int(request.group_id), user['id'])
            )
            if self.cursor.fetchone():
                return chat_pb2.JoinGroupResponse(success=False, message="Already a member of this group")

            # Add user to group
            self.cursor.execute(
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
            self.cursor.execute("SELECT id FROM users WHERE username = %s", (request.username,))
            user = self.cursor.fetchone()
            if not user:
                return chat_pb2.LeaveGroupResponse(success=False, message="User not found")

            # Remove user from group
            self.cursor.execute(
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
            self.cursor.execute("SELECT id FROM users WHERE username = %s", (request.username,))
            user = self.cursor.fetchone()
            if not user:
                print(f"User {request.username} not found")
                return chat_pb2.GetUserGroupsResponse(success=False, message="User not found")

            # Get all groups the user is a member of
            self.cursor.execute("""
                SELECT g.id as group_id, g.group_name 
                FROM groups g 
                JOIN group_members gm ON g.id = gm.group_id 
                WHERE gm.user_id = %s
            """, (user['id'],))
            
            groups = []
            for row in self.cursor.fetchall():
                groups.append(chat_pb2.GroupInfo(
                    group_id=str(row['group_id']),
                    group_name=row['group_name']
                ))
            print(f"Found {len(groups)} groups for user {request.username}")

            return chat_pb2.GetUserGroupsResponse(
                success=True,
                groups=groups
            )
        except Exception as e:
            print(f"Error getting user groups: {e}")
            return chat_pb2.GetUserGroupsResponse(success=False, message=str(e))

    def GetGroupHistory(self, request, context):
        try:
            # Get messages for the group
            self.cursor.execute("""
                SELECT m.content, m.timestamp, u.username as sender
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE m.group_id = %s
                ORDER BY m.timestamp ASC
            """, (int(request.group_id),))
            
            messages = []
            for row in self.cursor.fetchall():
                messages.append(chat_pb2.MessageInfo(
                    content=row['content'],
                    sender=row['sender'],
                    timestamp=int(row['timestamp'].timestamp())
                ))

            return chat_pb2.GetGroupHistoryResponse(
                success=True,
                messages=messages
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
                self.cursor.execute("SELECT id FROM users WHERE username = %s", (message.sender,))
                sender = self.cursor.fetchone()
                if not sender:
                    print(f"Error: Sender {message.sender} not found")
                    return

                # Check if sender is a member of the group
                self.cursor.execute("""
                    SELECT id FROM group_members 
                    WHERE group_id = %s AND user_id = %s
                """, (int(message.group_id), sender['id']))
                
                if not self.cursor.fetchone():
                    print(f"Error: {message.sender} is not a member of group {message.group_id}")
                    return

                # Save message to database
                self.cursor.execute(
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

                # Get all group members
                self.cursor.execute(
                    "SELECT u.username FROM users u JOIN group_members gm ON u.id = gm.user_id WHERE gm.group_id = %s",
                    (int(message.group_id),)
                )
                members = self.cursor.fetchall()
                print(f"Sending group message to {len(members)} members")
                for member in members:
                    if member['username'] in self.active_users and member['username'] != message.sender:
                        print(f"Sending to group member: {member['username']}")
                        self.active_users[member['username']].put(message)
                        print(f"Message queued for {member['username']}")
            except Exception as e:
                print(f"Error in send_message: {e}")

        # Handle incoming messages
        for message in request_iterator:
            try:
                if not username:
                    username = message.sender
                    print(f"User {username} connected")
                    self.active_users[username] = queue.Queue()
                    print(f"Active users: {list(self.active_users.keys())}")
                
                # Skip processing for empty/heartbeat messages
                if message.type == chat_pb2.HEARTBEAT:
                    print(f"Received heartbeat from {message.sender}")
                elif message.content:
                    print(f"Received message from {message.sender}: {message.content}")
                    send_message(message)

                # Yield any messages for this user
                try:
                    while not self.active_users[username].empty():
                        msg = self.active_users[username].get_nowait()
                        print(f"Yielding message to {username}: {msg.content}")
                        yield msg
                except queue.Empty:
                    pass
                
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
            self.cursor.execute("""
                SELECT u.id FROM users u
                JOIN group_members gm ON u.id = gm.user_id
                WHERE u.username = %s AND gm.group_id = %s
            """, (request.inviter, int(request.group_id)))
            inviter = self.cursor.fetchone()
            if not inviter:
                print(f"User {request.inviter} is not a member of group {request.group_id}")
                return chat_pb2.InviteUserResponse(success=False, message="You are not a member of this group")

            # Check if invitee exists
            self.cursor.execute("SELECT id FROM users WHERE username = %s", (request.invitee,))
            invitee = self.cursor.fetchone()
            if not invitee:
                print(f"User {request.invitee} not found")
                return chat_pb2.InviteUserResponse(success=False, message="User not found")

            # Check if invitee is already a member
            self.cursor.execute("""
                SELECT id FROM group_members 
                WHERE group_id = %s AND user_id = %s
            """, (int(request.group_id), invitee['id']))
            if self.cursor.fetchone():
                print(f"User {request.invitee} is already a member of group {request.group_id}")
                return chat_pb2.InviteUserResponse(success=False, message="User is already a member of this group")

            # Add invitee to group
            self.cursor.execute(
                "INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)",
                (int(request.group_id), invitee['id'])
            )
            self.db.commit()
            print(f"User {request.invitee} added to group {request.group_id}")

            # Notify all group members about the new member
            self.cursor.execute("""
                SELECT u.username FROM users u
                JOIN group_members gm ON u.id = gm.user_id
                WHERE gm.group_id = %s AND u.username != %s
            """, (int(request.group_id), request.invitee))
            
            members = self.cursor.fetchall()
            notification = chat_pb2.ChatMessage(
                sender="System",
                content=f"{request.invitee} has joined the group",
                type=chat_pb2.GROUP,
                group_id=request.group_id
            )
            
            for member in members:
                if member['username'] in self.active_users:
                    self.active_users[member['username']].put(notification)

            # Gửi thông báo cho chính người được mời (nếu đang online)
            if request.invitee in self.active_users:
                self.active_users[request.invitee].put(chat_pb2.ChatMessage(
                    sender="System",
                    content=f"You have been invited to group {request.group_id}",
                    type=chat_pb2.GROUP,
                    group_id=request.group_id
                ))

            return chat_pb2.InviteUserResponse(success=True, message=f"User {request.invitee} has been invited to the group")
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