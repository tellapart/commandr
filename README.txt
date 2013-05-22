========
commandr
========

commandr is a simple tool for making python functions accessible from the
command line.

Example usage:

In demo.py:
  from commandr import command, Run

  @command('greet')
  def Hi(name, title='Mr.', comma=False, capslock=False):
    '''Greet someone.
    Arguments:
      name - Name to greet.
      title - Title of the person to greet.
      comma - Whether to add a comma after the greeting.
      capslock - Whether to output in ALL CAPS.
    '''
    hello = 'Hi%s %s %s!' % ("," if comma else "", title, name)
    if capslock:
      return hello.upper()
    else:
      return hello
  if __name__ == '__main__':
    Run()

The command can them be invoked on the command line with:
  $ python demo.py greet --name=John -c
  Hi, Mr. John!


Authors
=======
commandr was developed at TellApart by Kevin Ballard and Chris Huegle.