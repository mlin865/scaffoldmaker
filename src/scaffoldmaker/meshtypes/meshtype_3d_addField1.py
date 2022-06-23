"""
Combine mapped data with rgb and radius field for Jack Cheng's data
"""

from scaffoldmaker.annotation.annotationgroup import AnnotationGroup, getAnnotationGroupForTerm, findOrCreateAnnotationGroupForTerm
from scaffoldmaker.annotation.stomach_terms import get_stomach_term
from scaffoldmaker.meshtypes.scaffold_base import Scaffold_base
from opencmiss.zinc.element import Element, Elementbasis
from opencmiss.zinc.field import Field
from opencmiss.zinc.node import Node
from opencmiss.utils.zinc.field import findOrCreateFieldCoordinates, findOrCreateFieldFiniteElement
from opencmiss.utils.zinc.finiteelement import get_element_node_identifiers


class MeshType_3d_addField1(Scaffold_base):
    '''
    Read in a mapped ex file and combine it with the radius and rgb field from the original ex file
    '''

    @staticmethod
    def getName():
        return 'Add field 1'

    @staticmethod
    def getParameterSetNames():
        return [
            'Default']

    @classmethod
    def getDefaultOptions(cls, parameterSetName='Default'):
        return {
            'Refine': False
        }

    @staticmethod
    def getOrderedOptionNames():
        return [
            'Refine']

    @classmethod
    def generateBaseMesh(cls, region, options):
        """
        Generate the base tricubic Hermite mesh.
        :param region: Zinc region to define model in. Must be empty.
        :param options: Dict containing options. See getDefaultOptions().
        :return: annotationGroups
        """
        # Turn off these 2 lines to see graphics
        # context = Context("Test")
        # region = context.getDefaultRegion()

        # Extract radius and rgb from file first
        radiusList= []
        rgbList = []

        sir = region.createStreaminformationRegion()
        # sir.createStreamresourceFile('C:\\Users\\mlin865\\dev\\Test example for stomach flat scaffold\\mapping\\mapped3DCombined.ex')
        sir.createStreamresourceFile('C:\\Users\\mlin865\\dev\\Test example for stomach flat scaffold\\CGRP.ex')
        region.read(sir)

        fieldModule = region.getFieldmodule()
        coordinates = findOrCreateFieldCoordinates(fieldModule)
        radius = findOrCreateFieldFiniteElement(fieldModule, name='radius', components_count=1, type_coordinate=False)
        rgb = findOrCreateFieldFiniteElement(fieldModule, name='rgb', components_count=3, type_coordinate=False)

        nodeset = fieldModule.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        mesh = fieldModule.findMeshByDimension(3)

        fieldcache = fieldModule.createFieldcache()

        nodeIter = nodeset.createNodeiterator()
        node = nodeIter.next()

        fieldcache.setNode(node)
        while node.isValid():
            identifier = node.getIdentifier()
            fieldcacheCheck = fieldcache.setNode(node)
            result_radius, pt_radius = radius.evaluateReal(fieldcache, 1) # doesnt generate the derivatives
            result_rgb, pt_rgb = rgb.getNodeParameters(fieldcache, -1, Node.VALUE_LABEL_VALUE, 1, 3)
            # print('Node', identifier, result_rgb, pt_rgb)

            # do stuff with node
            node = nodeIter.next()
            radiusList.append(pt_radius)
            rgbList.append(pt_rgb)

        del sir
        del fieldModule
        del rgb
        del radius

        sir = region.createStreaminformationRegion()
        sir.createStreamresourceFile('C:\\Users\\mlin865\\dev\\Test example for stomach flat scaffold\\mapping\\mapped2DCombined.exf')
        region.read(sir)

        fieldModule = region.getFieldmodule()
        coordinates = findOrCreateFieldCoordinates(fieldModule)
        nodeset = fieldModule.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)

        # Create radius and rgb fields
        radius = findOrCreateFieldFiniteElement(fieldModule, name='radius', components_count=1, type_coordinate=False)
        radiusNodetemplate1 = nodeset.createNodetemplate()
        radiusNodetemplate1.defineField(radius)

        rgb = findOrCreateFieldFiniteElement(fieldModule, name='rgb', components_count=3, type_coordinate=False)
        rgbNodetemplate1 = nodeset.createNodetemplate()
        rgbNodetemplate1.defineField(rgb)

        mesh = fieldModule.findMeshByDimension(3)
        fieldcache = fieldModule.createFieldcache()

        nodeIter = nodeset.createNodeiterator()
        node = nodeIter.next()

        # print('coordinates.isValid() =', coordinates.isValid())
        # print('fieldcache.isValid() = ', fieldcache.isValid())

        fieldcache.setNode(node)
        while node.isValid():
            identifier = node.getIdentifier()
            fieldcacheCheck = fieldcache.setNode(node)
            node.merge(radiusNodetemplate1)
            node.merge(rgbNodetemplate1)
            fieldcache.setNode(node)
            radius.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_VALUE, 1, radiusList[identifier - 1])
            rgb.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_VALUE, 1, rgbList[identifier - 1])
            node = nodeIter.next()

        # Set up elements
        elementtemplate = mesh.createElementtemplate()

        # Radius field
        linearLagrangeBasis = fieldModule.createElementbasis(3, Elementbasis.FUNCTION_TYPE_LINEAR_LAGRANGE)
        eft8 = mesh.createElementfieldtemplate(linearLagrangeBasis)
        radiusElementtemplate = mesh.createElementtemplate()
        radiusElementtemplate.setElementShapeType(Element.SHAPE_TYPE_CUBE)
        radiusElementtemplate.defineField(radius, -1, eft8)

        # RGB Field
        rgbElementtemplate = mesh.createElementtemplate()

        elementIter = mesh.createElementiterator()
        element = elementIter.next()

        while element.isValid():
            # do stuff with element
            eft = element.getElementfieldtemplate(coordinates, -1)
            rgbElementtemplate.defineField(rgb, -1, eft) # RGB field
            nodeIdentifiers = get_element_node_identifiers(element, eft)

            result1 = elementtemplate.defineField(coordinates, -1, eft)
            result2 = element.merge(elementtemplate)
            element.merge(radiusElementtemplate)
            element.merge(rgbElementtemplate)
            element.setNodesByIdentifier(eft, nodeIdentifiers)
            if eft.getNumberOfLocalScaleFactors() == 1:
                element.setScaleFactors(eft, [-1.0])
            # print('element', element.getIdentifier(), result1, result2)
            element = elementIter.next()

        return []