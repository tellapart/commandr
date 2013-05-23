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
# Tool for providing a simple and uniform command line interface to a set of
# functions. Decorated functions get registered as commands, whose signature is
# automatically converted to an OptionParser object, and run against the
# command line options. To use this tool, import the module, decorate functions
# that are to be exposed as commands, and call Run().
#
# Arguments are automatically converted to a type based on any default values
# in the function signature. All function arguments without a default value
# will be considered strings.
#
# If a default value is None, the None will be passed through as the default
# (i.e. when no value is specified), but will be considered a string when
# specified.
#
# If an argument can be of mixed types, the default should be a string and the
# value should be cast by the function.
#
# Booleans are treated specially. If the default value of an argument is
# False, the command line parameter is a simple switch. If the default value
# of the argument is True, the command line parameter a flag with "no_" in
# front of it.
#
# If there are extra command line arguments not specified as switches, those
# values will be applied to each function argument in order, skipping any
# function arguments with boolean defaults. To keep the interface cleaner,
# it's recommended to place boolean arguments at the end so that skipping is
# less likely to occur.
#
# Usage help is automatically generated based on the signature, and is
# augmented with the contents of the function's docstring.
#
# e.g., in example.py:
#
#   @command('greet')
#   def SayGreeting(name, title='Mr.', times=1, comma=False, capslock=False):
#     """Greet someone.
#
#     Arguments:
#       name - Name to greet.
#       title - Title of the person to greet.
#       times - Number of time to say the greeting.
#       comma - Whether to add a comma after the greeting.
#       capslock - Whether to output in ALL CAPS.
#     """
#     message = 'Hi%s %s %s!' % (',' if comma else '', title, name)
#     if capslock:
#       message = message.upper()
#
#     for _ in xrange(times):
#       print message
#
#   if __name__ == '__main__':
#     Run()
#
# The command can them be invoked on the command line with:
#   $ python example.py greet --name=John
#   Hi Mr. John!
#
#   # Invoke with short parameter names
#   $ python example.py greet -n=Nick -t=Dr. -c
#   Hi, Dr. Nick!
#
#   # Invoke with positional arguments
#   $ python example.py greet Smith Ms.
#   Hi Ms. Smith!
#
#   # Combined explicit and positional arguments. In this case, 'Julie' will
#   # match the first unspecified argument 'name'
#   # 'capslock' doesn't have a short name because 'comma' came first.
#   # Equal signs are also optional.
#   $ python example.py greet --title Engineer -c --capslock Julie
#   HI, ENGINEER JULIE!
#

from collections import namedtuple
import inspect
from optparse import OptionParser
import sys

# Mapping of all command names to the respective command function.
_ALL_COMMANDS = {}

# List of commands in the order they appeared, of the format:
#   [(name, callable, category)]
_COMMAND_INFO = namedtuple('_COMMAND_INFO', ['name', 'callable', 'category'])
_COMMAND_LIST = []

def command(command_name, category=None):
  """Decorator that marks a function as a 'command' which can be invoked with
  arguments from the command line. e.g.:

    @command('greet')
    def Hi(name, title='Mr.'):
      return 'Hi %s %s!' % (title, name)

  Can be invoked from the command line with:

    python something.py greet --name=Nick --title=Dr.

  If 'category' is specified, commands with the same category are grouped
  together when listing all available commands.
  """
  def command_decorator(cmd_fn):
    _ALL_COMMANDS[command_name] = cmd_fn
    _COMMAND_LIST.append(_COMMAND_INFO(command_name, cmd_fn, category))
    return cmd_fn

  return command_decorator

def Run():
  """Main function to take command line arguments, and parse them into a command
  to run, and the arguments to that command, and execute the command.
  """

  # Pull the command name from the first command line argument.
  if len(sys.argv) < 2:
    _HelpExitNoCommand("Command must be specified")

  cmd_name = sys.argv[1]
  if cmd_name not in _ALL_COMMANDS:
    _HelpExitNoCommand("Unknown command '%s'" % cmd_name)

  # Get the command function from the registry.
  cmd_fn = _ALL_COMMANDS[cmd_name]

  # Reflect the command function's arguments.
  argspec = inspect.getargspec(cmd_fn)

  # Populates defaults iff there is a default
  defaults_dict = {}
  if argspec.defaults:
    for i in xrange(1, len(argspec.defaults) + 1):
      defaults_dict[argspec.args[-i]] = argspec.defaults[-i]

  parser = _BuildOptParse(argspec, defaults_dict)

  (options, args) = parser.parse_args()
  options_dict = vars(options)

  # If help, print our message, else remove it so it doesn't confuse the
  # execution
  if options_dict['help']:
    _HelpExitCommand(None, cmd_name, cmd_fn, parser)
  elif 'help' in options_dict:
    del options_dict['help']

  # If desired, add args into the options_dict
  if len(args) > 1:
    skipped = 0
    for i, value in enumerate(args[1:]):
      if i + skipped >= len(argspec.args):
        _HelpExitCommand(
            "Too many arguments",
            cmd_name, cmd_fn, parser, options_dict, argspec.args)

      key = argspec.args[i + skipped]

      # If it's a boolean, skip assigning an arg to it.
      while key in defaults_dict and defaults_dict[key] in [True, False]:
        skipped += 1
        if i + skipped >= len(argspec.args):
          _HelpExitCommand(
              "Too many arguments: True/False must be specified via switches",
              cmd_name, cmd_fn, parser, options_dict, argspec.args)

        key = argspec.args[i + skipped]

      # Make sure the arg isn't already changed from the default.
      if (((key in defaults_dict and defaults_dict[key] != options_dict[key])
              or (key not in defaults_dict and options_dict[key] != None))
          and value != options_dict[key]):
        _HelpExitCommand(
            "Repeated option: %s\nOption: %s\nArgument: %s" % (
                key, options_dict[key], value),
            cmd_name, cmd_fn, parser, options_dict, argspec.args)

      # cast specific types
      if key in defaults_dict:
        if isinstance(defaults_dict, int):
          value = int(value)
        elif isinstance(defaults_dict, float):
          value = float(value)

      # Update arg
      options_dict[key] = value

  for key, value in options_dict.iteritems():
    if value == None and key not in defaults_dict:
      _HelpExitCommand(
          "All options without default values must be specified",
          cmd_name, cmd_fn, parser, options_dict, argspec.args)

  result = cmd_fn(**options_dict)

  if result:
    print result

def _BuildOptParse(argspec, defaults_dict):
  """Convert an ArgSpec object returned from inspect.getargsprc() into an
  OptionsParser object that can be used to convert and validate command line
  arguments to invoke the original function. Default values are pulled from
  the function definition if present in defaults_dict. All non-defaulted
  arguments must be specific on the command line.

  Args:
    argspec - ArgSpec object returned from inspect.getargspec() on the chosen
        command function.
    default_dict - If provided, defaults will be pulled from the dict instead
        of the argspec.

  Returns:
    A populated OptionParser object.
  """
  usage = 'Usage: %prog command [options]\n' + \
      'Options without default values MUST be specified'

  parser = OptionParser(usage=usage, add_help_option=False)

  parser.add_option('-h', '--help', dest='help', action='store_true',
                    default=False)

  # Parse the command function's arguments into the OptionsParser.
  letters = set(['h']) # -h is for help

  for arg in argspec.args:
    argname = arg
    # If the default is True, make the argument a negative
    if arg in defaults_dict and repr(defaults_dict[arg]) == 'True':
      argname = 'no_%s' % argname
    args = ['--%s' % argname]
    if argname[0] not in letters and argname[0] not in argspec.args:
      args.insert(0, '-%s' % argname[0])
      letters.add(argname[0])

    if arg in defaults_dict:
      if repr(defaults_dict[arg]) == 'False':
        parser.add_option(*args, dest=arg, action='store_true',
                           default=False)
      elif repr(defaults_dict[arg]) == 'True':
        parser.add_option(*args, dest=arg, action='store_false',
                           default=True)
      else:
        if isinstance(defaults_dict[arg], int):
          arg_type = 'int'
          help_str = '%default'
        elif isinstance(defaults_dict[arg], float):
          arg_type = 'float'
          help_str = '%default'
        elif defaults_dict[arg] == None:
          arg_type = 'string'
          help_str = 'None'
        else:
          arg_type = 'string'
          help_str = '"%default"'
        parser.add_option(*args, dest=arg, default=defaults_dict[arg],
                           type=arg_type, help='[default: %s]' % (help_str))
    else:
      parser.add_option(*args, dest=arg)
  return parser

def _HelpExitNoCommand(message):
  """Exit with a help message that is not specific to any command.

  Args:
    message - Error message explaining why the script exited.
  """
  # Emit the error message.
  print message
  print ''

  # Emit a list of registered commands.
  categories = [None] + [c.category for c in _COMMAND_LIST]
  appear_order = [c.name for c in _COMMAND_LIST]

  last_category = -1

  def _compare_commands(a, b):
    by_cat = cmp(categories.index(a.category), categories.index(b.category))
    by_order = cmp(appear_order.index(a.name), appear_order.index(b.name))
    return by_cat or by_order

  for command in sorted(_COMMAND_LIST, _compare_commands):
    if command.category != last_category:
      print "%s Commands:" % (command.category or "General")
      last_category = command.category
    print "  %s" % command.name

  sys.exit(1)

def _HelpExitCommand(
    message, cmd_name, cmd_fn, parser, options_dict=None, arglist=None):
  """Exit with a help message for a specific command.

  Args:
    message - Error message explaining why the script exited.
    cmd_name - String name of the chosen command.
    cmd_fn - The callable object of the chosen command.
    parser - The OptionsParser object built for the chosen command.
    options_dict - If specified, it will the current state of the options.
    arglist - Optional order of the printed options.
  """
  # Emit the error message.
  if message:
    print message
    print ''

  if options_dict:
    if not arglist:
      arglist = sorted(options_dict.keys())
    print "Current Options:"
    for arg in arglist:
      print " --%s=%s" % (arg, options_dict[arg])
    print ""

  # Emit the documentation for the command.
  if cmd_fn.__doc__:
    print "Documentation for command '%s':" % cmd_name
    print "-" * 40
    print cmd_fn.__doc__
    print "-" * 40

  else:
    print "No documentation for command '%s'." % cmd_name

  print ''

  # Emit the documentation for the parser.
  parser.print_help()

  sys.exit(2)
