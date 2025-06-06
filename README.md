# gRPC Chat System

A real-time chat system built with gRPC, Python, and MySQL that supports both direct messaging and group chats.

## Features

- User registration and authentication
- Direct messaging between users
- Group chat creation and management
- Real-time message delivery
- Message history storage in MySQL database

## Prerequisites

- Python 3.7+
- MySQL Server
- pip (Python package manager)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Create and activate virtual environment:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
```

3. Install required Python packages:
```bash
pip install -r requirements.txt
```

4. Set up MySQL database:
- Create a MySQL database and user
- Update the database connection settings in `server.py` if needed
- Run the schema.sql file to create the necessary tables:
```bash
mysql -u root -p < schema.sql
```

5. Generate gRPC code:
```bash
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. chat.proto
```

## Running the Application

1. Make sure your virtual environment is activated:
```bash
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
```

2. Start the server:
```bash
python server.py
```

3. In a new terminal (with virtual environment activated), start the client:
```bash
python client.py
```

## Usage

### Client Commands

1. Register/Login:
   - Choose option 1 to register a new account
   - Choose option 2 to login with existing credentials

2. After logging in:
   - Option 1: Send direct message to another user
   - Option 2: Create a new group chat
   - Option 3: Join an existing group chat
   - Option 4: Leave a group chat
   - Option 5: Send message to a group
   - Option 6: Exit the application

### Message Format

- Direct messages: Messages are sent directly to the specified user
- Group messages: Messages are sent to all members of the specified group

## Security Notes

- Passwords are hashed using bcrypt before storage
- No JWT authentication is used as per requirements
- Basic username/password authentication is implemented

## Error Handling

The system includes basic error handling for:
- Invalid credentials
- Non-existent users
- Group management errors
- Connection issues

## Development

### Virtual Environment

The project uses a virtual environment to manage dependencies. This ensures that:
- Dependencies are isolated from other Python projects
- Version conflicts are avoided
- The project can be easily reproduced on other machines

To deactivate the virtual environment when you're done:
```bash
deactivate
```

## Contributing

Feel free to submit issues and enhancement requests! 