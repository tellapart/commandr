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
# Utilities for managing 'stacked' decorators used with commandr.
#

import functools

_UPDATE_WRAPPER_ORIGINAL = functools.update_wrapper

def update_wrapper(wrapper, wrapped, *args, **kwargs):
  """commandr version of functools.update_wrapper"""
  wrapper = _UPDATE_WRAPPER_ORIGINAL(wrapper, wrapped, *args, **kwargs)
  setattr(wrapper, '__wrapped__', wrapped)
  return wrapper

def wraps(wrapped, **kwargs):
  """commandr version of functools.wraps"""
  return functools.partial(update_wrapper, wrapped=wrapped, **kwargs)

def MonkeyPatchFunctools():
  """Monkey-patch the commandr version of update_wrapper into functools. This
  updates functools.update_wrapper and functools.wraps to support commandr
  stacked decorators.

  NOTE: This must be called _BEFORE_ any declarations using functools.wraps
      or functools.update_wrapper.
  """
  functools.update_wrapper = update_wrapper
