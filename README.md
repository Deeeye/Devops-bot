# Devops-bot



Commands
Configure AWS Credentials
dob configure-aws --aws_access_key_id <your_access_key_id> --aws_secret_access_key <your_secret_access_key> --region <your_region>


Create EC2 Instances

dob create-ec2 --instance-type t2.micro --ami-id ami-0427090fd1714168b --key-name jenkins_key --security-group sg-04ac7dc75e1f54b3a --count 1 --tags key1=value1 key2=value2

Create EC2 Instances from YAML
dob create-ec2-dob <path_to_dob_screenplay.yaml>


Recreate EC2 Instances from Version ID
dob recreate-ec2 --version-id <version_id>

Delete EC2 Instances by IDs or Version ID
dob delete-ec2 <instance_id1> <instance_id2> ... [--version-id <version_id>]


List EC2 Instances
dob list-ec2


Create S3 Bucket
dob create-s3-bucket --bucket-name <bucket_name> --region <region>


Create S3 Buckets from YAML
dob create-s3-bucket-dob <path_to_dob_screenplay.yaml>


List S3 Buckets
dob list-s3


List Objects in an S3 Bucket
dob list-objects <bucket_name>

Delete an Object from an S3 Bucket
dob delete-object <bucket_name> <object_key>

Delete an S3 Bucket
dob delete-bucket <bucket_name>

View Version Information
dob view-version [-o table|wide]

Login to DevOps Bot
dob login
