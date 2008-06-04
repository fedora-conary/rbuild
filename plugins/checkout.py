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

from rpath_common.proddef import api1 as proddef

from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command

class CheckoutCommand(command.BaseCommand):
    """
    Creates a working directory for working with the given product.

    Parameters: (repository namespace shortname version|label)

    Example: checkout foresight.rpath.org fl prod 2
    Assuming that there were a product defined at
    foresight.rpath.org@fl:prod-2, this would create a product
    subdirectory tree representing the contents of that product
    definition.
    """

    commands = ['checkout']

    def runCommand(self, handle, _, args):
        if len(args) == 3:
            label, = self.requireParameters(args, ['label'])[1:]
            self._checkoutByLabelCommand(handle, label)
        else:
            params = self.requireParameters(args, ['repository', 'namespace',
                                                   'shortname', 'version'])
            repository, namespace, shortname, version = params[1:]
            self._checkoutCommand(handle, repository, namespace, shortname, version)

    @staticmethod
    def _checkoutByLabelCommand(handle, label):
        version = handle.Checkout.getProductVersionByLabel(label)
        handle.Checkout.createProductCheckout(version)
        return 0

    @staticmethod
    def _checkoutCommand(handle, repository, namespace, shortname, version):
        version = handle.Checkout.getProductVersionByParts(
                                repository, namespace, shortname, version)
        handle.Checkout.createProductCheckout(version)
        return 0

class Checkout(pluginapi.Plugin):
    name = 'checkout'

    def registerCommands(self):
        self.handle.Commands.registerCommand(CheckoutCommand)

    def getProductVersionByParts(self, repository, namespace, shortname, version):
        prodDef = proddef.ProductDefinition()
        prodDef.setConaryRepositoryHostname(repository)
        prodDef.setConaryNamespace(namespace)
        prodDef.setProductShortname(shortname)
        prodDef.setProductVersion(version)
        labelStr = prodDef.getProductDefinitionLabel()
        return self.getProductVersionByLabel(labelStr)

    def getProductVersionByLabel(self, label):
        troveName = proddef.ProductDefinition.getTroveName() + ':source'
        version = self.handle.facade.conary._findTrove(
                                        troveName,
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

        targetDir = checkoutDir + '/.rbuild'
        self.handle.facade.conary.checkout('product-definition', version,
                                           targetDir=targetDir)
        productStore = self.handle.Product.getProductStoreFromDirectory(
                                                                checkoutDir)
        product = productStore.get()
        if tempDir:
            checkoutDir = product.getProductShortname()
            if os.path.exists(checkoutDir):
                util.rmtree(tempDir)
                raise errors.RbuildError(
                                'Directory %r already exists.' % checkoutDir)
            os.rename(tempDir, checkoutDir)
            targetDir = checkoutDir + '/.rbuild'

        stages = product.getStages()
        for stage in stages:
            stageDir = checkoutDir + '/' + stage.name
            os.mkdir(stageDir)
            open(stageDir + '/.stage', 'w').write(stage.name + '\n')
        self.handle.getConfig().writeToFile(targetDir + '/rbuildrc')
        return self.handle.Product.getProductStoreFromDirectory(checkoutDir)

