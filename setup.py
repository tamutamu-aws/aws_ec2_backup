from setuptools import setup


requires = ["boto3", "requests", "pytz"]

setup(
    name='aws_ec2_backup',
    version='0.1',
    description='aws_ec2_backup',
    url='https://github.com/tamutamu/aws_ec2_backup.git',
    author='tamutamu',
    author_email='tamutamu731@gmail.com',
    license='MIT',
    keywords='python3',
    packages=[
        "ec2_backup"
    ],
    install_requires=requires,
    classifiers=[
        'Programming Language :: Python :: 3.6',
    ],
)
