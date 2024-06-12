"""
Adds rgb field to exf.
"""

from __future__ import division

from cmlibs.utils.zinc.field import findOrCreateFieldCoordinates, findOrCreateFieldFiniteElement, get_group_list
from cmlibs.utils.zinc.general import ChangeManager
from cmlibs.zinc.element import Element
from cmlibs.zinc.field import Field
from cmlibs.zinc.node import Node
from scaffoldmaker.annotation.annotationgroup import AnnotationGroup
from scaffoldmaker.meshtypes.scaffold_base import Scaffold_base
from scaffoldmaker.utils.eftfactory_tricubichermite import eftfactory_tricubichermite
from scaffoldmaker.utils.meshrefinement import MeshRefinement

import math


class MeshType_3d_addColor1(Scaffold_base):
    '''
    classdocs
    '''
    @staticmethod
    def getName():
        return '3D Add Color 1'

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

        sir = region.createStreaminformationRegion()
        file = "C:\\Users\\mlin865\manInBox\\organs from Japanese\\FJ3362_BP49034_FMA13322_Right clavicle.exf"
        color = fm.createFieldConstant([0.6,0.6,0.1])

        sir.createStreamresourceFile(file)
        region.read(sir)

        with ChangeManager(fm):
            zero = fm.createFieldConstant([0.0, 0.0, 0.0])
            # temporarily rename coordinates to "rgb"
            coordinates.setName("rgb")
            sir = region.createStreaminformationRegion()
            srm = sir.createStreamresourceMemory()
            region.write(sir)
            result, buffer = srm.getBuffer()
            coordinates.setName("coordinates")
            sir = region.createStreaminformationRegion()
            sir.createStreamresourceMemoryBuffer(buffer)
            region.read(sir)
            rgb = fm.findFieldByName("rgb")
            rgb.setTypeCoordinate(False)  # so not picked up as a 'coordinate' field

            fieldassignment = rgb.createFieldassignment(color)
            fieldassignment.assign()

            for valueLabel in [Node.VALUE_LABEL_D_DS1, Node.VALUE_LABEL_D_DS2, Node.VALUE_LABEL_D_DS3]:
                rgbDeriv = fm.createFieldNodeValue(rgb, valueLabel, 1)  # for version 1
                fieldassignment = rgbDeriv.createFieldassignment(zero)
                fieldassignment.assign()
                del rgbDeriv
            del zero

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
