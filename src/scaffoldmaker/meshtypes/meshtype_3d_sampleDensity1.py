"""
Generates equally distributed nodes in a flat mount sample.
"""

from __future__ import division

from cmlibs.utils.zinc.field import findOrCreateFieldCoordinates, findOrCreateFieldFiniteElement, get_group_list
from cmlibs.zinc.element import Element
from cmlibs.zinc.field import Field
from cmlibs.zinc.node import Node
from scaffoldmaker.annotation.annotationgroup import AnnotationGroup
from scaffoldmaker.meshtypes.scaffold_base import Scaffold_base
from scaffoldmaker.utils.eftfactory_tricubichermite import eftfactory_tricubichermite
from scaffoldmaker.utils.meshrefinement import MeshRefinement

import math


class MeshType_3d_sampleDensity1(Scaffold_base):
    '''
    classdocs
    '''
    @staticmethod
    def getName():
        return '3D Sample Density 1'

    @staticmethod
    def getDefaultOptions(parameterSetName='Default'):
        return {
            'Number of elements 1' : 1,
            'Number of elements 2' : 1,
            'Number of elements 3' : 1,
            'Use cross derivatives' : False,
            'Refine' : False,
            'Refine number of elements 1' : 1,
            'Refine number of elements 2' : 1,
            'Refine number of elements 3' : 1
        }

    @staticmethod
    def getOrderedOptionNames():
        return [
            'Number of elements 1',
            'Number of elements 2',
            'Number of elements 3',
            'Use cross derivatives',
            'Refine',
            'Refine number of elements 1',
            'Refine number of elements 2',
            'Refine number of elements 3'
        ]

    @staticmethod
    def checkOptions(options):
        for key in [
            'Number of elements 1',
            'Number of elements 2',
            'Number of elements 3',
            'Refine number of elements 1',
            'Refine number of elements 2',
            'Refine number of elements 3']:
            if options[key] < 1:
                options[key] = 1

    @classmethod
    def generateBaseMesh(cls, region, options):
        """
        Generate the base tricubic Hermite mesh.
        :param region: Zinc region to define model in. Must be empty.
        :param options: Dict containing options. See getDefaultOptions().
        :return: [] empty list of AnnotationGroup, None
        """

        fm = region.getFieldmodule()
        fm.beginChange()
        coordinates = findOrCreateFieldCoordinates(fm)

        # Set up density field
        density = findOrCreateFieldFiniteElement(fm, name='innervation density', components_count=1,
                                                 type_coordinate=False)

        nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        nodetemplate = nodes.createNodetemplate()
        nodetemplate.defineField(coordinates)
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_VALUE, 1)

        densityNodetemplate = nodes.createNodetemplate()
        densityNodetemplate.defineField(density)

        cache = fm.createFieldcache()

        # calculate boundary of flat-mount sample

        maxX = 144.37
        minX = 10271.9
        maxY = -9422.59
        minY = -194.91
        numRow = 27 * 2
        numCol = 25 * 2
        z = 0.0

        sir = region.createStreaminformationRegion()
        file = "C:\\Users\\mlin865\\HeatMapDrew-CGRP Female Dorsal 2\\#2 CGRP Female Dorsal Mouse annotation.xml.ex"  # should be made to take in an input file
        sir.createStreamresourceFile(file)

        region.read(sir)

        nodeset = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        mesh = fm.findMeshByDimension(1)
        fieldcache = fm.createFieldcache()

        allGroups = get_group_list(fm)
        dataCoords = []
        boundaryCoords = []
        notDendriteCoords = []

        nodeIter = nodeset.createNodeiterator()
        node = nodeIter.next()
        fieldcache.setNode(node)

        while node.isValid():
            fieldcache.setNode(node)
            result, x = coordinates.getNodeParameters(fieldcache, -1, Node.VALUE_LABEL_VALUE, 1, 3)
            dataCoords.append(x)
            node = nodeIter.next()

        # Extract nodes from groups
        for group in allGroups:
            if group.getName() != "Dendrite":
                notDendriteNodeSet = group.getNodesetGroup(nodeset)
                nodeIter = notDendriteNodeSet.createNodeiterator()
                node = nodeIter.next()
                fieldcache.setNode(node)

                while node.isValid():
                    fieldcache.setNode(node)
                    result, x = coordinates.getNodeParameters(fieldcache, -1, Node.VALUE_LABEL_VALUE, 1, 3)
                    notDendriteCoords.append(x)
                    node = nodeIter.next()

            if "circular-longitudinal muscle interface of" in group.getName() or "esophagus" in group.getName() or "Gastroduodenal" in group.getName():
                boundaryNodeSet = group.getNodesetGroup(nodeset)
                nodeIter = boundaryNodeSet.createNodeiterator()
                node = nodeIter.next()
                fieldcache.setNode(node)

                while node.isValid():
                    fieldcache.setNode(node)
                    result, x = coordinates.getNodeParameters(fieldcache, -1, Node.VALUE_LABEL_VALUE, 1, 3)
                    boundaryCoords.append(x)
                    node = nodeIter.next()

        mesh.destroyAllElements()
        nodeset.destroyAllNodes()

        centres = []
        xSpacing = (maxX - minX) / numCol
        ySpacing = (maxY - minY) / numRow
        densityCounts = []
        boundaryCentres = []

        for rowIdx in range(numRow):
            prevCount = 0
            prevIsBoundary = 0

            for colIdx in range(numCol):
                if colIdx % 2 == 1 and rowIdx % 2 == 1:
                    centreX = (maxX - minX) / numCol * colIdx + minX
                    centreY = (maxY - minY) / numRow * rowIdx + minY
                    densityCount = 0.0
                    notDendriteDensityCount = 0.0
                    boundaryBox = 0

                    # set up x and y limits
                    xLimits = [centreX - xSpacing, centreX + xSpacing]
                    yLimits = [centreY - ySpacing, centreY + ySpacing]

                    for dataCoord in dataCoords:
                        if xLimits[1] <= dataCoord[0] <= xLimits[0] and yLimits[1] <= dataCoord[1] <= yLimits[0]:
                            densityCount += 1

                    for boundaryCoord in boundaryCoords:
                        if xLimits[1] <= boundaryCoord[0] <= xLimits[0] and yLimits[1] <= boundaryCoord[1] <= yLimits[0]:
                            boundaryBox = 1
                            break

                    for dataCoord in notDendriteCoords:
                        if xLimits[1] <= dataCoord[0] <= xLimits[0] and yLimits[1] <= dataCoord[1] <= yLimits[0]:
                            notDendriteDensityCount += 1

                    densityCount = densityCount - notDendriteDensityCount
                    if densityCount < 0.0:
                        densityCount = 0.0

                    if densityCount > 0.0:
                        densityCounts.append(densityCount)
                        centres.append([centreX, centreY, z])
                    else:
                        if prevCount > 0.0 or prevIsBoundary:
                            # check next
                            nextX = (maxX - minX) / numCol * (colIdx + 2) + minX
                            xLimits = [nextX - xSpacing, nextX + xSpacing]
                            for dataCoord in dataCoords:
                                if xLimits[1] <= dataCoord[0] <= xLimits[0] and yLimits[1] <= dataCoord[1] <= yLimits[0]:
                                    densityCounts.append(densityCount)
                                    centres.append([centreX, centreY, z])
                                    break
                        if boundaryBox:
                            densityCounts.append(densityCount)
                            centres.append([centreX, centreY, z])

                    prevCount = densityCount
                    if boundaryBox:
                        prevIsBoundary = 1

        nodeIdentifier = 1
        for i in range(len(centres)):
            node = nodes.createNode(nodeIdentifier, nodetemplate)
            cache.setNode(node)
            coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, centres[i])
            node.merge(densityNodetemplate)
            density.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, densityCounts[i])
            nodeIdentifier = nodeIdentifier + 1

        # for i in range(len(notDendriteCoords)):
        #     node = nodes.createNode(nodeIdentifier, nodetemplate)
        #     cache.setNode(node)
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, notDendriteCoords[i])
        #     nodeIdentifier = nodeIdentifier + 1

        # compare against Drew's heatmap

        fm.endChange()
        return [], None

    @classmethod
    def refineMesh(cls, meshrefinement, options):
        """
        Refine source mesh into separate region, with change of basis.
        :param meshrefinement: MeshRefinement, which knows source and target region.
        :param options: Dict containing options. See getDefaultOptions().
        """
        assert isinstance(meshrefinement, MeshRefinement)
        refineElementsCount1 = options['Refine number of elements 1']
        refineElementsCount2 = options['Refine number of elements 2']
        refineElementsCount3 = options['Refine number of elements 3']
        meshrefinement.refineAllElementsCubeStandard3d(refineElementsCount1, refineElementsCount2, refineElementsCount3)
