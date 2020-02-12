#!/usr/bin/env python

import setuptools

setuptools.setup(
    name='pyawslambda-utils',
    py_modules=['pyawslambdautils'],
    entry_points={
        'distutils.commands': [
            ['aws_upload = pyawslambdautils.AwsLambdaUoload',
             'aws_publish = pyawslambdautils.AwsLambdaPublish']
        ]
    }
)
