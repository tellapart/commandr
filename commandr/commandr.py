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
# of the argument is True, the command line parameter a flag with "no-" in
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
#   def SayGreeting(name, title='Mr.', times=1, comma=False, caps_lock=False):
#     """Greet someone.
#
#     Arguments:
#       name - Name to greet.
#       title - Title of the person to greet.
#       times - Number of time to say the greeting.
#       comma - Whether to add a comma after the greeting.
#       caps_lock - Whether to output in ALL CAPS.
#     """
#     message = 'Hi%s %s %s!' % (',' if comma else '', title, name)
#     if caps_lock:
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
#   # 'caps_lock' doesn't have a short name because 'comma' came first.
#   # Equal signs are also optional.
#   $ python example.py greet --title Engineer -c --caps-lock Julie
#   HI, ENGINEER JULIE!
#
# There are several modes to handle arguments with underscores in the variable
# name.
# The mode can be set by calling:
#   SetOptionMode([<mode>, <mode>], hidden=False)
#
# The modes are:
# UNDERSCORE_MODE
# Options are accepted with underscores.
#
# DASH_MODE
# Options are accepted with dashes replacing underscores.
#
# DELETE_MODE
# Options are accepted with underscores deleted.
#
# If the hidden is True, only the first mode in the list set will displayed in
# the help text, while all forms will be accepted as arguments.
#
# If more than one mode is set, then partial arguments will result in a conflict
# error.  For example, if --caps is supplied for --caps-lock and --caps_lock, a
# conflict error will occur.

from collections import namedtuple
import inspect
from optparse import OptionParser, SUPPRESS_HELP
import sys

# Arguments with underscores get converted to dashes.
DASH_MODE = 'dash'
# Arguments with underscores stay underscores.
UNDERSCORE_MODE = 'underscore'
# Arguments with underscores will have the underscore deleted.
DELETE_MODE = 'delete'

COMMANDR = None

def GetCommandr():
  """Returns the global commandr object."""
  global COMMANDR
  if not COMMANDR:
    COMMANDR = Commandr()
  return COMMANDR

def command(*args, **kwargs):
  """Alias for commandr.command."""
  return GetCommandr().command(*args, **kwargs)

def Run(*args, **kwargs):
  """Alias for commandr.Run."""
  return GetCommandr().Run(*args, **kwargs)

def SetOptionModes(*args, **kwargs):
  """Alias for commandr.SetOptionModes."""
  return GetCommandr().SetOptionModes(*args, **kwargs)

class Commandr(object):
  """Class for managing commandr execution."""
  def __init__(self, modes=None, hidden=None):
    """Initializes a Commandr object.

    Args:
      modes - A list of modes to be set.
      hidden - If True, only the first mode will be displayed in help messages.
               If False, all modes will be displayed in the help messages in the
               order added.
    """
    self.modes = modes or [DASH_MODE, UNDERSCORE_MODE]
    self.hidden = hidden if hidden != None else True
    self.parser = None
    # Mapping of all command names to the respective command function.
    self._all_commands = {}
    # List of commands in the order they appeared, of the format:
    #   [(name, callable, category)]
    self._command_list = []
    self._command_info = namedtuple(
      '_COMMAND_INFO', ['name', 'callable', 'category'])

  def SetOptionModes(self, modes, hidden=None):
    """Sets which option styles are accepted.

    When an option has underscores, the underscores can be left alone, deleted or
    converted into dashes.

    Args:
      modes - A list of modes to be set.
      hidden - If True, only the first mode will be displayed in help messages.
               If False, all modes will be displayed in the help messages in the
               order added.
    """
    if hidden != None:
      self.hidden = hidden
    self.modes = modes

  def command(self, command_name, category=None):
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
      self._all_commands[command_name] = cmd_fn
      self._command_list.append(
        self._command_info(command_name, cmd_fn, category))
      return cmd_fn

    return command_decorator

  def Run(self):
    """Main function to take command line arguments, and parse them into a
    command to run, and the arguments to that command, and execute the command.
    """

    # Pull the command name from the first command line argument.
    if len(sys.argv) < 2:
      self._HelpExitNoCommand("Command must be specified")

    cmd_name = sys.argv[1]
    if cmd_name not in self._all_commands:
      self._HelpExitNoCommand("Unknown command '%s'" % cmd_name)

    # Get the command function from the registry.
    cmd_fn = self._all_commands[cmd_name]

    # Reflect the command function's arguments.
    argspec = inspect.getargspec(cmd_fn)

    # Populates defaults iff there is a default
    defaults_dict = {}
    if argspec.defaults:
      for i in xrange(1, len(argspec.defaults) + 1):
        defaults_dict[argspec.args[-i]] = argspec.defaults[-i]

    self._BuildOptParse(argspec, defaults_dict)

    (options, args) = self.parser.parse_args()
    options_dict = vars(options)

    # If help, print our message, else remove it so it doesn't confuse the
    # execution
    if options_dict['help']:
      self._HelpExitCommand(None, cmd_name, cmd_fn)
    elif 'help' in options_dict:
      del options_dict['help']

    # If desired, add args into the options_dict
    if len(args) > 1:
      skipped = 0
      for i, value in enumerate(args[1:]):
        if i + skipped >= len(argspec.args):
          self._HelpExitCommand("Too many arguments",
                                cmd_name, cmd_fn, options_dict, argspec.args)

        key = argspec.args[i + skipped]

        # If it's a boolean, skip assigning an arg to it.
        while key in defaults_dict and defaults_dict[key] in [True, False]:
          skipped += 1
          if i + skipped >= len(argspec.args):
            self._HelpExitCommand(
                "Too many arguments: True/False must be specified via switches",
                cmd_name, cmd_fn, options_dict, argspec.args)

          key = argspec.args[i + skipped]

        # Make sure the arg isn't already changed from the default.
        if (((key in defaults_dict and defaults_dict[key] != options_dict[key])
                or (key not in defaults_dict and options_dict[key] != None))
            and value != options_dict[key]):
          self._HelpExitCommand(
              "Repeated option: %s\nOption: %s\nArgument: %s" % (
                  key, options_dict[key], value),
              cmd_name, cmd_fn, options_dict, argspec.args)

        # cast specific types
        if key in defaults_dict:
          if isinstance(defaults_dict[key], int):
            value = int(value)
          elif isinstance(defaults_dict[key], float):
            value = float(value)

        # Update arg
        options_dict[key] = value

    for key, value in options_dict.iteritems():
      if value == None and key not in defaults_dict:
        self._HelpExitCommand(
            "All options without default values must be specified",
            cmd_name, cmd_fn, options_dict, argspec.args)

    result = cmd_fn(**options_dict)

    if result:
      print result

  def _BuildOptParse(self, argspec, defaults_dict):
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

    self.parser = OptionParser(usage=usage, add_help_option=False)

    self._AddOption(['-h', '--help'], dest='help', action='store_true',
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
          self._AddOption(args, dest=arg, action='store_true',
                      default=False)
        elif repr(defaults_dict[arg]) == 'True':
          self._AddOption(args, dest=arg, action='store_false',
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
          self._AddOption(args, dest=arg, default=defaults_dict[arg],
                           type=arg_type, help='[default: %s]' % (help_str))
      else:
        self._AddOption(args, dest=arg)

  def _AddOption(self, args, **kwargs):
    """Adds an option to the parser.

    This will manage converting underscores to dashes based off of the currently
    set OPTIONS_MODE.

    Args:
      args - List of arguments to add, where the last argument is the full
             argument.
      kwargs - Remaining arguments to be passed to parser.add_option.
    """
    if '_' in args[-1] and self.modes != [UNDERSCORE_MODE]:
      arg = args[-1]
      extras = args[:-1]
      alt_args = []
      args = []
      options = {DASH_MODE:arg.replace('_', '-'),
                 UNDERSCORE_MODE:arg,
                 DELETE_MODE:arg.replace('_', '')}
      for mode in self.modes:
        if mode not in options:
          raise ValueError('InvalidOptionMode', mode)

        if not args:
          args = extras + [options[mode]]
        elif not self.hidden:
          args.append(options[mode])
        else:
          alt_args.append(options[mode])

      if alt_args:
        alt_kwargs = kwargs.copy()
        alt_kwargs['help'] = SUPPRESS_HELP
        if 'default' in alt_kwargs:
          del alt_kwargs['default']
        self.parser.add_option(*alt_args, **alt_kwargs)
    self.parser.add_option(*args, **kwargs)

  def _HelpExitNoCommand(self, message):
    """Exit with a help message that is not specific to any command.

    Args:
      message - Error message explaining why the script exited.
    """
    # Emit the error message.
    print message
    print ''

    # Emit a list of registered commands.
    categories = [None] + [c.category for c in self._command_list]
    appear_order = [c.name for c in self._command_list]

    last_category = -1

    def _compare_commands(a, b):
      by_cat = cmp(categories.index(a.category), categories.index(b.category))
      by_order = cmp(appear_order.index(a.name), appear_order.index(b.name))
      return by_cat or by_order

    for command in sorted(self._command_list, _compare_commands):
      if command.category != last_category:
        print "%s Commands:" % (command.category or "General")
        last_category = command.category
      print "  %s" % command.name

    sys.exit(1)

  def _HelpExitCommand(self, message, cmd_name, cmd_fn,
                       options_dict=None, arglist=None):
    """Exit with a help message for a specific command.

    Args:
      message - Error message explaining why the script exited.
      cmd_name - String name of the chosen command.
      cmd_fn - The callable object of the chosen command.
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
    self.parser.print_help()

    sys.exit(2)
