#!/bin/bash


### Depends module
yum -y groupinstall "Development Tools"
yum -y install gcc readline-devel zlib-devel bzip2-devel sqlite-devel openssl-devel


### pyenv
git clone https://github.com/yyuu/pyenv.git ~/.pyenv
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
. ~/.bashrc


### pyenv-virtualenv
git clone https://github.com/yyuu/pyenv-virtualenv.git ~/.pyenv/plugins/pyenv-virtualenv
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc
. ~/.bashrc

pyenv install 3.6.4
pyenv virtualenv 3.6.4 ec2_backup
pyenv local ec2_backup


# For current shell.
exec $SHELL -l
