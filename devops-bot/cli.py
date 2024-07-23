import os
import requests
import click
from flask import Flask
import time

cli = click.Group()

API_BASE_URL = "https://devopsbot-testserver.online"

BASE_DIR = os.path.expanduser("~/.etc/devops-bot")
MASTER_INFO_FILE = os.path.join(BASE_DIR, "master_info.json")
AWS_CREDENTIALS_FILE = os.path.join(BASE_DIR, "aws_credentials.json")
DEVOPS_BOT_TOKEN_FILE = os.path.join(BASE_DIR, "devops_bot_token")

app = Flask(__name__)

def ensure_user_folder():
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR, mode=0o700, exist_ok=True)

def save_token(token):
    ensure_user_folder()
    with open(DEVOPS_BOT_TOKEN_FILE, 'w') as token_file:
        token_file.write(token)
    os.chmod(DEVOPS_BOT_TOKEN_FILE, 0o600)

@click.group()
def cli():
    """DevOps Bot CLI."""
    pass

@cli.command(help="Login to the DevOps Bot.")
def login():
    username = click.prompt('Enter your username')
    password = click.prompt('Enter your password', hide_input=True)
    response = requests.post(f"{API_BASE_URL}/api/login", headers={'Content-Type': 'application/json'}, json={"username": username, "password": password})
    if response.status_code == 200:
        token = response.json().get('token')
        if token:
            save_token(token)
            click.echo(f"Login successful! Your token is: {token}")
            verify_token(username, token)
        else:
            click.echo("Failed to retrieve token.")
    else:
        click.echo("Invalid username or password")

def verify_token(username, token):
    for _ in range(12):  # 1 minute with 5-second intervals
        response = requests.post(f"{API_BASE_URL}/api/verify_token", headers={'Content-Type': 'application/json'}, json={"username": username, "token": token})
        if response.status_code == 200:
            click.echo(f"Token verified successfully for {username}.")
            return
        time.sleep(5)
    click.echo("Token verification failed.")

if __name__ == '__main__':
    cli.add_command(login)
    cli()
