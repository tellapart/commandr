"""Example usage of commandr.
"""

from commandr import command, Run

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
