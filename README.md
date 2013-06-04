commandr
========

commandr is a simple tool for making Python functions accessible from the
command line. Essentially you add a command decorator and you are off to 
the races.

Example
-------
In example.py:
```python
  @command('greet')
  def SayGreeting(name, title='Mr.', times=1, comma=False, capslock=False):
    """Greet someone.
    Arguments:
      name - Name to greet.
      title - Title of the person to greet.
      times - Number of time to say the greeting.
      comma - Whether to add a comma after the greeting.
      capslock - Whether to output in ALL CAPS.
    """
    message = 'Hi%s %s %s!' % (',' if comma else '', title, name)
    if capslock:
      message = message.upper()

    for _ in xrange(times):
      print message

  if __name__ == '__main__':
    Run()
````

The command can them be invoked on the command line with:
```bash
  $ python example.py greet --name=John
  Hi Mr. John!

  # Invoke with short parameter names
  $ python example.py greet -n=Nick -t=Dr. -c
  Hi, Dr. Nick!

  # Invoke with positional arguments
  $ python example.py greet Smith Ms.
  Hi Ms. Smith!

  # Combined explicit and positional arguments. In this case, 'Julie' will
  # match the first unspecified argument 'name'
  # 'capslock' doesn't have a short name because 'comma' came first.
  # Equal signs are also optional.
  $ python example.py greet --title Engineer -c --capslock Julie
  HI, ENGINEER JULIE!
```

Installation
------------

To install commandr, simply:
```bash
$ pip install commandr
```
or
```bash
$ easy_install commandr
```

Features
--------

commandr creates command-line interfaces to Python functions through a decorator
that uses reflection to automatically convert a function's signature into a
command line parser.

The following script will be used to show examples of the features:

```python
  from commandr import command, Run

  @command('get', category='Database')
  def DoGet(key, timeout=10, cache=True):
    """Get an item from the database
    Arguments:
      key - Database key to get.
      timeout - Seconds to wait.
      cache - Whether to get from the local cache first.
    """
    ...

  @command('put', category='Database')
  def DoPut(key, value, timeout=10, transaction=False):
    """Put an item in the database.
    Arguments:
      key - Database key to put.
      value - String value to put.
      timeout - Seconds to wait.
      transaction - Whether to perform the put in a transaction
    """
    ...

  @command('status')
  def GetStatus(service=None):
    """Get the status of service, or all services.
    Arguments:
      service - If not None, get the status of this service, otherwise, get
                the status of all services.
    """
    ...

  @command('version')
  def GetVersion(host, dev=False):
    ...

  if __name__ == '__main__':
    Run()
```

### Parser Generation

The command-line interface to a function is generated based on the arguments in
the function's signature. Both regular and keyword arguments are supported.
Arguments can be bound on the command line explicitly by name, by the first
letter in the argument's name (limited to the first unique instance of that
letter), or positionally. For example, the following are valid ways to invoke
the 'put' command:
```bash
$ python features.py put --key=somekey --value somevalue
$ python features.py put -k somekey -v somevalue
$ python features.py put somekey somevalue -t 5
```
Note that the '=' signs are optional.

### Defaults and Types

Keyword argument defaults are respected, and are used to infer types for those
parameters. For non-keyword arguments and keyword arguments where the default
is None, the default type is str. The generated parser automatically casts
and checks types. For example, the following will not validate, and will print
usage help:
```bash
$ python features.py get somekey --timeout=blah
```
In the body of DoGet e.g., the 'timeout' parameter will always be an int.

### Boolean Parameters

Boolean parameters are treated specially. The generated parser converts boolean
keyword parameters into single flags which, when specified on the command-line,
sets the argument to the opposite of the default.

For example, the 'dev' argument of the 'version' command can be set to True by:
```bash
$ python features.py version --dev
```
When a boolean parameter default is True, the generated switch is the parameter
name with "no_" prefixed. For example, to set 'cache' to False for 'get':
```bash
$ python features.py get somekey --no_cache
```

### Documentation Generation

Command help is automatically generated, using the signature and docstring of
decorated functions.

Running a commandr script directly gives a list of available commands, grouped
by the category specified in each decorator.
```bash
$ python features.py
> Command must be specified
>
> General Commands:
>   status
>   version
> Database Commands:
>   get
>   put
```

Documentation for any command can be accessed by running the script with that
command and the -h or --help argument. This includes the function's docstring
(if any), argument names, and default values.
```bash
$ python features.py get -h
> Documentation for command 'get':
> ----------------------------------------
> Get an item from the database
>   Arguments:
>     key - Database key to get.
>     timeout - Seconds to wait.
>     cache - Whether to get from the local cache first.
>
> ----------------------------------------
>
> Usage: features.py command [options]
> Options without default values MUST be specified
>
> Options:
>   -h, --help
>   -k KEY, --key=KEY
>   -t TIMEOUT, --timeout=TIMEOUT
>                         [default: 10]
>   -n, --no_cache
```

If a command is invoked with incomplete arguments, or invalid values, the error
is printed, along with the usage documentation.

```bash
$ python features.py put somekey1 --transaction
> All options without default values must be specified
>
> Current Options:
>  --key=somekey1
>  --value=None
>  --timeout=10
>  --transaction=True
>
> Documentation for command 'put':
> ----------------------------------------
> Put an item in the database.
>   Arguments:
>     key - Database key to put.
>     value - String value to put.
>     timeout - Seconds to wait.
>     transaction - Whether to perform the put in a transaction
>
> ----------------------------------------
>
> Usage: features.py command [options]
> Options without default values MUST be specified
>
> Options:
>   -h, --help
>   -k KEY, --key=KEY
>   -v VALUE, --value=VALUE
>   -t TIMEOUT, --timeout=TIMEOUT
>                         [default: 10]
>   --transaction
```

Authors
-------
commandr was developed at TellApart by [Kevin Ballard](https://github.com/kevinballard) and [Chris Huegle](https://github.com/chuegle).
