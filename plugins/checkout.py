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
#
"""
Checkout command and related utilities.
"""
import os
import tempfile

from conary.lib import util


from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command

class CheckoutCommand(command.BaseCommand):
    """
    Creates a working directory for working with the given product.

    Parameters: (repository namespace version|label)

    Example: checkout foresight.rpath.org fl 2
    Assuming that there were a product defined at
    foresight.rpath.org@fl:proddef-2, this would create a product for
    """

    commands = ['checkout']

    def runCommand(self, handle, _, args):
        if len(args) == 3:
            label, = self.requireParameters(args, ['label'])[1:]
            self.checkoutByLabelCommand(handle, label)
        else:
            params = self.requireParameters(args, ['repository',
                                                   'namespace', 'version'])
            repository, namespace, version = params[1:]
            self.checkoutCommand(handle, repository, namespace, version)

    def checkoutByLabelCommand(self, handle, label):
        #R0201: method could be a function
        #pylint: disable-msg=R0201
        version = handle.Checkout.getProductVersionByLabel(label)
        handle.Checkout.createProductCheckout(version)
        return 0

    def checkoutCommand(self, handle, repository, namespace, version):
        #R0201: method could be a function
        #pylint: disable-msg=R0201
        version = handle.Checkout.getProductVersionByParts(
                                            repository, namespace, version)
        handle.Checkout.createProductCheckout(version)
        return 0

class Checkout(pluginapi.Plugin):
    name = 'checkout'

    def registerCommands(self):
        self._handle.Commands.registerCommand(CheckoutCommand)

    def getProductVersionByParts(self, repository, namespace, version):
        labelStr = '%s@%s:proddef-%s' % (repository, namespace, version)
        return self.getProductVersionByLabel(labelStr)

    def getProductVersionByLabel(self, label):
        version = self._handle.facade.conary._findTrove(
                                        'product-definition:source',
                                        str(label))[1]
        return str(version)

    def createProductCheckout(self, version, checkoutDir=None):
        if checkoutDir is None:
            checkoutDir = tempfile.mkdtemp(dir=os.getcwd())
            tempDir = checkoutDir
        else:
            tempDir = None
            if not os.path.exists(checkoutDir):
                util.mkdirChain(checkoutDir)

        targetDir = checkoutDir + '/RBUILD'
        self._handle.facade.conary.checkout('product-definition', version,
                                           targetDir=targetDir)
        productStore = self._handle.Product.getProductStoreFromDirectory(
                                                                targetDir)
        product = productStore.get()
        if tempDir:
            checkoutDir = product.getProductShortname()
            if os.path.exists(checkoutDir):
                util.rmtree(tempDir)
                raise errors.RbuildError(
                                'Directory %r already exists.' % checkoutDir)
            os.rename(tempDir, checkoutDir)
            targetDir = checkoutDir + '/RBUILD'

        stages = product.getStages()
        for stage in stages:
            stageDir = checkoutDir + '/' + stage.name
            os.mkdir(stageDir)
            open(stageDir + '/.stage', 'w').write(stage.name + '\n')
        self._handle.getConfig().writeToFile(targetDir + '/rbuildrc')
        return self._handle.Product.getProductStoreFromDirectory(targetDir)
