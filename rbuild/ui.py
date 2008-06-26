#
# Copyright (c) 2008 rPath, Inc.
#
# This program is distributed under the terms of the Common Public License,
# version 1.0. A copy of this license should have been distributed with this
# source file in a file called LICENSE. If it is not present, the license
# is always available at http://www.rpath.com/permanent/licenses/CPL-1.0.
#
# This program is distributed in the hope that it will be useful, but
# without any warranty; without even the implied warranty of merchantability
# or fitness for a particular purpose. See the Common Public License for
# full details.
"""
User interface module for rbuild.
"""
import getpass
import sys

class UserInterface(object):
    def __init__(self, cfg, outStream=None, errorStream=None):
        if outStream is None:
            outStream = sys.stdout
        if errorStream is None:
            errorStream = sys.stderr
        self.outStream = outStream
        self.errorStream = errorStream
        self.cfg = cfg

    def write(self, msg, *args):
        self.outStream.write('%s\n' % (msg % args, ))

    def writeError(self, errorMsg, *args):
        self.errorStream.write('warning: %s\n' % (errorMsg % args, ))

    def info(self, msg, *args):
        if not self.cfg.quiet:
            self.write(msg, *args)

    def warning(self, msg, *args):
        self.writeError(msg, *args)

    def input(self, prompt):
        try:
            return raw_input(prompt)
        except EOFError:
            raise errors.RbuildError(
                    "Ran out of input while reading for '%s'" % prompt)

    def inputPassword(self, prompt):
        return getpass.getpass(prompt)

    def getPassword(self, prompt, default=None, validationFn=None):
        return self.getResponse(prompt, default=default,
                                validationFn=validationFn,
                                inputFn=self.inputPassword)

    def getResponse(self, prompt, default=None, validationFn=None,
                    inputFn=None):
        if inputFn is None:
            inputFn = self.input
        if default:
            prompt += ' (Default: %s): ' % default
        else:
            prompt += ': '
        while True:
            response = inputFn(prompt)
            if not response:
                if not default:
                    self.write('Empty response not allowed.')
                    continue
                else:
                    return default
            if validationFn is not None:
                if not validationFn(response):
                    continue
            return response