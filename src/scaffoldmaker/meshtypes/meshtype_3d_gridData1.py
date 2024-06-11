"""
Generates equally distributed nodes in a flat mount sample.
"""

from __future__ import division

from cmlibs.utils.zinc.field import findOrCreateFieldCoordinates, findOrCreateFieldFiniteElement
from cmlibs.zinc.element import Element
from cmlibs.zinc.field import Field
from cmlibs.zinc.node import Node
from scaffoldmaker.meshtypes.scaffold_base import Scaffold_base
from scaffoldmaker.utils.eftfactory_tricubichermite import eftfactory_tricubichermite
from scaffoldmaker.utils.meshrefinement import MeshRefinement

import re


class MeshType_3d_gridData1(Scaffold_base):
    '''
    classdocs
    '''
    @staticmethod
    def getName():
        return '3D Grid Data 1'

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
        useCrossDerivatives = False

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

        # create nodes
        nodeIdentifier = 1
        maxX = 144.37
        minX = 10271.9
        maxY = -9422.59
        minY = -194.91
        numRow = 27 * 2
        numCol = 25 * 2
        z = 0.0

        file = "C:\\Users\\mlin865\\HeatMapDrew-CGRP Female Dorsal 2\\density.csv"
        for index, line in enumerate(open(file)):
            png = line.split(',')[0]
            if png != 'Name':
                rowIdx = int(png.split('-')[0])
                colIdx = int((png.split('-')[1]).split('.')[0])
                x = (maxX - minX)/numCol * (colIdx * 2 - 1) + minX
                y = (maxY - minY)/numRow * (rowIdx * 2 - 1) + minY
                densityValue = float(line.split(',')[1])

                coord = [x, y, z]
                node = nodes.createNode(nodeIdentifier, nodetemplate)
                cache.setNode(node)
                coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, coord)
                node.merge(densityNodetemplate)
                density.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, densityValue)
                nodeIdentifier = nodeIdentifier + 1

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
