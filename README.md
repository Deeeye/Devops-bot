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


Staging area: Recreating EC2 instance(s):
+----+----------------+----------------------------------------------------------------------------+
|    | Attribute      | Value                                                                      |
+====+================+============================================================================+
| +  | Instance Type  | t2.micro                                                                   |
+----+----------------+----------------------------------------------------------------------------+
| +  | AMI ID         | ami-0427090fd1714168b                                                      |
+----+----------------+----------------------------------------------------------------------------+
| +  | Key Name       | jenkins_key                                                                |
+----+----------------+----------------------------------------------------------------------------+
| +  | Security Group | ['sg-04ac7dc75e1f54b3a']                                                   |
+----+----------------+----------------------------------------------------------------------------+
| +  | Tags           | [{'Key': 'Name', 'Value': 'test'}, {'Key': 'Environment', 'Value': 'Dev'}] |
+----+----------------+----------------------------------------------------------------------------+
Do you want to proceed with recreating the instance(s)? [Y/n]: y
Enter a new comment for this version: training version
Instances recreated successfully.
Instance 1: ID = i-08b069638414fefd2

root@devops-bot:~/devops_bot# dob recreate-ec2 --version-id 51dba69a-0fd1-434d-aa29-b2026e874baa

Staging area: Recreating EC2 instance(s):
+----+----------------+-------------------------------------------------------+
|    | Attribute      | Value                                                 |
+====+================+=======================================================+
| +  | Instance Type  | t2.micro                                              |
+----+----------------+-------------------------------------------------------+
| +  | AMI ID         | ami-0427090fd1714168b                                 |
+----+----------------+-------------------------------------------------------+
| +  | Key Name       | jenkins_key                                           |
+----+----------------+-------------------------------------------------------+
| +  | Security Group | ['sg-04ac7dc75e1f54b3a']                              |
+----+----------------+-------------------------------------------------------+
| +  | Tags           | [{'Key': 'Name=ansible', 'Value': 'Environment=Dev'}] |
+----+----------------+-------------------------------------------------------+
Do you want to proceed with recreating the instance(s)? [Y/n]: y
Enter a new comment for this version: dev env 2
Instances recreated successfully.
Instance 1: ID = i-0fad4881290a81ac5
Version information saved in S3 bucket with ID 35c6678d-f3ab-4a49-9076-533bf534d007.

root@devops-bot:~/devops_bot# dob view-version 
+--------------------------------------+------------------------------------+---------------------+--------+
| Version ID                           | Comment                            | Date                |   Time |
+======================================+====================================+=====================+========+
| 19f21de6-3aa5-4aea-9e68-e6219f23e237 | delete version is recreated agin   | 2024-07-25 08:56:10 |      1 |
+--------------------------------------+------------------------------------+---------------------+--------+
| 1dd3e4f3-bd14-44c7-a2e4-4becfeac1f71 | instance for my production server  | 2024-07-26 09:34:45 |      1 |
+--------------------------------------+------------------------------------+---------------------+--------+
| 361b8ccd-598d-42e4-bce8-48b17c1dedae | ansable vm                         | 2024-07-24 18:42:17 |      1 |
+--------------------------------------+------------------------------------+---------------------+--------+
| 36949d43-dc00-4fb9-b2d9-bcfde154383e | new version                        | 2024-07-25 09:55:23 |      1 |
+--------------------------------------+------------------------------------+---------------------+--------+
| 422b1cb6-5cdc-444c-a017-b49e8e429c9f | dev env                            | 2024-07-26 11:31:28 |      1 |
+--------------------------------------+------------------------------------+---------------------+--------+
| 51dba69a-0fd1-434d-aa29-b2026e874baa | trial for my ec2                   | 2024-07-24 19:12:04 |      1 |
+--------------------------------------+------------------------------------+---------------------+--------+
| 572c95e0-b625-4eaa-85b5-4da154b83851 | i just created for test            | 2024-07-24 18:38:02 |      1 |
+--------------------------------------+------------------------------------+---------------------+--------+
| 5eb32f4f-d195-497a-b41f-6be62244534f | new test version                   | 2024-07-25 09:46:46 |      1 |
+--------------------------------------+------------------------------------+---------------------+--------+
| 69d9dc46-2517-412a-b5ff-f0a86f812581 | dev instance that did not work     | 2024-07-25 08:26:10 |      1 |
+--------------------------------------+------------------------------------+---------------------+--------+
| 725e2aa7-31eb-442c-afb6-58833d602a7f | my                                 | 2024-07-24 20:20:47 |      1 |
+--------------------------------------+------------------------------------+---------------------+--------+
| 8308340d-0178-4e9f-8f21-dc53c5bb7fda | new recreation                     | 2024-07-26 10:49:38 |      0 |
+--------------------------------------+------------------------------------+---------------------+--------+
| 9cc3057f-1f99-473f-b8a4-78b979a21d01 | new version of recreation          | 2024-07-25 08:46:20 |      1 |
+--------------------------------------+------------------------------------+---------------------+--------+
| affbc034-a223-4f75-b75e-602f76386f94 | my devops                          | 2024-07-24 20:30:06 |      1 |
+--------------------------------------+------------------------------------+---------------------+--------+
| b82b4060-7a91-41fa-bbf0-fd0639c70779 | new version 2                      | 2024-07-25 09:33:14 |      1 |
+--------------------------------------+------------------------------------+---------------------+--------+
| c9d89cf3-0c6e-41f2-8971-fc4fb7e4086c | this instance is set for version 1 | 2024-07-25 08:11:43 |      1 |
+--------------------------------------+------------------------------------+---------------------+--------+
| d5ac4202-169c-47a7-9ac1-dffb2b96564d | production was finish              | 2024-07-26 10:32:21 |      1 |
+--------------------------------------+------------------------------------+---------------------+--------+
| dca53710-5848-41a6-9eba-e13245a75534 | version for production             | 2024-07-26 10:30:04 |      1 |
+--------------------------------------+------------------------------------+---------------------+--------+
| ffa4de59-e218-42bb-86d6-2d462f8e1541 | production server                  | 2024-07-26 10:28:18 |      1 |
+--------------------------------------+------------------------------------+---------------------+--------+


root@devops-bot:~/devops_bot# dob create-ec2 --instance-type t2.micro --ami-id ami-0427090fd1714168b --key-name jenkins_key --security-group sg-04ac7dc75e1f54b3a --count 1 --tags key1=value1 key2=value2

Staging area: Creating EC2 instance(s) with the following configuration:

+----+----------------+--------------------------------+
|    | Attribute      | Value                          |
+====+================+================================+
| +  | Instance Type  | t2.micro                       |
+----+----------------+--------------------------------+
| +  | AMI ID         | ami-0427090fd1714168b          |
+----+----------------+--------------------------------+
| +  | Key Name       | jenkins_key                    |
+----+----------------+--------------------------------+
| +  | Security Group | sg-04ac7dc75e1f54b3a           |
+----+----------------+--------------------------------+
| +  | Count          | 1                              |
+----+----------------+--------------------------------+
| +  | Tags           | {'key1=value1': 'key2=value2'} |
+----+----------------+--------------------------------+
Do you want to proceed with creating the instance(s)? [Y/n]: y
Enter a comment for this version: dev env
Instances created successfully.
Instance 1: ID = i-059204f25458ca64c
Version information saved in S3 bucket with ID 422b1cb6-5cdc-444c-a017-b49e8e429c9f.




