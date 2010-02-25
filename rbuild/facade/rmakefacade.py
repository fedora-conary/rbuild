#
# Copyright (c) 2008-2009 rPath, Inc.
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
rMake facade module

This module provides a high-level stable API for use within rbuild
plugins.  It provides public methods which are only to be accessed
via C{handle.facade.rmake} which is automatically available to
all plugins through the C{handle} object.
"""

import itertools
import os

from rmake.build import buildcfg
from rmake.cmdline import helper
from rmake.cmdline import query
from rmake import plugins
from rbuild import errors

class RmakeFacade(object):
    """
    The rBuild rMake facade.

    Note that the contents of objects marked as B{opaque} may vary
    according to the version of rMake and conary in use, and the contents
    of such objecst are not included in the stable rBuild API.
    """

    def __init__(self, handle):
        """
        @param handle: The handle with which this instance is associated.
        """
        self._handle = handle
        self._rmakeConfig = None
        self._rmakeConfigWithContexts = None
        self._plugins = None

    def _getBaseRmakeConfig(self, readConfigFiles=True):
        """
        Fetches an B{opaque} rmake build config object with no rBuild
        configuration data included.
        @param readConfigFiles: initialize contents of config object
        from normal configuration files (default: True)
        @type readConfigFiles: bool
        @return: C{rmake.build.buildcfg.BuildConfiguration} B{opaque} object
        """
        return buildcfg.BuildConfiguration(readConfigFiles = readConfigFiles,
                                           ignoreErrors = True)

    def _getRmakeConfig(self, useCache=True, includeContext=True):
        """
        Returns an rmake configuration file that matches the product associated
        with the current handle.
        @param useCache: if True (default), uses a cached version of the
        rmake configuration file if available, and caches the results
        for future invocations.
        @type useCache: bool
        @param includeContext: include context-specific information, as
        required when building an rmake configuration for use in a
        specific rMake job (default: True).  Setting this to False
        also disables caching.
        @type includeContext: bool
        @return: rMake configuration file suitable for use with the current
        product.
        """
        if not includeContext:
            # context-free config must not be cached
            useCache = False

        if self._rmakeConfig and useCache:
            return self._rmakeConfig

        conaryFacade = self._handle.facade.conary
        rbuildConfig = self._handle.getConfig()
        if not self._plugins:
            p = plugins.PluginManager(rbuildConfig.rmakePluginDirs,
                                      ['test'])
            p.loadPlugins()
            p.callLibraryHook('library_preInit')
            self._plugins = p

        if includeContext:
            stageName = self._handle.productStore.getActiveStageName()
            stageLabel = conaryFacade._getLabel(
                self._handle.product.getLabelForStage(stageName))
            baseFlavor = conaryFacade._getFlavor(
                self._handle.product.getBaseFlavor())

        # BuildConfiguration must be created after loading rMake plugins
        cfg = buildcfg.BuildConfiguration(False)
        cfg.rbuilderUrl = rbuildConfig.serverUrl
        cfg.rmakeUser = rbuildConfig.user
        cfg.resolveTrovesOnly = True
        cfg.shortenGroupFlavors = True
        cfg.ignoreExternalRebuildDeps = True
        if rbuildConfig.rmakePluginDirs:
            cfg.pluginDirs = rbuildConfig.rmakePluginDirs

        if includeContext:
            cfg.buildLabel = stageLabel
            cfg.installLabelPath = [ stageLabel ]
            cfg.flavor = [baseFlavor]
            cfg.buildFlavor = baseFlavor
            searchPaths = self._handle.product.getResolveTroves()
            searchPaths = [ x.getTroveTup() for x in searchPaths ]
            # Search paths with no trove name go at the end of installLabelPath
            # Everything else becomes a resolveTrove
            cfg.resolveTroves = [
                [x] for x in searchPaths if x[0] is not None ]
            cfg.installLabelPath.extend(conaryFacade._getLabel(x[1])
                for x in searchPaths if x[0] is None)

            cfg.autoLoadRecipes = \
                self._handle.productStore.getPlatformAutoLoadRecipes()

            #E1101: 'BuildConfiguration' has no 'user' member - untrue
            #pylint: disable-msg=E1101
            cfg.user.append((stageLabel.getHost(),) + rbuildConfig.user)

        cfg.repositoryMap = rbuildConfig.repositoryMap
        if rbuildConfig.rmakeUrl:
            cfg.rmakeUrl = rbuildConfig.rmakeUrl
        if rbuildConfig.rmakeUser:
            cfg.rmakeUser = rbuildConfig.rmakeUser
        cfg.signatureKey = rbuildConfig.signatureKey
        cfg.signatureKeyMap = rbuildConfig.signatureKeyMap
        cfg.name = rbuildConfig.name
        cfg.contact = rbuildConfig.contact
        self._handle.facade.conary._parseRBuilderConfigFile(cfg)

        if self._handle.productStore:
            rmakeConfigPath = self._handle.productStore.getRmakeConfigPath()
            if os.path.exists(rmakeConfigPath):
                cfg.includeConfigFile(rmakeConfigPath)

        if useCache:
            self._rmakeConfig = cfg

        return cfg

    def _getRmakeConfigWithContexts(self):
        """
        Returns an rmake configuration file that matches the product associated
        with the current handle.  Beyond the settings provided in 
        _getRmakeConfig, this rmake configuration will have contexts set up 
        that match the flavors required by the product's build definitions 
        for building packages for those build definitions.
        @return: rMake configuration object suitable for use with the current
        product, and a dictionary of {flavor : contextName} lists that match 
        the flavors in the current product's build definitions.
        """

        if self._rmakeConfigWithContexts:
            return self._rmakeConfigWithContexts
        cfg = self._getRmakeConfig(useCache=False)
        conaryFacade = self._handle.facade.conary
        buildFlavors = [x[1] 
                        for x in self._handle.productStore.getGroupFlavors() ]
        contextNames = conaryFacade._getShortFlavorDescriptors(buildFlavors)
        for flavor, name in contextNames.items():
            # Fix names to be rMake-safe
            name = name.replace(',', '-')
            contextNames[flavor] = name

            cfg.configLine('[%s]' % name)
            cfg.configLine('flavor %s' % flavor)
            cfg.configLine('buildFlavor %s' % str(flavor))
        # TODO: add cfg interface for resetting the section to default
        cfg._sectionName = None
        self._rmakeConfigWithContexts = (cfg, contextNames)
        return cfg, contextNames

    def _getRmakeHelperWithContexts(self):
        """
        @return: an rMakeHelper object suitable for use with the current
        product, and a dictionary of {flavor : contextName} lists that match the
        flavors in the current product's build definitions.
        """
        cfg, contextDict = self._getRmakeConfigWithContexts()
        client = helper.rMakeHelper(buildConfig=cfg, plugins=self._plugins)
        return client, contextDict

    def _getRmakeContexts(self):
        _, contextDict = self._getRmakeConfigWithContexts()
        return contextDict

    def _getRmakeHelper(self):
        """
        @return: an rMakeHelper object suitable for use with the current
        product (without any contexts for use in starting a build)
        """
        cfg = self._getRmakeConfig()
        return helper.rMakeHelper(buildConfig=cfg)

    def createBuildJobForStage(self, itemList, recurse=True, rebuild=True,
      useLocal=False, progress=True):
        """
        @param itemList: list of troveSpec style items to build or
            paths to recipes.  May include version (after =) flavor
            (in []) or context (in {}) for each item.
        @type  itemList: list of strings
        @param recurse: if C{True} (the default), build all child
            packages included in groups.
        @param rebuild: if C{True} (the default), rmake will reuse
            packages that do not need to be rebuilt.
        @param useLocal: if C{True}, built packages on the stage label
            will be inserted into resolveTroves
        @param progress: if C{True} (the default), print a progress
            indication at the start of the operation
        @return: The new build job object
        """
        rmakeClient = self._getRmakeHelperWithContexts()[0]
        handle = self._handle

        if progress:
            handle.ui.progress('Creating rMake build job for %d items'
                               %len(itemList))

        stageLabel = handle.productStore.getActiveStageLabel()
        if recurse:
            recurse = rmakeClient.BUILD_RECURSE_GROUPS_SOURCE

        cfg = self._getRmakeConfigWithContexts()[0]
        if useLocal:
            # Insert troves from the build label into resolveTroves
            # to emulate a recursive job's affinity for built troves.
            conary = handle.facade.conary
            initialTroves = conary.getLatestPackagesOnLabel(stageLabel)
            cfg.resolveTroves.insert(0, initialTroves)

        job = rmakeClient.createBuildJob(itemList,
            rebuild=rebuild, recurseGroups=recurse, limitToLabels=[stageLabel],
            buildConfig=cfg)

        # Populate the group's productDefinitionSearchPath macro by
        # finding them first in the lookups rMake did for
        # resolveTroveTups, then with findTroves.
        searchPathTups = [x.getTroveTup()
                          for x in handle.product.getGroupSearchPaths()]

        # Iterate over each config that belongs to at least one trove
        # (generally one per context)
        troveConfigs = dict((id(x.cfg), x.cfg) for x in job.iterTroves())
        for troveCfg in troveConfigs.itervalues():
            # Figure out which troves we need to look up by filtering
            # out the ones rMake already looked up for us.
            alreadyFoundMap = dict((troveSpec, troveTup)
                    for (troveSpec, troveTup) in itertools.izip(
                        itertools.chain(*troveCfg.resolveTroves),
                        itertools.chain(*troveCfg.resolveTroveTups)))
            toFind = [x for x in searchPathTups if x not in alreadyFoundMap]

            # Look up the remaining ones using the config's flavor.
            results = handle.facade.conary._findTroves(toFind,
                    troveCfg.installLabelPath, troveCfg.flavor,
                    allowMissing=True)

            groupSearchPath = []
            for troveSpec in searchPathTups:
                if troveSpec in alreadyFoundMap:
                    troveTup = alreadyFoundMap[troveSpec]
                elif troveSpec in results:
                    troveTup = max(results[troveSpec])
                else:
                    raise errors.MissingGroupSearchPathElementError(*troveSpec)
                groupSearchPath.append('%s=%s' % troveTup[:2])

            troveCfg.macros['productDefinitionSearchPath'] = '\n'.join(
                    groupSearchPath)

        return job

    def createImagesJobForStage(self, nameFilter = None):
        #pylint: disable-msg=R0914
        # fewer local variables would make this hard; it's pretty simple
        # despite the large number of locals
        rmakeClient = self._getRmakeHelper()
        conaryFacade = self._handle.facade.conary
        stageName = self._handle.productStore.getActiveStageName()
        stageLabel = self._handle.productStore.getActiveStageLabel()
        product = self._handle.product
        productName = str(product.getProductShortname())
        builds = self._handle.productStore.getBuildsWithFullFlavors(stageName)
        allImages = []
        for build, buildFlavor in builds:
            if nameFilter is not None:
                if not build.getBuildName() in nameFilter:
                    continue
            buildFlavor = conaryFacade._getFlavor(buildFlavor)
            groupName = str(build.getBuildImageGroup())
            buildImageName = str(build.getBuildName())
            buildImageType = build.getBuildImage().containerFormat
            buildSettings = build.getBuildImage().fields.copy()
            troveSpec = (groupName, stageLabel, buildFlavor)
            allImages.append((troveSpec, buildImageType,
                              buildSettings, buildImageName))

        return rmakeClient.createImageJob(productName, allImages)

    def getBuildIdsFromJobId(self, jobId):
        client = self._getRmakeHelper()
        job = client.getJob(jobId)
        buildIds = [x.getImageBuildId() for x in job.troves.values()]
        return buildIds

    def buildJob(self, job):
        """
        Submits the given job to the rMake server
        @param job: rMake job to submit
        @return: jobId of the job that is started
        @rtype: int
        """
        client = self._getRmakeHelper()
        return client.buildJob(job)

    def watchAndCommitJob(self, jobId, message=None):
        """
        Waits for the job to commit and watches.
        @param jobId: id of the job to watch and commit.
        @return: True if the watch and commit succeeds
        """
        if not message:
            message='Automatic commit by rbuild'

        client = self._getRmakeHelper()
        return client.watch(jobId, commit=True, showTroveLogs=True,
                            showBuildLogs=True, message=message)

    def watchJob(self, jobId):
        """
        Output progress of the job to stdout.
        @param jobId: id of the job to watch
        @return: True if the watch succeeds
        """
        client = self._getRmakeHelper()
        return client.watch(jobId, showTroveLogs=True, showBuildLogs=True,
                            exitOnFinish=True)

    def displayJob(self, jobId, troveList=None, showLogs=False):
        client = self._getRmakeHelper()
        query.displayJobInfo(client, jobId, troveList, showLogs=showLogs,
                             displayTroves=True)

    def isJobBuilt(self, jobId):
        client = self._getRmakeHelper()
        job = client.getJob(jobId)
        return job.isBuilt()

    @staticmethod
    def overlayJob(job1, job2):
        if job1 is None:
            job1 = job2
        else:
            for buildTrove in job2.iterTroves():
                job1.addBuildTrove(buildTrove)
            job1Configs = job1.getConfigDict()
            job2Configs = job2.getConfigDict()
            for context, config in job1Configs.iteritems():
                if context in job2Configs:
                    config.buildTroveSpecs.extend(
                                    job2Configs[context].buildTroveSpecs)
            prebuiltBinaries = set(job1.getMainConfig().prebuiltBinaries
                                    +   job2.getMainConfig().prebuiltBinaries)
            job1.getMainConfig().prebuiltBinaries = list(prebuiltBinaries)
        job1.getMainConfig().primaryTroves = list(job2.iterTroveList(True))
        return job1
