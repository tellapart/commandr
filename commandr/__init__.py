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

__all__ = [
    'command',
    'Run',
    'SetOptions',
    'update_wrapper',
    'wraps',
    'MonkeyPatchFunctools']

# Export the global Commandr object methods.
from commandr import Commandr
_COMMANDR = Commandr()

command = _COMMANDR.command
Run = _COMMANDR.Run
SetOptions = _COMMANDR.SetOptions

# Export the decorator utils.
from functools_util import update_wrapper, wraps, MonkeyPatchFunctools
