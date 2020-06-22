"""
Generates a 2-D unit plate mesh with variable numbers of elements in 2 directions.
"""

from __future__ import division
import math
from opencmiss.utils.zinc.field import findOrCreateFieldCoordinates, findOrCreateFieldGroup, \
    findOrCreateFieldNodeGroup, findOrCreateFieldStoredMeshLocation, findOrCreateFieldStoredString
from opencmiss.zinc.element import Element, Elementbasis
from opencmiss.zinc.field import Field
from opencmiss.zinc.node import Node
from scaffoldmaker.annotation.annotationgroup import AnnotationGroup, findOrCreateAnnotationGroupForTerm
from scaffoldmaker.meshtypes.scaffold_base import Scaffold_base

class MeshType_2d_plate1(Scaffold_base):
    '''
    classdocs
    '''
    @staticmethod
    def getName():
        return '2D Plate 1'

    @staticmethod
    def getDefaultOptions(parameterSetName='Default'):
        return {
            'Coordinate dimensions' : 3,
            'Number of elements 1' : 1,
            'Number of elements 2' : 1,
            'Use cross derivatives' : False
        }

    @staticmethod
    def getOrderedOptionNames():
        return [
            'Coordinate dimensions',
            'Number of elements 1',
            'Number of elements 2',
            'Use cross derivatives'
        ]

    @staticmethod
    def checkOptions(options):
        if (options['Coordinate dimensions'] < 2) :
            options['Coordinate dimensions'] = 2
        elif (options['Coordinate dimensions'] > 3) :
            options['Coordinate dimensions'] = 3
        if (options['Number of elements 1'] < 1) :
            options['Number of elements 1'] = 1
        if (options['Number of elements 2'] < 1) :
            options['Number of elements 2'] = 1

    @staticmethod
    def generateMesh(region, options):
        """
        :param region: Zinc region to define model in. Must be empty.
        :param options: Dict containing options. See getDefaultOptions().
        :return: None
        """
        coordinateDimensions = options['Coordinate dimensions']
        elementsCount1 = options['Number of elements 1']
        elementsCount2 = options['Number of elements 2']
        useCrossDerivatives = options['Use cross derivatives']

        fm = region.getFieldmodule()
        fm.beginChange()
        coordinates = findOrCreateFieldCoordinates(fm, components_count=coordinateDimensions)

        nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        nodetemplate = nodes.createNodetemplate()
        nodetemplate.defineField(coordinates)
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_VALUE, 1)
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D_DS1, 1)
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D_DS2, 1)
        if useCrossDerivatives:
            nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D2_DS1DS2, 1)

        mesh = fm.findMeshByDimension(2)
        bicubicHermiteBasis = fm.createElementbasis(2, Elementbasis.FUNCTION_TYPE_CUBIC_HERMITE)
        eft = mesh.createElementfieldtemplate(bicubicHermiteBasis)
        if not useCrossDerivatives:
            for n in range(4):
                eft.setFunctionNumberOfTerms(n*4 + 4, 0)
        elementtemplate = mesh.createElementtemplate()
        elementtemplate.setElementShapeType(Element.SHAPE_TYPE_SQUARE)
        result = elementtemplate.defineField(coordinates, -1, eft)

        cache = fm.createFieldcache()

        sampleGroup = AnnotationGroup(region, ("sample", ""))
        sampleMeshGroup = sampleGroup.getMeshGroup(mesh)
        annotationGroups = [sampleGroup]

        # annotation fiducial points
        markerGroup = findOrCreateFieldGroup(fm, "marker")
        markerName = findOrCreateFieldStoredString(fm, name="marker_name")
        markerLocation = findOrCreateFieldStoredMeshLocation(fm, mesh, name="marker_location")

        markerPoints = findOrCreateFieldNodeGroup(markerGroup, nodes).getNodesetGroup()
        markerTemplateInternal = nodes.createNodetemplate()
        markerTemplateInternal.defineField(markerName)
        markerTemplateInternal.defineField(markerLocation)

        # create nodes
        nodeIdentifier = 1
        markerIdentifier = 1000001
        x = [ 0.0, 0.0, 0.0 ]
        dx_ds1 = [ 1.0 / elementsCount1, 0.0, 0.0 ]
        dx_ds2 = [ 0.0, 1.0 / elementsCount2, 0.0 ]
        zero = [ 0.0, 0.0, 0.0 ]
        for n2 in range(elementsCount2 + 1):
            x[1] = n2 / elementsCount2
            for n1 in range(elementsCount1 + 1):
                x[0] = n1 / elementsCount1
                node = nodes.createNode(nodeIdentifier, nodetemplate)
                cache.setNode(node)
                coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, x)
                coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, dx_ds1)
                coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, dx_ds2)
                if useCrossDerivatives:
                    coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, zero)
                nodeIdentifier = nodeIdentifier + 1

        # create elements
        elementIdentifier = 1
        no2 = (elementsCount1 + 1)
        for e2 in range(elementsCount2):
            for e1 in range(elementsCount1):
                element = mesh.createElement(elementIdentifier, elementtemplate)
                bni = e2*no2 + e1 + 1
                nodeIdentifiers = [ bni, bni + 1, bni + no2, bni + no2 + 1 ]
                result = element.setNodesByIdentifier(eft, nodeIdentifiers)
                elementIdentifier = elementIdentifier + 1
                sampleMeshGroup.addElement(element)

        # Add markers
        for n2 in range(2):
            for n1 in range(2):
                if n2 == 0 and n1 == 0:
                    addMarker = {"name": "bottom left", "xi": [0.0, 0.0, 0.0]}
                    elementIdentifierMarker = 1
                if n2 == 0 and n1 == 1:
                    addMarker = {"name": "bottom right", "xi": [1.0, 0.0, 0.0]}
                    elementIdentifierMarker = elementsCount1
                if n2 == 1 and n1 == 0:
                    addMarker = {"name": "top left", "xi": [0.0, 1.0, 0.0]}
                    elementIdentifierMarker = elementsCount1 * (elementsCount2 - 1) + 1
                if n2 == 1 and n1 == 1:
                    addMarker = {"name": "top right", "xi": [1.0, 1.0, 0.0]}
                    elementIdentifierMarker = elementsCount1 * elementsCount2
                markerPoint = markerPoints.createNode(markerIdentifier, markerTemplateInternal)
                markerIdentifier += 1
                cache.setNode(markerPoint)
                markerName.assignString(cache, addMarker["name"])
                element = mesh.findElementByIdentifier(elementIdentifierMarker)
                markerLocation.assignMeshLocation(cache, element, addMarker["xi"])

        fm.defineAllFaces()
        mesh1d = fm.findMeshByDimension(1)
        sampleGroup.addSubelements()
        is_sampleLines = sampleGroup.getFieldElementGroup(mesh1d)
        is_exterior = fm.createFieldIsExterior()
        # For Gould's data
        is_submucosa = fm.createFieldAnd(is_sampleLines, is_exterior)
        submucosaGroup = findOrCreateAnnotationGroupForTerm(annotationGroups, region, ("Submucosa of transverse colon", ""))
        submucosaGroup.getMeshGroup(mesh1d).addElementsConditional(is_submucosa)

        # # For PuQing's data
        # is_exterior_face_xi2_0 = fm.createFieldAnd(is_exterior, fm.createFieldIsOnFace(Element.FACE_TYPE_XI2_0))
        # is_exterior_face_xi2_1 = fm.createFieldAnd(is_exterior, fm.createFieldIsOnFace(Element.FACE_TYPE_XI2_1))
        # is_bottom = fm.createFieldAnd(is_sampleLines, is_exterior_face_xi2_0)
        # is_top = fm.createFieldAnd(is_sampleLines, is_exterior_face_xi2_1)
        # bottomGroup = findOrCreateAnnotationGroupForTerm(annotationGroups, region, ("ImageOutlineBottom", ""))
        # bottomGroup.getMeshGroup(mesh1d).addElementsConditional(is_bottom)
        # topGroup = findOrCreateAnnotationGroupForTerm(annotationGroups, region, ("ImageOutlineTop", ""))
        # topGroup.getMeshGroup(mesh1d).addElementsConditional(is_top)

        fm.endChange()
        