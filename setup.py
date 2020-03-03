#!/usr/bin/env python

import setuptools

setuptools.setup(
    name='pyawslambda-utils',
    version='1.0.0',
    py_modules=['pyawslambdautils'],
    setup_requires=['botocore'],
    entry_points={
        'distutils.commands': [
            'awsupload = pyawslambdautils:AwsLambdaUoload',
            'awspublish = pyawslambdautils:AwsLambdaPublish',
            'awstest = pyawslambdautils:AwsLambdaTest'
        ]
    }
)
