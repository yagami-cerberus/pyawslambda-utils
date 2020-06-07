
from botocore.session import Session
from distutils.core import Command
from subprocess import Popen, PIPE
from time import sleep
import shutil
import os


class AwsLambdaAbstractCommand(Command):
    user_options = []

    def initialize_options(self):
        options = self.distribution.get_option_dict('tools:awslambda')
        self.region = options['region'][1] if 'region' in options else None
        self.name = options['name'][1] if 'name' in options else None

    def finalize_options(self):
        if self.region is None:
            raise Exception('Parameter region is missing')
        if self.name is None:
            raise Exception('Parameter name is missing')


class AwsLambdaUpload(AwsLambdaAbstractCommand):
    description = 'Upload aws lambda function packages'

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
        self.make_archive(zip_filename[:-4], 'zip', None, '.')

        print('Uploading...')
        client = Session().create_client('lambda', region_name=self.region)
        with open(zip_filename, 'rb') as f:
            buf = f.read()
        ret = client.update_function_code(FunctionName=self.name, ZipFile=buf)
        revision_id = ret['RevisionId']
        print(' >> RevisionId: %s' % revision_id)
        print(' >> CodeSha256: %s' % ret['CodeSha256'])

        for i in range(20):
            info_ret = client.get_function(FunctionName=self.name)
            if info_ret['Configuration']['RevisionId'] == revision_id:
                break
            else:
                sleep(0.2)
        else:
            raise RuntimeError('Wait amz apply the code timeout')


class AwsLambdaPublish(AwsLambdaAbstractCommand):
    description = 'Publish aws lambda function version'

    def run(self):
        proc = Popen(('git', 'diff-index', '--quiet', '--ignore-submodules', 'HEAD'))
        if proc.wait() != 0:
            raise RuntimeError('Repo is dirty')

        proc = Popen(('git', 'log', '-1', '--pretty=format:%h'), stdout=PIPE)
        rev = proc.communicate()[0].decode().rstrip('\n')

        proc = Popen(('git', 'rev-parse', '--abbrev-ref', 'HEAD'), stdout=PIPE)
        branch = proc.communicate()[0].decode().rstrip('\n')

        client = Session().create_client('lambda', region_name=self.region)
        ret = client.publish_version(FunctionName=self.name, Description='%s (%s)' % (rev, branch))
        print('\nVersion %r published (Description=%s)' % (ret['Version'], ret['Description']))


class AwsLambdaTest(AwsLambdaAbstractCommand):
    description = 'Test aws lambda function'

    def initialize_options(self):
        super().initialize_options()
        options = self.distribution.get_option_dict('tools:awslambda')
        self.testdata = options['testdata'][1] if 'testdata' in options else None

    def finalize_options(self):
        super().finalize_options()
        if self.testdata is None:
            raise Exception('Parameter testdata is missing')

    def run(self):
        print('Running test...')
        client = Session().create_client('lambda', region_name=self.region)
        ret = client.invoke(FunctionName=self.name, InvocationType='RequestResponse', Payload=self.testdata.encode())
        print('HTTP Status Code: %s' % ret['ResponseMetadata']['HTTPStatusCode'])
        print(ret['Payload'].read())


class AwsLambdaLayerBuilder(AwsLambdaAbstractCommand):
    DOCKERFILE = '''
FROM %(DOCKER_IMAGE_FROM)s AS build-stage
RUN pip install --upgrade pip

%(DOCKERFILE_PACKAGES_CMDS)s

FROM scratch AS export-stage
COPY --from=build-stage /tmp /
'''

    DOCKERFILE_PACKAGES_CMD = '''
RUN mkdir /tmp/%(PKG_NAME)s
RUN mkdir /tmp/%(PKG_NAME)s/python
RUN pip3 install -t /tmp/%(PKG_NAME)s/python %(PACKAGES)s
RUN cd /tmp/%(PKG_NAME)s/python && python3 -c 'import os; print(",".join(sorted([dir[:-10] for dir in os.listdir("/tmp/%(PKG_NAME)s/python") if dir.endswith(".dist-info")])))' > /tmp/%(PKG_NAME)s.txt && rm -rf bin *.dist-info
'''

    PY_VER = {
        'py36': {'DOCKER_IMAGE_FROM': 'python:3.6', 'RUNTIME': 'python3.6'},
        'py37': {'DOCKER_IMAGE_FROM': 'python:3.7', 'RUNTIME': 'python3.7'},
        'py38': {'DOCKER_IMAGE_FROM': 'python:3.8', 'RUNTIME': 'python3.8'},
    }

    def initialize_options(self):
        super().initialize_options()
        self.build_params = None
        self.layers = None

    def finalize_options(self):
        super().finalize_options()
        lambda_options = self.distribution.get_option_dict('tools:awslambda')

        if 'runtime' not in lambda_options:
            raise Exception('Parameter pyver is missing')
        elif lambda_options['runtime'][1] not in self.PY_VER:
            raise Exception('Parameter pyver is must be %s' % ', '.join(self.PY_VER.keys()))
        else:
            self.build_params = self.PY_VER[lambda_options['runtime'][1]].copy()

        lambda_layers = self.distribution.get_option_dict('tools:awslambda-layers')
        self.layers = [(layername, info[1]) for layername, info in lambda_layers.items()]

    def create_dockerfile(self):
        build_cmds = '\n'.join(
            self.DOCKERFILE_PACKAGES_CMD % {
                'PKG_NAME': layername,
                'PACKAGES': packages,
            }
            for layername, packages in self.layers
        )
        return self.DOCKERFILE % {
            'DOCKER_IMAGE_FROM': self.build_params['DOCKER_IMAGE_FROM'],
            'DOCKERFILE_PACKAGES_CMDS': build_cmds
        }

    def run(self):
        root_path = os.path.abspath('.')
        package_path = os.path.join(root_path, 'dist', 'awslambdalayers')
        if os.path.exists(package_path):
            shutil.rmtree(package_path)
        os.makedirs(package_path)

        os.environ['DOCKER_BUILDKIT'] = '1'

        proc = Popen(('docker', 'build', '--output', package_path, '-'), stdin=PIPE)
        proc.communicate(self.create_dockerfile().encode())

        if proc.returncode != 0:
            raise RuntimeError('build return %s' % proc.returncode)

        client = Session().create_client('lambda', region_name=self.region)
        arns = []

        for layername, packages in self.layers:
            zip_filename = os.path.join(package_path, f'{layername}.zip')
            os.chdir(os.path.join(package_path, layername))
            self.make_archive(zip_filename[:-4], 'zip', None, '.')
            with open(os.path.join(package_path, f'{layername}.txt'), 'r') as f:
                description = f.read()
            with open(os.path.join(package_path, f'{layername}.zip'), 'rb') as f:
                zipbuf = f.read()

            print(f'Uploading {layername} ...')
            ret = client.publish_layer_version(
                LayerName=layername,
                Description=description,
                Content={'ZipFile': zipbuf},
                CompatibleRuntimes=[self.build_params['RUNTIME']]
            )
            arns.append(ret.get('LayerArn'))
        for arn in arns:
            print(f'Layer created for {arn}')
