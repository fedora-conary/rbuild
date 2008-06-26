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

from rbuild import pluginapi
from rbuild.pluginapi import command

class BuildImagesCommand(command.BaseCommand):
    help = 'build images for this stage'
    docs = {'no-watch' : 'do not watch the job after starting the build' }

    def addLocalParameters(self, argDef):
        argDef['no-watch'] = command.NO_PARAM

    #pylint: disable-msg=R0201,R0903
    # could be a function, and too few public methods
    def runCommand(self, handle, argSet, args):
        watch = not argSet.pop('no-watch', False)
        # no allowed parameters
        self.requireParameters(args)
        buildIds = handle.BuildImages.buildAllImages()
        if watch:
            handle.BuildImages.watchImages(buildIds)


class BuildImages(pluginapi.Plugin):
    name = 'buildimages'

    def initialize(self):
        self.handle.Commands.getCommandClass('build').registerSubCommand(
                                    'images', BuildImagesCommand)

    def buildAllImages(self):
        return self.handle.facade.rbuilder.buildAllImagesForStage()

    def watchImages(self, buildIds):
        self.handle.facade.rbuilder.watchImages(buildIds)