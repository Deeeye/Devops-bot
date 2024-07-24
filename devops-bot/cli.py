import os
import requests
import click
import uuid
import json
import time
import yaml
import boto3
from flask import Flask
from cryptography.fernet import Fernet
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
from datetime import datetime



cli = click.Group()

API_BASE_URL = "https://devopsbot-testserver.online"

BASE_DIR = os.path.expanduser("~/.etc/devops-bot")
VERSION_DIR = os.path.join(BASE_DIR, "version")
AWS_CREDENTIALS_FILE = os.path.join(BASE_DIR, "aws_credentials.enc")
KEY_FILE = os.path.join(BASE_DIR, "key.key")
VERSION_BUCKET_NAME = "devops-bot-version-bucket"
DEVOPS_BOT_TOKEN_FILE = os.path.join(BASE_DIR, "devops_bot_token")
DOB_SCREENPLAY_FILE = os.path.join(BASE_DIR, "dob_screenplay.yaml")
app = Flask(__name__)

# Ensure user folder
def ensure_user_folder():
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR, mode=0o700, exist_ok=True)

# Ensure version folder
def ensure_version_folder():
    if not os.path.exists(VERSION_DIR):
        os.makedirs(VERSION_DIR, mode=0o700, exist_ok=True)

# Generate encryption key
def generate_key():
    key = Fernet.generate_key()
    with open(KEY_FILE, 'wb') as key_file:
        key_file.write(key)
    click.echo("Encryption key generated and saved.")

# Load encryption key
def load_key():
    return open(KEY_FILE, 'rb').read()

# Encrypt data
def encrypt_data(data, key):
    fernet = Fernet(key)
    encrypted = fernet.encrypt(data.encode())
    return encrypted

# Decrypt data
def decrypt_data(encrypted_data, key):
    fernet = Fernet(key)
    decrypted = fernet.decrypt(encrypted_data).decode()
    return decrypted

# Save AWS credentials encrypted
def save_aws_credentials(access_key, secret_key, region):
    ensure_user_folder()
    key = load_key()
    credentials = {
        'aws_access_key_id': access_key,
        'aws_secret_access_key': secret_key,
        'region_name': region
    }
    encrypted_credentials = encrypt_data(json.dumps(credentials), key)
    with open(AWS_CREDENTIALS_FILE, 'wb') as cred_file:
        cred_file.write(encrypted_credentials)
    os.chmod(AWS_CREDENTIALS_FILE, 0o600)
    click.echo("AWS credentials encrypted and saved locally.")

def check_bucket_exists(bucket_name):
    try:
        credentials = load_aws_credentials()
        s3 = boto3.client('s3', **credentials)
        s3.head_bucket(Bucket=bucket_name)
        return True
    except ClientError:
        return False

def list_versions_in_bucket():
    try:
        credentials = load_aws_credentials()
        s3 = boto3.client('s3', **credentials)
        response = s3.list_objects_v2(Bucket=VERSION_BUCKET_NAME)
        return response.get('Contents', [])
    except ClientError:
        return []

def list_versions_locally():
    ensure_version_folder()
    return [f for f in os.listdir(VERSION_DIR) if f.endswith('.enc')]



# Load AWS credentials and decrypt them
def load_aws_credentials():
    try:
        key = load_key()
        with open(AWS_CREDENTIALS_FILE, 'rb') as cred_file:
            encrypted_credentials = cred_file.read()
        decrypted_credentials = decrypt_data(encrypted_credentials, key)
        return json.loads(decrypted_credentials)
    except FileNotFoundError:
        return None

# Create an S3 bucket
def create_s3_bucket(bucket_name, region):
    try:
        credentials = load_aws_credentials()
        s3 = boto3.client('s3', aws_access_key_id=credentials['aws_access_key_id'], aws_secret_access_key=credentials['aws_secret_access_key'], region_name=credentials['region_name'])
        if region != "us-east-1":
            s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': region})
        else:
            s3.create_bucket(Bucket=bucket_name)
        click.echo(f"Bucket {bucket_name} created successfully.")
    except (NoCredentialsError, PartialCredentialsError) as e:
        click.echo(f"Error with AWS credentials: {e}")
    except ClientError as e:
        click.echo(f"Error creating bucket: {e}")

# Upload encrypted credentials to S3
def upload_encrypted_credentials_to_s3(bucket_name):
    try:
        key = load_key()
        with open(AWS_CREDENTIALS_FILE, 'rb') as cred_file:
            encrypted_credentials = cred_file.read()
            click.echo("Encrypted credentials loaded for upload.")

        credentials = load_aws_credentials()
        s3 = boto3.client('s3', aws_access_key_id=credentials['aws_access_key_id'], aws_secret_access_key=credentials['aws_secret_access_key'], region_name=credentials['region_name'])
        s3.put_object(Bucket=bucket_name, Key='aws_credentials.enc', Body=encrypted_credentials)
        click.echo(f"Encrypted credentials uploaded to bucket {bucket_name} successfully.")
    except (NoCredentialsError, PartialCredentialsError) as e:
        click.echo(f"Error with AWS credentials: {e}")
    except ClientError as e:
        click.echo(f"Error uploading encrypted credentials to bucket: {e}")

# Save the dob-screenplay content to a file
def save_dob_screenplay(dob_screenplay_content):
    with open(DOB_SCREENPLAY_FILE, 'w') as f:
        yaml.dump(dob_screenplay_content, f)
    click.echo("dob-screenplay content saved locally.")

@click.group()
def cli():
    """DevOps Bot CLI."""
    pass

@cli.command(name="configure-aws", help="Configure AWS credentials.")
@click.option('--aws_access_key_id', required=True, help="AWS Access Key ID")
@click.option('--aws_secret_access_key', required=True, help="AWS Secret Access Key")
@click.option('--region', required=True, help="AWS Region")
def configure_aws(aws_access_key_id, aws_secret_access_key, region):
    if not os.path.exists(KEY_FILE):
        generate_key()
    
    save_aws_credentials(aws_access_key_id, aws_secret_access_key, region)
    click.echo("AWS credentials configured and saved locally successfully.")

    if click.confirm("Do you want to save these credentials in a cloud storage like S3?", default=True):
        num_buckets = click.prompt("How many storage buckets do you require?", type=int)
        bucket_names = [click.prompt(f"Enter name for bucket {i+1}") for i in range(num_buckets)]

        dob_screenplay_content = {
            'version': '1.0',
            'resources': {
                's3_buckets': [
                    {'name': bucket_name, 'region': region} for bucket_name in bucket_names
                ]
            }
        }

        save_dob_screenplay(dob_screenplay_content)

        click.echo(yaml.dump(dob_screenplay_content))
        if click.confirm("Do you want to proceed with creating the above buckets?", default=True):
            for bucket in dob_screenplay_content['resources']['s3_buckets']:
                create_s3_bucket(bucket['name'], bucket['region'])
                upload_encrypted_credentials_to_s3(bucket['name'])

            click.echo("All buckets created successfully and encrypted credentials uploaded.")
        else:
            click.echo("Bucket creation aborted.")

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

def save_token(token):
    ensure_user_folder()
    with open(DEVOPS_BOT_TOKEN_FILE, 'w') as token_file:
        token_file.write(token)
    os.chmod(DEVOPS_BOT_TOKEN_FILE, 0o600)
    click.echo("Token saved locally.")

# EC2

def save_version_info_locally(version_id, comment, content):
    ensure_version_folder()
    key = load_key()
    version_info = {
        'version_id': version_id,
        'comment': comment,
        'content': content
    }
    encrypted_version_info = encrypt_data(json.dumps(version_info), key)
    with open(os.path.join(VERSION_DIR, f"{version_id}.enc"), 'wb') as version_file:
        version_file.write(encrypted_version_info)
    click.echo(f"Version information saved locally with ID {version_id}.")

# Serialize instance information
def serialize_instance_info(instance):
    for key, value in instance.items():
        if isinstance(value, datetime):
            instance[key] = value.isoformat()
        elif isinstance(value, list):
            instance[key] = [serialize_instance_info(item) if isinstance(item, dict) else item for item in value]
        elif isinstance(value, dict):
            instance[key] = serialize_instance_info(value)
    return instance

def save_version_info_to_bucket(version_id, comment, content):
    key = load_key()
    credentials = load_aws_credentials()
    if not credentials:
        click.echo("No AWS credentials found. Please configure them first.")
        return None
    
    version_info = {
        'version_id': version_id,
        'comment': comment,
        'content': [serialize_instance_info(instance) for instance in content]
    }
    encrypted_version_info = encrypt_data(json.dumps(version_info), key)

    s3 = boto3.client('s3', **credentials)
    try:
        s3.put_object(Bucket=VERSION_BUCKET_NAME, Key=f"{version_id}.enc", Body=encrypted_version_info)
        click.echo(f"Version information saved in S3 bucket with ID {version_id}.")
    except ClientError as e:
        click.echo(click.style(f"Failed to save version information to bucket: {e}", fg="red"))



def load_version_info(version_id):
    key = load_key()
    if os.path.exists(os.path.join(VERSION_DIR, f"{version_id}.enc")):
        with open(os.path.join(VERSION_DIR, f"{version_id}.enc"), 'rb') as version_file:
            encrypted_version_info = version_file.read()
        decrypted_version_info = decrypt_data(encrypted_version_info, key)
        return json.loads(decrypted_version_info)
    else:
        try:
            credentials = load_aws_credentials()
            s3 = boto3.client('s3', **credentials)
            response = s3.get_object(Bucket=VERSION_BUCKET_NAME, Key=f"{version_id}.enc")
            encrypted_version_info = response['Body'].read()
            decrypted_version_info = decrypt_data(encrypted_version_info, key)
            return json.loads(decrypted_version_info)
        except ClientError as e:
            click.echo(click.style(f"No version information found for ID {version_id}.", fg="red"))
            return None
def create_ec2_instances(instance_type, ami_id, key_name, security_group, count, tags):
    credentials = load_aws_credentials()
    if not credentials:
        click.echo("No AWS credentials found. Please configure them first.")
        return None

    ec2 = boto3.client('ec2', **credentials)
    try:
        instances = ec2.run_instances(
            ImageId=ami_id,
            InstanceType=instance_type,
            KeyName=key_name,
            SecurityGroupIds=[security_group],
            MinCount=count,
            MaxCount=count,
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [{'Key': k, 'Value': v} for k, v in tags.items()]
                }
            ]
        )
        return instances['Instances']
    except ClientError as e:
        click.echo(click.style(f"Failed to create instances: {e}", fg="red"))
        return None

@cli.command(name="create-ec2", help="Create EC2 instances with specified options.")
@click.option('--instance-type', required=True, help="EC2 instance type")
@click.option('--ami-id', required=True, help="AMI ID")
@click.option('--key-name', required=True, help="Key pair name")
@click.option('--security-group', required=True, help="Security group ID")
@click.option('--count', default=1, help="Number of instances to create")
@click.option('--tags', multiple=True, type=(str, str), help="Tags for the instance in key=value format")
def create_ec2(instance_type, ami_id, key_name, security_group, count, tags):
    tags_dict = dict(tags)
    click.echo(click.style(f"\nStaging area: Creating {count} EC2 instance(s) with the following configuration:", fg="green"))
    click.echo(click.style(f"  Instance Type: {instance_type}", fg="green"))
    click.echo(click.style(f"  AMI ID: {ami_id}", fg="green"))
    click.echo(click.style(f"  Key Name: {key_name}", fg="green"))
    click.echo(click.style(f"  Security Group: {security_group}", fg="green"))
    click.echo(click.style(f"  Tags: {tags_dict}", fg="green"))
    
    if click.confirm(click.style("Do you want to proceed with creating the instance(s)?", fg="green"), default=True):
        version_id = str(uuid.uuid4())  # Generate a unique version ID
        comment = click.prompt(click.style("Enter a comment for this version", fg="green"))

        try:
            instances = create_ec2_instances(instance_type, ami_id, key_name, security_group, count, tags_dict)
            if instances is None:
                raise Exception("Instance creation failed. Aborting operation.")

            click.echo(click.style("Instances created successfully.", fg="green"))
            for idx, instance in enumerate(instances):
                click.echo(click.style(f"Instance {idx+1}: ID = {instance['InstanceId']}", fg="green"))

            if check_bucket_exists(VERSION_BUCKET_NAME):
                save_version_info_to_bucket(version_id, comment, instances)
            else:
                if click.confirm("Do you want to save the version information in a bucket?", default=False):
                    create_version_bucket()
                    save_version_info_to_bucket(version_id, comment, instances)
                else:
                    save_version_info_locally(version_id, comment, instances)
        except Exception as e:
            click.echo(click.style(f"Failed to create instances: {e}", fg="red"))
    else:
        click.echo(click.style("Instance creation aborted.", fg="yellow"))

@cli.command(name="create-ec2-dob", help="Create EC2 instances using dob-screenplay YAML file.")
@click.argument('dob_screenplay', type=click.Path(exists=True))
def create_ec2_dob(dob_screenplay):
    with open(dob_screenplay, 'r') as f:
        dob_content = yaml.safe_load(f)
    
    click.echo(click.style("\nStaging area: Creating EC2 instance(s) using dob-screenplay:", fg="green"))
    for idx, resource in enumerate(dob_content['resources']['ec2_instances']):
        click.echo(click.style(f"  Instance {idx+1}:", fg="green"))
        click.echo(click.style(f"    Instance Type: {resource['instance_type']}", fg="green"))
        click.echo(click.style(f"    AMI ID: {resource['ami_id']}", fg="green"))
        click.echo(click.style(f"    Key Name: {resource['key_name']}", fg="green"))
        click.echo(click.style(f"    Security Group: {resource['security_group']}", fg="green"))
        click.echo(click.style(f"    Count: {resource.get('count', 1)}", fg="green"))
        click.echo(click.style(f"    Tags: {resource.get('tags', {})}", fg="green"))
    
    if click.confirm(click.style("Do you want to proceed with creating the instance(s)?", fg="green"), default=True):
        version_id = str(uuid.uuid4())  # Generate a unique version ID
        comment = click.prompt(click.style("Enter a comment for this version", fg="green"))

        try:
            instances = []
            for resource in dob_content['resources']['ec2_instances']:
                instance_type = resource['instance_type']
                ami_id = resource['ami_id']
                key_name = resource['key_name']
                security_group = resource['security_group']
                count = resource.get('count', 1)
                tags = resource.get('tags', {})

                created_instances = create_ec2_instances(instance_type, ami_id, key_name, security_group, count, tags)
                if created_instances is None:
                    raise Exception("Instance creation failed. Aborting operation.")
                instances.extend(created_instances)

            click.echo(click.style("Instances created successfully.", fg="green"))
            for idx, instance in enumerate(instances):
                click.echo(click.style(f"Instance {idx+1}: ID = {instance['InstanceId']}", fg="green"))

            if check_bucket_exists(VERSION_BUCKET_NAME):
                save_version_info_to_bucket(version_id, comment, instances)
            else:
                if click.confirm("Do you want to save the version information in a bucket?", default=False):
                    create_version_bucket()
                    save_version_info_to_bucket(version_id, comment, instances)
                else:
                    save_version_info_locally(version_id, comment, instances)
        except Exception as e:
            click.echo(click.style(f"Failed to create instances: {e}", fg="red"))
    else:
        click.echo(click.style("Instance creation aborted.", fg="yellow"))



def create_version_bucket():
    credentials = load_aws_credentials()
    if not credentials:
        click.echo("No AWS credentials found. Please configure them first.")
        return None

    s3 = boto3.client('s3', **credentials)
    try:
        if click.confirm("Do you want to create a new bucket for version information?", default=True):
            s3.create_bucket(Bucket=VERSION_BUCKET_NAME)
            click.echo(f"S3 bucket '{VERSION_BUCKET_NAME}' created successfully.")
    except ClientError as e:
        click.echo(click.style(f"Failed to create S3 bucket: {e}", fg="red"))


@cli.command(name="view-version", help="View version information.")
def view_version():
    versions = list_versions_locally() + list_versions_in_bucket()
    if not versions:
        click.echo("No version information found.")
        return
    
    for version in versions:
        version_id = version['Key'].split('.enc')[0] if 'Key' in version else version.split('.enc')[0]
        version_info = load_version_info(version_id)
        if version_info:
            click.echo(click.style(f"Version ID: {version_info['version_id']}", fg="green"))
            click.echo(click.style(f"Comment: {version_info['comment']}", fg="green"))
            click.echo(click.style(json.dumps(version_info['content'], indent=2), fg="green"))
            click.echo('-' * 80)

if __name__ == '__main__':
    cli.add_command(configure_aws)
    cli.add_command(login)
    cli.add_command(create_ec2)
    cli.add_command(create_ec2_dob)
    cli.add_command(recreate_ec2)
    cli.add_command(view_version)
    cli()

