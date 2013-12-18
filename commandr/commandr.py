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
#   # 'caps_lock' is capital 'C' because 'comma' came first.  If a third argument
#   # started with 'c', it would have no short option.
#   # Equal signs are also optional.
#   $ python example.py greet --title Engineer -c -C Julie
#   HI, ENGINEER JULIE!
#
# There are several options that affect the form of the generated parser. The
# options can be set by calling:
#   SetOptions(hyphenate=<bool>, show_all_help_variants=<bool>)
#
# All options can also be set as arguments to Run(). Values set in that way
# will take precedence.
#
# hyphenate:
#   If True (default), then any argument containing an underscore ('_') will be
#   parsable with dashes ('-') in their place (both variants will be allowed).
#   If False, then only the original argument name will be accepted.
#
#   Note that if hyphenate is enabled, partial arguments will result in a
#   conflict error. For example, if --caps is supplied for --caps-lock and
#   --caps_lock, a conflict error will occur.
#
# show_all_help_variants:
#   If False (default), then only one argument name variant will be displayed
#   in the help text (all forms will remain accepted as arguments).
#   Specifically, when hyphenate is True, only the hyphenated variant will be
#   displayed in the help text.
#
# ignore_self:
#   If True, arguments named "self" will be ignored when building the parser
#   for functions. This is useful when using member functions as commands.
#   Default is False.
#
# main_docs:
#   If True, __main__.__doc__ and __main__.__copyright__ will be printed if
#   the command is run with no command or help. Default is True.
#
# main:
#   If set, Commandr will use the supplied value as the command name to run
#   if no command name is supplied.  It will override any previous values.

from collections import namedtuple
import inspect
import itertools
from optparse import OptionParser, SUPPRESS_HELP
import sys

class CommandInfo(
  namedtuple('BaseCommandInfo',
             ['name', 'callable', 'category', 'ignore_self'])):
  """Class to contain information about a spepcific supported command."""
  def __new__(cls, name=None, callable=None, category=None, ignore_self=None):
    """Creates a new CommandInfo allowing for default values.

    Args:
      name - Name of the command.
      callable - Callable function of the command.
      category - Category classification of the command.
      ignore_self - Whether the arg list should ignore the first value if it is
                    self.
    Returns:
      info - A CommandInfo.
    """
    return super(CommandInfo, cls).__new__(cls, name, callable, category,
                                           ignore_self)

class Commandr(object):
  """Class for managing commandr context."""

  def __init__(self):
    """Initializes a Commmandr Object """
    self.hyphenate = True
    self.hidden = True
    self.ignore_self = False
    self.main_docs = True
    self.main = None

    # Internal flag indicating whether to expect the command name as the first
    # command line argument.
    self.no_command_arg = True

    # Mapping of all command names to the respective command function.
    self.parser = None
    self._all_commands = {}
    self.current_command = None

    # List of commands in the order they appeared, of the format:
    #   [(name, callable, category)]
    self._command_list = []

    self.command('help', ignore_self=True)(self._HelpExitNoCommand)

  def command(self, command_name=None, category=None, main=False,
              ignore_self=None):
    """Decorator that marks a function as a 'command' which can be invoked with
    arguments from the command line. e.g.:

      @command('greet')
      def Hi(name, title='Mr.'):
        return 'Hi %s %s!' % (title, name)

    Can be invoked from the command line with:

      python something.py greet --name=Nick --title=Dr.

    Args:
      command_name - Name the command is called on the command line. Default is
        the name of the function.
      category - Group to list the command under on help.  Default is General.
      main - If True, this command will be set to run if no commands are
        specified.  An Exception will be thrown if two commands are set to be
        main.
      ignore_self - If True or False, it will apply the ignore_self option for
        this command, while others use the global default.
    Returns:
      decorator/function to register the command.
    """
    def command_decorator(cmd_fn, cmd_fn_name=None):
      info = self.AddCommand(cmd_fn, cmd_fn_name or command_name, category,
                             ignore_self)
      if main:
        if not self.main:
          self.main = info.name
        else:
          raise CommandrDuplicateMainError("'%s' tried to override '%s'" % (
              info.name, self._main_command))
      return cmd_fn

    # Handle no command_name case.
    if callable(command_name):
      cmd_func = command_name
      return command_decorator(cmd_func, cmd_func.func_name)

    return command_decorator

  def AddCommand(self, cmd_fn, cmd_fn_name, category, ignore_self):
    """Adds a command to the commandr list.

    Args:
      cmd_fn - The function to add.
      cmd_fn_name - The name of the command being added or the func_name.
      category - The category of the command.
      ignore_self - Whether to ignore self in the arg list.
    Returns:
      info - The CommandInfo created.
    """
    final_name = (cmd_fn_name if cmd_fn_name is not None
                  else cmd_fn.func_name)
    info = CommandInfo(final_name, cmd_fn, category, ignore_self)
    self._all_commands[info.name] = info
    self._command_list.append(info)
    return info

  def SetOptions(self,
      hyphenate=None,
      show_all_help_variants=None,
      ignore_self=None,
      main_docs=None,
      main=None):
    """Set commandr options. Any argument not set to None will be applied
    (otherwise it will retain its current value).

    Args:
      hyphenate - If True, underscores in argument names will be converted to
          hyphens (both variants will be acceptable inputs).
      show_all_help_variants - If hyphenate is True and show_all_help_variants
          is False, then only the hyphenated version of applicable arguments
          will be shown in the help text (although both variants will be
          acceptable inputs).
      ignore_self - If True, arguments named "self" will be ignored when
          building the parser for functions. This is useful when using member
          functions as commands. Default is False.
      main_docs - If True, the __doc__ from __main__ will be printed when no
          command is specified.  Default is True.
      main - If set, it will use the supplied value as the command name to run
          if no command name is supplied.  It will override any previous values.
    """
    # Anything added here should also be added to the RunFunction interface.
    if hyphenate is not None:
      self.hyphenate = bool(hyphenate)
    if show_all_help_variants is not None:
      self.hidden = not bool(show_all_help_variants)
    if ignore_self is not None:
      self.ignore_self = ignore_self
    if main_docs is not None:
      self.main_docs = main_docs
    if main is not None:
      self.main = main

  def Run(self, *args, **kwargs):
    """Main function to take command line arguments, and parse them into a
    command to run, and the arguments to that command, and execute the command.

    Args:
     All args are passed to SetOptions.  See SetOptions for detials.
    """
    self.SetOptions(*args, **kwargs)

    # Pull the command name from the first command line argument.
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
      if self.main is not None:
        sys.argv.insert(1, self.main)
        cmd_name = self.main
      elif (len(sys.argv) in [2, 3]
          and sys.argv[1] == '--list_command_completions'):
        self._CompletionAllCommands(sys.argv[2] if len(sys.argv) > 2 else '')
      else:
        cmd_name = None
    else:
      cmd_name = sys.argv[1]

    if cmd_name not in self._all_commands:
      if cmd_name:
        message = "Unknown command '%s'" % cmd_name
      else:
        message = "A command must be specified."

      self._HelpExitNoCommand(message=message)

    # Get the command function from the registry.
    cmd_fn = self._all_commands[cmd_name].callable

    self.no_command_arg = False
    return self.RunFunction(cmd_fn, cmd_name)

  def RunFunction(self,
      cmd_fn,
      cmd_name=None,
      hyphenate=None,
      show_all_help_variants=None,
      ignore_self=None,
      main_doc=None,
      main=None):
    """Method to explicitly execute a given function against the command line
    arguments. If this method is called directly, the command name will not be
    expected in the arguments.

    Args:
      cmd_fn - Callable to inspect, apply command line arguments, and execute.
      cmd_name - String name of the command.
      hyphenate - If not None, set the hyphenate option to this value (see
          SetOptions for details)
      show_all_help_variants - If not None, set the show_all_help_variants
          option to this value (see SetOptions for details).
      ignore_self - If not None, set the ignore_self option to this value (see
          SetOptions for details).
      main_docs - If True, the __doc__ from __main__ will be printed when no
          command is specified.  Default is True.
      main - If set, it will use the supplied value as the command name to run
          if no command name is supplied.  It will override any previous values.
    """
    info = self._all_commands.get(cmd_name)
    if not info:
      info = self.AddCommand(cmd_fn, cmd_name, None, ignore_self)

    self.SetOptions(hyphenate, show_all_help_variants, ignore_self, main_doc,
                    main)

    argspec, defaults_dict = self._BuildOptParse(info)

    (options, args) = self.parser.parse_args()

    options_dict = vars(options)

    # If help, print our message, else remove it so it doesn't confuse the
    # execution
    if options_dict['help']:
      self._HelpExitCommand(None, info.name, info.callable)
    elif 'help' in options_dict:
      del options_dict['help']

    ignore = (info.ignore_self
              if info.ignore_self is not None
              else self.ignore_self)

    # If desired, add args into the options_dict
    args_to_parse = args[1:] if not self.no_command_arg else args
    if len(args_to_parse) > 0:
      skipped = 0

      for i, value in enumerate(args_to_parse):
        while True:
          if i + skipped >= len(argspec.args):
            self._HelpExitCommand("Too many arguments",
                                  info.name, info.callable, options_dict, argspec.args)
          key = argspec.args[i + skipped]
          if ignore and key == 'self':
            skipped += 1
            continue
          break

        # If it's a boolean, skip assigning an arg to it.
        while key in defaults_dict and defaults_dict[key] in [True, False]:
          skipped += 1
          if i + skipped >= len(argspec.args):
            self._HelpExitCommand(
                "Too many arguments: True/False must be specified via switches",
                info.name, info.callable, options_dict, argspec.args)

          key = argspec.args[i + skipped]

        # Make sure the arg isn't already changed from the default.
        if (((key in defaults_dict and defaults_dict[key] != options_dict[key])
             or (key not in defaults_dict and options_dict[key] is not None))
            and value != options_dict[key]
            and not isinstance(defaults_dict[key], list)):
          self._HelpExitCommand(
              "Repeated option: %s\nOption: %s\nArgument: %s" % (
                  key, options_dict[key], value),
              info.name, info.callable, options_dict, argspec.args)

        # cast specific types
        if key in defaults_dict:
          if isinstance(defaults_dict[key], int):
            value = int(value)
          elif isinstance(defaults_dict[key], float):
            value = float(value)
          elif  isinstance(defaults_dict[key], list):
            if options_dict[key] is None:
              value = [value]
            else:
              value = options_dict[key] + [value]
        # Update arg
        options_dict[key] = value

    for key, value in options_dict.iteritems():
      if value is None:
        if key not in defaults_dict:
          self._HelpExitCommand(
            "All options without default values must be specified",
            info.name, info.callable, options_dict, argspec.args)
        elif defaults_dict[key] is not None:
          options_dict[key] = defaults_dict[key]

    self.current_command = info
    try:
      result = info.callable(**options_dict)
    except CommandrUsageError as e:
      self.Usage(str(e) or None)

    if result:
      print result

  def _BuildOptParse(self, info):
    """Sets the current command parser to reflect the provided command.

    Args:
      info - CommandInfo of the command being built.
    Returns:
      argspec - ArgSpec object returned from inspect.getargspec() on the chosen
          command function.
      defaults_dict - Defaults will pulled from argspec.

    Returns:
      A populated OptionParser object.
    """
    usage = 'Usage: %%prog %s [options]\n' % (info.name) + \
        'Options without default values MUST be specified\n\n' + \
        'Use: %prog help [command]\n  to see other commands available.'

    self.parser = OptionParser(usage=usage, add_help_option=False)

    self._AddOption(['-h', '--help'], dest='help', action='store_true',
                     default=False)

    # Parse the command function's arguments into the OptionsParser.
    letters = set(['h']) # -h is for help

    # Check if the command function is wrapped with other decorators, and if so,
    # find the original function signature.
    cmd_fn_root = info.callable
    while hasattr(cmd_fn_root, '__wrapped__'):
      cmd_fn_root = getattr(cmd_fn_root, '__wrapped__')

    # Reflect the command function's arguments.
    argspec = inspect.getargspec(cmd_fn_root)

    # Populates defaults iff there is a default
    defaults_dict = {}
    if argspec.defaults:
      for i in xrange(1, len(argspec.defaults) + 1):
        defaults_dict[argspec.args[-i]] = argspec.defaults[-i]

    for arg in argspec.args:
      argname = arg

      if argname == 'self':
        ignore = (info.ignore_self
                  if info.ignore_self is not None
                  else self.ignore_self)
        if ignore:
          continue

      # If the default is True, make the argument a negative
      if arg in defaults_dict and repr(defaults_dict[arg]) == 'True':
        argname = 'no_%s' % argname

      args = ['--%s' % argname]

      switch_options = (argname[0], argname[0].upper())
      for switch in switch_options:
        if switch not in letters and switch not in argspec.args:
          args.insert(0, '-%s' % switch)
          letters.add(switch)
          break

      if arg in defaults_dict:
        if repr(defaults_dict[arg]) == 'False':
          self._AddOption(args, dest=arg, action='store_true',
                      default=False)
        elif repr(defaults_dict[arg]) == 'True':
          self._AddOption(args, dest=arg, action='store_false',
                      default=True)
        elif isinstance(defaults_dict[arg], list):
          self._AddOption(args, dest=arg, action='append',
                          type='string')
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

    return argspec, defaults_dict

  def _AddOption(self, args, **kwargs):
    """Adds an option to the parser.

    This will manage converting underscores to dashes based off of the currently
    set OPTIONS_MODE.

    Args:
      args - List of arguments to add, where the last argument is the full
             argument.
      kwargs - Remaining arguments to be passed to parser.add_option.
    """
    arg_orig_label = args[-1]
    arg_orig_alternates = args[:-1]

    args_final = arg_orig_alternates[:]
    args_hidden = []

    # Build the final arguments list based on the options.
    if '_' in arg_orig_label and self.hyphenate:
      args_final.append(arg_orig_label.replace('_', '-'))

      if self.hidden:
        args_hidden.append(arg_orig_label)
      else:
        args_final.append(arg_orig_label)

    else:
      args_final.append(arg_orig_label)

    # Add the final option to the parser (and possibly a hidden one as well).
    self.parser.add_option(*args_final, **kwargs)

    if args_hidden:
      kwargs_hidden = kwargs.copy()
      kwargs_hidden['help'] = SUPPRESS_HELP
      if 'default' in kwargs_hidden:
        del kwargs_hidden['default']
      self.parser.add_option(*args_hidden, **kwargs_hidden)

  def _CompletionAllCommands(self, prefix):
    """Given a command name prefix, print a ' ' delimited list of all possible
    commands that match, and exit with success. Useful for bash tab completion.

    Args:
      prefix - Command name prefix.
    """
    print ' '.join([
        c.name for c in self._command_list
        if c.name.startswith(prefix)])

    sys.exit(0)

  def Usage(self, message=None):
    """Prints out a Usage message and exits."""
    if self.current_command:
      self._HelpExitCommand(message, self.current_command.name,
                            self.current_command.callable)
    else:
      self._HelpExitNoCommand(message=message)

  def _HelpExitNoCommand(self, cmd_name=None, message=None):
    """Prints the global help message listing all commands.

    Args:
      message - Error message explaining why the script exited, if applicable.
    """
    if cmd_name:
      if cmd_name in self._all_commands:
        self._BuildOptParse(cmd_name)
        return self._HelpExitCommand(None, cmd_name,
                                     self._all_commands[cmd_name].callable,
                                     {}, [])
      else:
        message = "Unknown command '%s'" % cmd_name
    if self.main_docs:
      import __main__
      if getattr(__main__, '__doc__', None):
        print __main__.__doc__, "\n"
      if getattr(__main__, '__copyright__', None):
        print __main__.__copyright__, "\n"

    if message:
      # Emit the error message.
      print message, "\n"

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

      if hasattr(command.callable, '__doc__') and command.callable.__doc__:
        docs = itertools.takewhile(
          bool, [l.strip() for l in command.callable.__doc__.split('\n')])
      else:
        docs = []
      doc = " - %s" % " ".join(docs) if docs else ""
      name = ("[%s]" % command.name if command.name == self.main
              else command.name)
      print "  %s%s" % (name, doc)

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
        arg_start =  " --%s=" % arg
        arg_list = (arg_start.join(str(a) for a in options_dict[arg])
                    if isinstance(options_dict[arg], list)
                    else str(options_dict[arg]))
        print "%s%s" % (arg_start, arg_list)
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

class CommandrError(Exception): pass
class CommandrUsageError(CommandrError): pass
class CommandrDuplicateMainError(CommandrError): pass
