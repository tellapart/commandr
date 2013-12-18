#!/bin/bash
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
#
# Bash Tab-completion registration for commandr scripts. This is used like:
#  $ source register_commandr_completion.sh example.py
#

function _CommandrCompletion() {
  local cur
  cur=${COMP_WORDS[COMP_CWORD]}

  COMPREPLY=()

  # Only do completion on the command name.
  if [ $1 == $3 ] ; then
    COMPREPLY=($( $1 --list_command_completions "${cur}" ))
  fi

  return 0
}

complete -F _CommandrCompletion -o default "$@"

