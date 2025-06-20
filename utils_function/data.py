# Language options
LANGUAGES = [
    {'label': 'English', 'value': 'en'},
    {'label': 'Vietnamese', 'value': 'vi'},
    {'label': 'Spanish', 'value': 'es'},
]

# Placeholder for user credentials
user_credentials = {'admin': 'admin'}

# Function to authenticate user
def authenticate(username, password):
    return username == 'admin' and password == 'admin'

# Function to update user password
def update_password(username, new_password):
    global user_credentials
    if username in user_credentials:
        user_credentials[username] = new_password
        return True
    return False