
from botocore.session import Session
from distutils.cmd import Command
from subprocess import Popen, PIPE
import shutil
import os


class AwsLambdaAbstractCommand(Command):
    user_options = [
        ('region=', None, 'AWS Region'),
        ('name=', None, 'AWS Lambda Name'),
    ]

    def initialize_options(self):
        self.region = None
        self.name = None

    def finalize_options(self):
        if self.region is None:
            raise Exception('Parameter --region is missing')
        if self.name is None:
            raise Exception('Parameter --name is missing')


class AwsLambdaUoload(AwsLambdaAbstractCommand):
    description = 'Upload aws lambda packages'

    def run(self):
        root_path = os.path.abspath('.')
        package_path = os.path.join(root_path, 'dist', 'aws_package')
        if os.path.exists(package_path):
            shutil.rmtree(package_path)
        os.makedirs(package_path)

        proc = Popen(('pip3', 'install', '--no-deps', '-t', package_path, '.'))
        proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError('pip3 return %s' % proc.returncode)

        os.chdir(package_path)
        for item in os.listdir('.'):
            if item.endswith('.egg-info') or item.endswith('.dist-info'):
                shutil.rmtree(os.path.join(package_path, item))
        zip_filename = os.path.join(root_path, 'dist', 'aws_package.zip')
        shutil.make_archive(zip_filename[:-4], 'zip', None, '.')

        print('Uploading...')
        client = Session().create_client('lambda', region_name=self.region)
        with open(zip_filename, 'rb') as f:
            client.update_function_code(FunctionName=self.name, ZipFile=f.read())
        # sleep(1)
        # print('Running test...')
        # ret = client.invoke(FunctionName=self.name, InvocationType='RequestResponse', Payload=b'{"basicTest": true}')
        # print('HTTP Status Code: %s' % ret['ResponseMetadata']['HTTPStatusCode'])
        # print(ret['Payload'].read())


class AwsLambdaPublish(AwsLambdaAbstractCommand):
    description = 'Publish aws lambda version'

    def run(self):
        proc = Popen(('git', 'diff-index', '--cached', '--quiet', '--ignore-submodules', 'HEAD'))
        if proc.wait() != 0:
            raise RuntimeError('Repo is not clean, some file is stashed.')
        proc = Popen(('git', 'diff-index', '--quiet', '--ignore-submodules', 'HEAD'))
        if proc.wait() != 0:
            raise RuntimeError('Repo is not clean')

        proc = Popen(('git', 'rev-parse', '--short', 'HEAD'), stdout=PIPE)
        rev = proc.communicate()[0].decode().rstrip('\n')

        proc = Popen(('git', 'rev-parse', '--abbrev-ref', 'HEAD'), stdout=PIPE)
        branch = proc.communicate()[0].decode().rstrip('\n')

        client = Session().create_client('lambda', region_name=self.region)
        ret = client.publish_version(FunctionName=self.name, Description='%s (%s)' % (rev, branch))
        print('\nVersion %r published (Description=%s)' % (ret['Version'], ret['Description']))
