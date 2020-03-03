
# pyawslambdautils

pyawslambdautils add setup.py support upload python source codes to AWS Lambda.

## Example

The most simple usage looks like this in setup.py:

```
setup(
    setup_requires=[
        'pyawslambdautils',
    ]
)
```

And add AWS Lambda configure in setup.cfg:

```
[tools:awslambda]
region=us-west-1
name=MyAWSLambda
testdata={"test": "payload"}
```

To upload source code to AWS Lambda

`./setup.py awsupload`

To publish a new version

`./setup.py awspublish`

To run a test in AWS Lambda

`./setup.py awstest`
