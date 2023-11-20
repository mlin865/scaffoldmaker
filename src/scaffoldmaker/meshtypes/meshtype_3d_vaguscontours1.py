"""
Generates a 2D contours based outer surface of left vagal trunk from the Japanese dataset
"""

import os
import re

from scaffoldmaker.meshtypes.scaffold_base import Scaffold_base
from cmlibs.zinc.element import Element, Elementbasis
from cmlibs.zinc.field import Field
from cmlibs.zinc.node import Node
from cmlibs.utils.zinc.field import findOrCreateFieldCoordinates
from cmlibs.utils.zinc.finiteelement import get_element_node_identifiers


class MeshType_3d_vaguscontours1(Scaffold_base):
    '''
    Generates a 2D vagus contours mesh from Japanese dataset.
    '''

    @staticmethod
    def getName():
        return '3D Vagus Contours 1'

    @staticmethod
    def getParameterSetNames():
        return [
            'Default']

    @classmethod
    def getDefaultOptions(cls, parameterSetName='Default'):
        return {
            # 'Refine': False,
            # 'Refine number of elements around': 2,
            # 'Refine number of elements along': 2,
            # 'Refine number of elements through wall': 1
        }

    @staticmethod
    def getOrderedOptionNames():
        return []
            # 'Refine',
            # 'Refine number of elements around',
            # 'Refine number of elements along',
            # 'Refine number of elements through wall' ]

    # @classmethod
    # def checkOptions(cls, options):
    #     for key in [
    #         'Refine number of elements around',
    #         'Refine number of elements along',
    #         'Refine number of elements through wall']:
    #         if options[key] < 1:
    #             options[key] = 1

    @classmethod
    def generateBaseMesh(cls, region, options):
        """
        Generate the base tricubic Hermite mesh.
        :param region: Zinc region to define model in. Must be empty.
        :param options: Dict containing options. See getDefaultOptions().
        :return: annotationGroups
        """
        inputFile = 'C:\\Users\\mlin865\\Vagus\\Japanese dataset_exf\\test_dump\\top_1.json'

        # Extract values from webGL file
        copyValue = False
        allValues = []

        for index, line in enumerate(open(inputFile)):
            if re.match('\t],', line.split(' ')[0]):
                copyValue = False
                break

            if copyValue == True:
                tmp = line.split('\t')
                values = tmp[2].split(',')
                for t in range(len(values) - 1):
                    value = float(values[t])
                    allValues.append(value)

            if re.match('\t\"vertices\"', line.split(' ')[0]):
                copyValue = True

        # Make coordinates
        allCoordinates = []
        idx = 0
        while idx < len(allValues) - 3:
            coord = [allValues[idx], allValues[idx + 1], allValues[idx + 2]]
            idx += 3
            allCoordinates.append(coord)

        print('Number of coordinates', len(allCoordinates))

        # remove duplicates
        cleanList = []
        for i in allCoordinates:
            if i not in cleanList:
                cleanList.append(i)

        print('len of cleanList', len(cleanList))

        # zComp = allCoordinates[0][2]
        # allContours = []
        # contour = [allCoordinates[0]]
        # zCompList = [zComp]
        #
        # for i in range(1, len(allCoordinates)):
        #     if abs(allCoordinates[i][2] - zComp) < 1e-3:
        #         contour.append(allCoordinates[i])
        #     else:
        #         zExists = False
        #         for z in range(len(zCompList)):
        #             if abs(zCompList[z] - zComp) < 1e-3: # part of extracted contours
        #                 if allContours == []:
        #                     allContours.append(contour)
        #                 else:
        #                     allContours[z] += contour
        #                 zExists = True
        #                 break
        #         if not zExists:
        #             zCompList.append(zComp)
        #             allContours.append(contour)
        #
        #         contour = [allCoordinates[i]]
        #         zComp = allCoordinates[i][2]
        #
        # print(zCompList)
        # numVertices = 0
        # for i in range(len(allContours)):
        #     print(len(allContours[i]))
        #     numVertices += len(allContours[i])
        # print('all vertices', numVertices)

        # Create nodes
        fm = region.getFieldmodule()
        fm.beginChange()
        coordinates = findOrCreateFieldCoordinates(fm)
        cache = fm.createFieldcache()

        nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        nodetemplate = nodes.createNodetemplate()
        nodetemplate.defineField(coordinates)
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_VALUE, 1)
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D_DS1, 1)

        nodeIdentifier = 1
        for i in range(len(cleanList)):
            node = nodes.createNode(nodeIdentifier, nodetemplate)
            cache.setNode(node)
            coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, cleanList[i])
            coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, [0.0, 0.0, 0.0])
            nodeIdentifier += 1

        # # Create elements
        # mesh = fm.findMeshByDimension(1)
        # cubicHermiteBasis = fm.createElementbasis(1, Elementbasis.FUNCTION_TYPE_CUBIC_HERMITE)
        # eft = mesh.createElementfieldtemplate(cubicHermiteBasis)
        # elementtemplate = mesh.createElementtemplate()
        # elementtemplate.setElementShapeType(Element.SHAPE_TYPE_LINE)
        # result = elementtemplate.defineField(coordinates, -1, eft)
        #
        # elementIdentifier = 1
        # for e in range(1):
        #     for e1 in range(1, 3):
        #         element = mesh.createElement(elementIdentifier, elementtemplate)
        #         element.setNodesByIdentifier(eft, [e * 3 + e1, e * 3 + e1 + 1])
        #         print([e * 3 + e1, e * 3 + e1 + 1])
        #         elementIdentifier = elementIdentifier + 1

        # for c in range(len(allContours)):
        #     for n in range(len(allContours[c])):
        #         node = nodes.createNode(nodeIdentifier, nodetemplate)
        #         cache.setNode(node)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, allContours[c][n])
        #         # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, dx_ds1)
        #         nodeIdentifier += 1

        fm.endChange()

        return [], None

    @classmethod
    def refineMesh(cls, meshrefinement, options):
        """
        Refine source mesh into separate region, with change of basis.
        :param meshrefinement: MeshRefinement, which knows source and target region.
        :param options: Dict containing options. See getDefaultOptions().
        """
        refineElementsCountAround = options['Refine number of elements around']
        refineElementsCountAlong = options['Refine number of elements along']
        refineElementsCountThroughWall = options['Refine number of elements through wall']

        meshrefinement.refineAllElementsCubeStandard3d(refineElementsCountAround, refineElementsCountAlong,
                                                       refineElementsCountThroughWall)
        return
