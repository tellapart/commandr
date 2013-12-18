# Copyright 2013 TellApart, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# =============================================================================
#
# setup.py for the commandr package.
#

from distutils.core import setup

setup(
    name='commandr',
    version='1.3.2',
    packages=['commandr'],
    author='Kevin Ballard',
    author_email='kevin@tellapart.com',
    url='http://pypi.python.org/pypi/commandr/',
    license='LICENSE',
    description='Tool to automatically build command line interfaces to functions')
