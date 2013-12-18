#!/usr/bin/python
#
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
"""Example usage of commandr."""

from commandr import command, Run, CommandrUsageError, wraps

@command('greet')
def SayGreeting(name, title='Mr.', times=1, comma=False, caps_lock=False):
  """Greet someone.

  Arguments:
    name - Name to greet.
    title - Title of the person to greet.
    times - Number of time to say the greeting.
    comma - Whether to add a comma after the greeting.
    caps_lock - Whether to output in ALL CAPS.
  """
  message = 'Hi%s %s %s!' % (',' if comma else '', title, name)
  if caps_lock:
    message = message.upper()

  for _ in xrange(times):
    print message

@command
def simple_greet(name):
  """An example of @command without arguments and printing Usage.

  Arguments:
    name - Name to greet.
  """
  if name == 'John':
    raise CommandrUsageError("John is not a valid name.")
  print 'Hi %s!' % name

@command()
def another_simple_greet(name):
  """An example of @command() without arguments.

  Arguments:
    name - Name to greet.
  """
  print 'Aloha %s!' % name

def some_decorator(fn):
  @wraps(fn)
  def _wrapper(*args, **kwargs):
    print 'Wrapper Here!'
    return fn(*args, **kwargs)
  return _wrapper

@command('test_decorated')
@some_decorator
def DecoratedFunction(arg1, arg2=1):
    """An example usage of stacked decorators."""
    print arg1, arg2

if __name__ == '__main__':
  Run(hyphenate=True)
