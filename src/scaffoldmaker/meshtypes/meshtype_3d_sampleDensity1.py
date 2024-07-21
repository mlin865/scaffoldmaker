"""
Generates equally distributed nodes in a flat mount sample.
"""

from __future__ import division

from cmlibs.utils.zinc.field import findOrCreateFieldCoordinates, findOrCreateFieldFiniteElement, get_group_list
from cmlibs.zinc.element import Element, Elementbasis
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

        cache = fm.createFieldcache()

        sir = region.createStreaminformationRegion()
        file = "C:\\Users\\mlin865\\SPARC Datasets\\Jack Cheng\\retrograde tracing of spinal afferent innervation\\sub-115\\3D scaffold_sub115VM.xml.ex"
            # "C:\\Users\\mlin865\\HeatMapDrew-CGRP Female Dorsal 2\\sub-112\\3D scaffold_sub112VM.xml.ex"
            #"C:\\Users\\mlin865\\SPARC Datasets\\Jack Cheng\\retrograde tracing of spinal afferent innervation\\sub-115\\3D scaffold_sub115VM.xml.ex"
            # "C:\\Users\\mlin865\\SPARC Datasets\\Jack Cheng\\retrograde tracing of spinal afferent innervation\\sub-123\\3D scaffold_sub123VM (1).xml.ex"
            #"C:\\Users\\mlin865\\HeatMapDrew-CGRP Female Dorsal 2\\#2 CGRP Female Dorsal Mouse\\#2 CGRP Female Dorsal Mouse annotation.xml.ex"
            #"C:\\Users\\mlin865\\HeatMapDrew-CGRP Female Dorsal 2\\#5 CGRP Female Dorsal Mouse\\3D scaffold CGRP-FG-F-Mice-Dorsal-5.xml.ex" # should be made to take in an input file
        sir.createStreamresourceFile(file)

        region.read(sir)

        numNodes = nodes.getSize()
        nodeIdentifier = numNodes + 1
        # nodeIdentifier = 1
        mesh = fm.findMeshByDimension(1)
        fieldcache = fm.createFieldcache()

        allGroups = get_group_list(fm)
        dataCoords = []
        boundaryCoords = []

        nodeIter = nodes.createNodeiterator()
        node = nodeIter.next()
        fieldcache.setNode(node)

        maxX = 0.0
        minX = 100000.0
        maxY = -1.0
        minY = -100000.0

        while node.isValid():
            fieldcache.setNode(node)
            result, x = coordinates.getNodeParameters(fieldcache, -1, Node.VALUE_LABEL_VALUE, 1, 3)
            if x[0] > maxX:
                maxX = x[0]
            if x[0] < minX:
                minX = x[0]
            if -x[1] > -maxY:
                maxY = x[1]
            if -x[1] < -minY:
                minY = x[1]

            node = nodeIter.next()

        # calculate boundary of flat-mount sample
        xSpacing = 2000 #400
        ySpacing = -2000 #-350
        z = 0.0

        numCol = int(math.ceil((maxX - minX)/xSpacing))
        numRow = int(math.ceil((maxY - minY) / ySpacing))

        xOffset = (numCol * xSpacing - (maxX - minX)) * 0.5
        yOffset = (numRow * ySpacing - (maxY - minY)) * 0.5

        # Extract nodes from groups
        for group in allGroups:
            if group.getName() == "Axon": # Axon for #5 and Dendrites for #2
                dataNodeSet = group.getNodesetGroup(nodes)
                nodeIter = dataNodeSet.createNodeiterator()
                node = nodeIter.next()
                fieldcache.setNode(node)

                while node.isValid():
                    fieldcache.setNode(node)
                    result, x = coordinates.getNodeParameters(fieldcache, -1, Node.VALUE_LABEL_VALUE, 1, 3)
                    dataCoords.append(x)
                    node = nodeIter.next()

            if "circular-longitudinal muscle interface of" in group.getName() or "esophagus" in group.getName() or "Gastroduodenal" in group.getName():
                nodeCount = 0
                boundaryNodeSet = group.getNodesetGroup(nodes)
                nodeIter = boundaryNodeSet.createNodeiterator()
                node = nodeIter.next()
                fieldcache.setNode(node)

                while node.isValid():
                    fieldcache.setNode(node)
                    result, x = coordinates.getNodeParameters(fieldcache, -1, Node.VALUE_LABEL_VALUE, 1, 3)
                    boundaryCoords.append(x)
                    node = nodeIter.next()

                    # close up big gaps within boundary groups
                    if nodeCount > 0:
                        diff = [x[c] - xPrev[c] for c in range(3)]
                        if abs(diff[0]) > 0.1*abs(xSpacing) or abs(diff[1]) > 0.1*abs(ySpacing):
                            for i in range(4):
                                scale = 1/5 * (i + 1)
                                scaleVector = [scale * c for c in diff]
                                xNew = [scaleVector[c] + x[c] for c in range(3)]
                                boundaryCoords.append(xNew)
                    nodeCount += 1
                    xPrev = x

        totalDendriteCounts = len(dataCoords)

        # mesh.destroyAllElements()
        # nodes.destroyAllNodes()
        #
        # nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        # nodetemplate2 = nodes.createNodetemplate()
        # nodetemplate2.defineField(coordinates)
        # nodetemplate2.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_VALUE, 1)
        # nodetemplate2.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D_DS1, 1)
        # nodetemplate2.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D_DS2, 1)

        densityNodetemplate = nodes.createNodetemplate()
        densityNodetemplate.defineField(density)

        dataCentres = []
        densityCounts = []
        xAll = []
        centres = []
        inBoundaryCentres = []

        # Make grid and find centres inside boundary
        for colIdx in range(numCol + 1):
            startRowIdx = numRow
            endRowIdx = 0
            for rowIdx in range(numRow + 1):
                xNode = minX + xSpacing * colIdx - xOffset
                yNode = minY + ySpacing * rowIdx - yOffset
                xAll.append([xNode, yNode, z])

                # node = nodes.createNode(nodeIdentifier, nodetemplate2)
                # cache.setNode(node)
                # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, [xNode, yNode, z])
                # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, [0.0, 0.0, 0.0])
                # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, [0.0, 0.0, 0.0])
                # nodeIdentifier = nodeIdentifier + 1

                xLimit = [xNode, xNode + xSpacing]
                yLimit = [yNode, yNode + ySpacing]

                if rowIdx < numRow and colIdx < numCol:
                    centre = [xNode + 0.5*xSpacing, yNode + 0.5*ySpacing, 0.0]
                    centres.append(centre)

                    for boundaryCoord in boundaryCoords:
                        if xLimit[0] <= boundaryCoord[0] <= xLimit[1] and yLimit[1] <= boundaryCoord[1] <= yLimit[0]:
                            if rowIdx < startRowIdx:
                                startRowIdx = rowIdx
                            if rowIdx > endRowIdx:
                                endRowIdx = rowIdx
                            break

            for n in range(startRowIdx, endRowIdx + 1):
                yNode = ySpacing * n + minY - yOffset
                yLimit = [yNode, yNode + ySpacing]
                inBoundaryCentre = [xNode + 0.5*xSpacing, yNode + 0.5*ySpacing, 0.0]
                inBoundaryCentres.append(inBoundaryCentre)

                densityCount = 0
                for dataCoord in dataCoords:
                    if xLimit[0] <= dataCoord[0] <= xLimit[1] and yLimit[1] <= dataCoord[1] <= yLimit[0]:
                        densityCount += 1

                densityCounts.append(densityCount/totalDendriteCounts)
                dataCentres.append(inBoundaryCentre)

        # mesh = fm.findMeshByDimension(2)
        # bicubicHermiteBasis = fm.createElementbasis(2, Elementbasis.FUNCTION_TYPE_CUBIC_HERMITE)
        # eft = mesh.createElementfieldtemplate(bicubicHermiteBasis)
        # for n in range(4):
        #     eft.setFunctionNumberOfTerms(n * 4 + 4, 0)
        # elementtemplate = mesh.createElementtemplate()
        # elementtemplate.setElementShapeType(Element.SHAPE_TYPE_SQUARE)
        # result = elementtemplate.defineField(coordinates, -1, eft)

        # # create elements
        # elementIdentifier = 1
        # no2 = numRow + 1
        # for e1 in range(numCol):
        #     for e2 in range(numRow):
        #         element = mesh.createElement(elementIdentifier, elementtemplate)
        #         bni = e1 * no2 + e2 + 1
        #         nodeIdentifiers = [bni, bni + 1, bni + no2, bni + no2 + 1]
        #         result = element.setNodesByIdentifier(eft, nodeIdentifiers)
        #         elementIdentifier = elementIdentifier + 1

        densityGroup = AnnotationGroup(region, ("density points", "None"))
        densityNodeGroup = densityGroup.getNodesetGroup(nodes)
        for i in range(len(dataCentres)):
            node = nodes.createNode(nodeIdentifier, nodetemplate)
            cache.setNode(node)
            coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, dataCentres[i])
            node.merge(densityNodetemplate)
            density.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, densityCounts[i])
            densityNodeGroup.addNode(node)
            nodeIdentifier = nodeIdentifier + 1

        fm.endChange()
        return [densityGroup], None

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
