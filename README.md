
# pyawslambdautils

pyawslambdautils add setup.py support upload python source codes to AWS Lambda.

## Example

### Configure

Add pyawslambda-utils into your `setup.py`:

```
setup(
    setup_requires=[
        'pyawslambda-utils@git+https://github.com/yagami-cerberus/pyawslambda-utils.git',
    ]
)
```

Add AWS Lambda configure in setup.cfg:

```
[tools:awslambda]
# AWS Lambda runtime, can be py36, py37, py38
runtime=py38
# AWS Lambda region
region=us-west-1
# AWS Lambda name
name=MyAWSLambda
# Test data for aws lambda
testdata={"test": "payload"}

[tools:awslambda-layers]
py38_database=SQLAlchemy psycopg2_binary
py38_crypto_modules=pycryptodome python_jose rsa
```

# Commands

Upload source code to AWS Lambda named `MyAWSLambda` at region `us-west-1`

`./setup.py awsupload`

Publish a new version

`./setup.py awspublish`

Run a test in AWS Lambda

`./setup.py awstest`

Create lambda layer:

* Layer name `py38_database`, runtime `python3.8` with package `SQLAlchemy` and `psycopg2_binary`
* Layer name `py38_crypto_modules`, runtime `python3.8` with package `pycryptodome` `python_jose` `rsa`

`./setup.py awsbuildlayer`
