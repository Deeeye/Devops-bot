import os
import requests
import click
import uuid
import json
import time
import yaml
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from flask import Flask
from cryptography.fernet import Fernet
from datetime import datetime
from tabulate import tabulate

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

# Load AWS credentials and decrypt them
def load_aws_credentials():
    credentials = None
    try:
        if os.path.exists(AWS_CREDENTIALS_FILE):
            key = load_key()
            with open(AWS_CREDENTIALS_FILE, 'rb') as cred_file:
                encrypted_credentials = cred_file.read()
            decrypted_credentials = decrypt_data(encrypted_credentials, key)
            credentials = json.loads(decrypted_credentials)
    except FileNotFoundError:
        pass
    return credentials

def create_s3_bucket(bucket_name, region=None):
    try:
        credentials = load_aws_credentials()
        s3 = boto3.client(
            's3',
            aws_access_key_id=credentials['aws_access_key_id'],
            aws_secret_access_key=credentials['aws_secret_access_key'],
            region_name=region
        ) if credentials else boto3.client('s3', region_name=region)

        create_bucket_config = {'LocationConstraint': region} if region and region != 'us-east-1' else None
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration=create_bucket_config
        ) if create_bucket_config else s3.create_bucket(Bucket=bucket_name)

        click.echo(f"Bucket {bucket_name} created successfully in region {region}.")
        return True
    except (NoCredentialsError, PartialCredentialsError) as e:
        click.echo(f"Error with AWS credentials: {e}")
    except ClientError as e:
        click.echo(f"Error creating bucket: {e}")
    return False

@cli.command(name="create-s3-bucket", help="Create one or more S3 buckets.")
@click.argument('bucket_names', nargs=-1)
@click.option('--region', default=None, help='AWS region to create the bucket in.')
@click.option('--count', default=1, help='Number of buckets to create.')
def create_s3_bucket_cli(bucket_names, region, count):
    for bucket_name in bucket_names:
        for i in range(count):
            unique_bucket_name = f"{bucket_name}-{i}" if count > 1 else bucket_name
            if create_s3_bucket(unique_bucket_name, region):
                click.echo(click.style(f"Bucket {unique_bucket_name} created successfully.", fg="green"))
            else:
                click.echo(click.style(f"Failed to create bucket {unique_bucket_name}.", fg="red"))

@cli.command(name="create-s3-bucket-dob", help="Create S3 buckets using dob-screenplay YAML file.")
@click.argument('dob_screenplay', type=click.Path(exists=True))
def create_s3_bucket_dob(dob_screenplay):
    with open(dob_screenplay, 'r') as f:
        dob_content = yaml.safe_load(f)

    click.echo(click.style("\nStaging area: Creating S3 bucket(s) using dob-screenplay:", fg="green"))
    for idx, resource in enumerate(dob_content['resources']['s3_buckets']):
        data = [
            [click.style("+", fg="green"), "Bucket Name", resource['name']],
            [click.style("+", fg="green"), "Region", resource['region']]
        ]
        table = tabulate(data, headers=["", "Attribute", "Value"], tablefmt="grid")
        click.echo(table)

    if click.confirm(click.style("Do you want to proceed with creating the bucket(s)?", fg="green"), default=True):
        all_buckets_created = True
        for resource in dob_content['resources']['s3_buckets']:
            if not create_s3_bucket(resource['name'], resource['region']):
                all_buckets_created = False

        if all_buckets_created:
            click.echo(click.style("All buckets created successfully.", fg="green"))
        else:
            click.echo(click.style("Some buckets failed to create. Check the logs for details.", fg="red"))
    else:
        click.echo(click.style("Bucket creation aborted.", fg="yellow"))

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

# Delete instance
@cli.command(name="delete-ec2", help="Delete EC2 instances using instance IDs or a version ID.")
@click.argument('ids', nargs=-1)
@click.option('--version-id', help="Version ID to delete instances from")
def delete_ec2(ids, version_id):
    instance_ids = list(ids)

    if version_id:
        version_info = load_version_info(version_id)
        if not version_info:
            click.echo("No version information found.")
            return
        instance_ids.extend(instance['InstanceId'] for instance in version_info['content'])

    if not instance_ids:
        click.echo("No instance IDs provided.")
        return

    table_data = [
        [click.style("-", fg="red"), "Instance ID", instance_id] for instance_id in instance_ids
    ]
    click.echo(click.style("\nStaging area: Deleting EC2 instance(s) with IDs:", fg="red"))
    click.echo(tabulate(table_data, headers=["", "Attribute", "Value"], tablefmt="grid"))

    if click.confirm(click.style("Do you want to proceed with deleting the instance(s)?", fg="red"), default=False):
        comment = click.prompt(click.style("Enter a comment for this version", fg="red"))
        version_id = str(uuid.uuid4())  # Generate a unique version ID

        try:
            terminated_instances = delete_ec2_instances(instance_ids)
            if terminated_instances is None:
                raise Exception("Instance deletion failed. Aborting operation.")

            click.echo(click.style("Instances deleted successfully.", fg="green"))
            for idx, instance in enumerate(terminated_instances):
                click.echo(click.style(f"Instance {idx+1}: ID = {instance['InstanceId']} - {instance['CurrentState']['Name']}", fg="green"))

            version_content = [{'InstanceId': instance['InstanceId'], 'CurrentState': instance['CurrentState']} for instance in terminated_instances]
            
            if check_bucket_exists(VERSION_BUCKET_NAME):
                save_version_info_to_bucket(version_id, comment, version_content)
            else:
                if click.confirm("Do you want to save the version information in a bucket?", default=False):
                    create_version_bucket()
                    save_version_info_to_bucket(version_id, comment, version_content)
                else:
                    save_version_info_locally(version_id, comment, version_content)
        except Exception as e:
            click.echo(click.style(f"Failed to delete instances: {e}", fg="red"))
    else:
        click.echo(click.style("Instance deletion aborted.", fg="yellow"))

# Utility function for deleting EC2 instances
def delete_ec2_instances(instance_ids):
    credentials = load_aws_credentials()
    if not credentials:
        click.echo("No AWS credentials found. Please configure them first.")
        return None

    ec2 = boto3.client('ec2', **credentials)
    try:
        response = ec2.terminate_instances(InstanceIds=instance_ids)
        return response['TerminatingInstances']
    except ClientError as e:
        click.echo(click.style(f"Failed to delete instances: {e}", fg="red"))
        return None

# Assuming utility functions for encryption, AWS credential loading, version saving/loading are present

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

def create_ec2_instances(instance_type, ami_id, key_name, security_group, count, tags):
    credentials = load_aws_credentials()
    if not credentials:
        click.echo("No AWS credentials found. Please configure them first.")
        return None

    ec2 = boto3.client('ec2', **credentials)
    try:
        instances = ec2.run_instances(
            InstanceType=instance_type,
            ImageId=ami_id,
            KeyName=key_name,
            SecurityGroupIds=[security_group],
            MinCount=count,
            MaxCount=count,
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [{'Key': key, 'Value': value} for key, value in tags.items()]
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
@click.option('--tags', multiple=True, type=(str, str), help="Tags for the instance in key=value format", required=False)
def create_ec2(instance_type, ami_id, key_name, security_group, count, tags):
    tags_dict = dict(tags)
    table_data = [
        [click.style("+", fg="green"), "Instance Type", instance_type],
        [click.style("+", fg="green"), "AMI ID", ami_id],
        [click.style("+", fg="green"), "Key Name", key_name],
        [click.style("+", fg="green"), "Security Group", security_group],
        [click.style("+", fg="green"), "Count", count],
        [click.style("+", fg="green"), "Tags", tags_dict]
    ]
    click.echo(click.style("\nStaging area: Creating EC2 instance(s) with the following configuration:\n", fg="green"))
    click.echo(tabulate(table_data, headers=["", "Attribute", "Value"], tablefmt="grid"))

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

            version_content = [{'InstanceId': instance['InstanceId'], 'InstanceType': instance['InstanceType'], 'ImageId': instance['ImageId'], 'KeyName': instance['KeyName'], 'SecurityGroups': instance['SecurityGroups'], 'Tags': instance.get('Tags', [])} for instance in instances]

            if check_bucket_exists(VERSION_BUCKET_NAME):
                save_version_info_to_bucket(version_id, comment, version_content)
            else:
                if click.confirm("Do you want to save the version information in a bucket?", default=False):
                    create_version_bucket()
                    save_version_info_to_bucket(version_id, comment, version_content)
                else:
                    save_version_info_locally(version_id, comment, version_content)
        except Exception as e:
            click.echo(click.style(f"Failed to create instances: {e}", fg="red"))
    else:
        click.echo(click.style("Instance creation aborted.", fg="yellow"))

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

@cli.command(name="recreate-ec2", help="Recreate EC2 instances using a version ID.")
@click.option('--version-id', required=True, help="Version ID to recreate instances from")
def recreate_ec2(version_id):
    version_info = load_version_info(version_id)
    if not version_info:
        click.echo("No version information found.")
        return
    
    instances_to_recreate = version_info['content']
    
    click.echo(click.style(f"\nStaging area: Recreating EC2 instance(s):", fg="green"))
    table_data = []
    for idx, instance in enumerate(instances_to_recreate):
        table_data.append([click.style("+", fg="green"), "Instance Type", instance.get('InstanceType', 'Unknown')])
        table_data.append([click.style("+", fg="green"), "AMI ID", instance.get('ImageId', 'Unknown')])
        table_data.append([click.style("+", fg="green"), "Key Name", instance.get('KeyName', 'Unknown')])
        security_groups = instance.get('SecurityGroups', [])
        security_group_ids = [sg['GroupId'] for sg in security_groups] if security_groups else None
        table_data.append([click.style("+", fg="green"), "Security Group", security_group_ids if security_group_ids else 'None'])
        table_data.append([click.style("+", fg="green"), "Tags", instance.get('Tags', [])])
    click.echo(tabulate(table_data, headers=["", "Attribute", "Value"], tablefmt="grid"))
    
    if click.confirm(click.style("Do you want to proceed with recreating the instance(s)?", fg="green"), default=True):
        new_version_id = str(uuid.uuid4())
        comment = click.prompt(click.style("Enter a new comment for this version", fg="green"))

        try:
            recreated_instances = []
            for instance in instances_to_recreate:
                created_instances = create_ec2_instances(
                    instance_type=instance.get('InstanceType', 'Unknown'),
                    ami_id=instance.get('ImageId', 'Unknown'),
                    key_name=instance.get('KeyName', 'Unknown'),
                    security_group=security_group_ids[0] if security_group_ids else None,
                    count=1,
                    tags={tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                )
                if created_instances is None:
                    raise Exception("Instance recreation failed. Aborting operation.")
                recreated_instances.extend(created_instances)

            click.echo(click.style("Instances recreated successfully.", fg="green"))
            for idx, instance in enumerate(recreated_instances):
                click.echo(click.style(f"Instance {idx+1}: ID = {instance['InstanceId']}", fg="green"))

            if check_bucket_exists(VERSION_BUCKET_NAME):
                save_version_info_to_bucket(new_version_id, comment, recreated_instances)
            else:
                if click.confirm("Do you want to save the version information in a bucket?", default=False):
                    create_version_bucket()
                    save_version_info_to_bucket(new_version_id, comment, recreated_instances)
                else:
                    save_version_info_locally(new_version_id, comment, recreated_instances)
        except Exception as e:
            click.echo(click.style(f"Failed to recreate instances: {e}", fg="red"))
    else:
        click.echo(click.style("Instance recreation aborted.", fg="yellow"))


def list_versions():
    versions = []
    key = load_key()
    # Check local versions
    for file_name in os.listdir(VERSION_DIR):
        if file_name.endswith(".enc"):
            version_id = file_name.split(".")[0]
            version_info = load_version_info(version_id)
            if version_info:
                timestamp = datetime.fromtimestamp(os.path.getmtime(os.path.join(VERSION_DIR, f"{version_id}.enc"))).strftime('%Y-%m-%d %H:%M:%S')
                instance_count = len(version_info['content'])
                versions.append((version_id, version_info.get('comment', ''), timestamp, instance_count))
    # Check S3 versions
    credentials = load_aws_credentials()
    s3 = boto3.client('s3', **credentials)
    try:
        response = s3.list_objects_v2(Bucket=VERSION_BUCKET_NAME)
        for obj in response.get('Contents', []):
            version_id = obj['Key'].split(".")[0]
            version_info = load_version_info(version_id)
            if version_info:
                timestamp = obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
                instance_count = len(version_info['content'])
                versions.append((version_id, version_info.get('comment', ''), timestamp, instance_count))
    except ClientError as e:
        click.echo(click.style(f"Error listing versions in S3: {e}", fg="red"))
    return versions

@cli.command(name="view-version", help="View version information.")
@click.option('-o', '--output', type=click.Choice(['table', 'wide']), default='table', help="Output format")
def view_version(output):
    versions = list_versions()
    if output == 'table':
        table = [[version_id, comment, timestamp, count] for version_id, comment, timestamp, count in versions]
        headers = ["Version ID", "Comment", "Date", "Time", "Count"]
        click.echo(tabulate(table, headers, tablefmt="grid"))
    elif output == 'wide':
        for version_id, comment, timestamp, count in versions:
            version_info = load_version_info(version_id)
            click.echo(click.style(f"Version ID: {version_id}", fg="green"))
            click.echo(click.style(f"Comment: {comment}", fg="green"))
            click.echo(click.style(f"Timestamp: {timestamp}", fg="green"))
            click.echo(click.style(f"Count: {count}", fg="green"))
            click.echo(click.style(json.dumps(version_info['content'], indent=2), fg="green"))
            click.echo("-" * 80)

# List EC2 instances command
@cli.command(name="list-ec2", help="List EC2 instances in a table format.")
def list_ec2_instances():
    credentials = load_aws_credentials()
    ec2 = boto3.client('ec2', **credentials)
    try:
        response = ec2.describe_instances()
        instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_type = instance['InstanceType']
                key_name = instance.get('KeyName', '-')
                security_groups = ', '.join([sg['GroupId'] for sg in instance.get('SecurityGroups', [])])
                state = instance['State']['Name']
                state_symbol = {
                    'running': click.style('+', fg='green'),
                    'stopped': click.style('-', fg='red'),
                    'terminated': click.style('-', fg='yellow')
                }.get(state, state)
                launch_time = instance['LaunchTime'].strftime('%Y-%m-%d %H:%M:%S')
                tags = ', '.join([f"{tag['Key']}={tag['Value']}" for tag in instance.get('Tags', [])])
                instances.append([
                    state_symbol, instance_id, instance_type, key_name, security_groups,
                    launch_time, tags
                ])
        
        headers = ["State", "Instance ID", "Instance Type", "Key Name", "Security Groups", "Launch Time", "Tags"]
        click.echo(tabulate(instances, headers, tablefmt="grid"))
    except ClientError as e:
        click.echo(click.style(f"Failed to list instances: {e}", fg="red"))

# List S3 buckets command
@cli.command(name="list-s3", help="List S3 buckets in a table format.")
def list_s3_buckets():
    credentials = load_aws_credentials()
    s3 = boto3.client('s3', **credentials)
    try:
        response = s3.list_buckets()
        buckets = []
        for bucket in response['Buckets']:
            bucket_name = bucket['Name']
            creation_date = bucket['CreationDate'].strftime('%Y-%m-%d %H:%M:%S')
            try:
                encryption = s3.get_bucket_encryption(Bucket=bucket_name)
                enc_rules = encryption['ServerSideEncryptionConfiguration']['Rules']
                encryption_status = 'Enabled'
            except ClientError:
                encryption_status = 'None'
            
            try:
                object_count = s3.list_objects_v2(Bucket=bucket_name)['KeyCount']
            except ClientError:
                object_count = 'Unknown'
            
            buckets.append([
                bucket_name, creation_date, encryption_status, object_count
            ])
        
        headers = ["Bucket Name", "Creation Date", "Encryption", "Number of Objects"]
        click.echo(tabulate(buckets, headers, tablefmt="grid"))
    except ClientError as e:
        click.echo(click.style(f"Failed to list buckets: {e}", fg="red"))

# List objects in a specific S3 bucket command
@cli.command(name="list-objects", help="List objects in a specific S3 bucket in a table format.")
@click.argument('bucket_name')
def list_s3_objects(bucket_name):
    credentials = load_aws_credentials()
    s3 = boto3.client('s3', **credentials)
    try:
        response = s3.list_objects_v2(Bucket=bucket_name)
        if 'Contents' not in response:
            click.echo(click.style(f"No objects found in bucket {bucket_name}.", fg="yellow"))
            return

        objects = []
        for obj in response['Contents']:
            key = obj['Key']
            size = obj['Size']
            last_modified = obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
            storage_class = obj['StorageClass']
            objects.append([
                key, size, last_modified, storage_class
            ])

        headers = ["Object Key", "Size (Bytes)", "Last Modified", "Storage Class"]
        click.echo(tabulate(objects, headers, tablefmt="grid"))
    except ClientError as e:
        click.echo(click.style(f"Failed to list objects in bucket {bucket_name}: {e}", fg="red"))

@cli.command(name="delete-object", help="Delete an object from an S3 bucket.")
@click.argument('bucket_name')
@click.argument('object_key')
def delete_object(bucket_name, object_key):
    click.echo(click.style("Warning: This action is irreversible and you will not be able to recreate the object. No version information will be saved.", fg="red"))
    if click.confirm(click.style("Do you want to proceed with deleting the object?", fg="red"), default=False):
        comment = click.prompt(click.style("Enter a comment for this deletion", fg="red"))
        try:
            credentials = load_aws_credentials()
            s3 = boto3.client('s3', **credentials)
            s3.delete_object(Bucket=bucket_name, Key=object_key)
            click.echo(click.style(f"Object '{object_key}' deleted successfully from bucket '{bucket_name}'.", fg="green"))
        except ClientError as e:
            click.echo(click.style(f"Failed to delete object: {e}", fg="red"))
    else:
        click.echo(click.style("Object deletion aborted.", fg="yellow"))

@cli.command(name="delete-bucket", help="Delete an S3 bucket.")
@click.argument('bucket_name')
def delete_bucket(bucket_name):
    click.echo(click.style("Warning: This action is irreversible and you will not be able to recreate the bucket or its contents. No version information will be saved.", fg="red"))
    if click.confirm(click.style("Do you want to proceed with deleting the bucket?", fg="red"), default=False):
        try:
            credentials = load_aws_credentials()
            s3 = boto3.client('s3', **credentials)
            # Empty the bucket before deleting
            response = s3.list_objects_v2(Bucket=bucket_name)
            if 'Contents' in response:
                for obj in response['Contents']:
                    s3.delete_object(Bucket=bucket_name, Key=obj['Key'])
            s3.delete_bucket(Bucket=bucket_name)
            click.echo(click.style(f"Bucket '{bucket_name}' and all its contents deleted successfully.", fg="green"))
        except ClientError as e:
            click.echo(click.style(f"Failed to delete bucket: {e}", fg="red"))
    else:
        click.echo(click.style("Bucket deletion aborted.", fg="yellow"))

if __name__ == '__main__':
    cli.add_command(configure_aws)
    cli.add_command(login)
    cli.add_command(create_ec2)
    cli.add_command(create_ec2_dob)
    cli.add_command(recreate_ec2)
    cli.add_command(view_version)
    cli.add_command(delete_ec2)
    cli.add_command(delete_object)
    cli.add_command(delete_bucket)
    cli.add_command(list_ec2_instances)
    cli.add_command(list_s3_buckets)
    cli.add_command(list_s3_objects)
    cli.add_command(create_s3_bucket_cli)
    cli.add_command(create_s3_bucket_dob)

    cli()


