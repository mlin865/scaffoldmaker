"""
Generates a 0-D acupoints as markers in a 3D box.
"""

from __future__ import division

import json
import openpyxl

from cmlibs.utils.zinc.field import findOrCreateFieldStoredMeshLocation
from cmlibs.zinc.element import Element, Elementbasis
from cmlibs.zinc.field import Field
from cmlibs.zinc.node import Node
from scaffoldmaker.annotation.annotationgroup import AnnotationGroup, findOrCreateAnnotationGroupForTerm
from scaffoldmaker.meshtypes.scaffold_base import Scaffold_base
from cmlibs.utils.zinc.field import findOrCreateFieldCoordinates, findOrCreateFieldStoredString, findOrCreateFieldGroup
from scaffoldmaker.utils.eftfactory_tricubichermite import eftfactory_tricubichermite

class MeshType_3d_boxwithacupoints1(Scaffold_base):
    '''
    classdocs
    '''
    @staticmethod
    def getName():
        return '3D Box With Acupoints 1'

    @classmethod
    def generateBaseMesh(cls, region, options):
        """
        :param region: Zinc region to define model in. Must be empty.
        :param options: Dict containing options. See getDefaultOptions().
        :return: [] empty list of AnnotationGroup, None
        """
        coordinateDimensions = 3
        fieldmodule = region.getFieldmodule()
        fieldmodule.beginChange()
        coordinates = findOrCreateFieldCoordinates(fieldmodule, components_count=coordinateDimensions)
        useCrossDerivatives = 'False'

        nodes = fieldmodule.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        nodetemplate = nodes.createNodetemplate()
        nodetemplate.defineField(coordinates)
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_VALUE, 1)
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D_DS1, 1)
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D_DS2, 1)
        if useCrossDerivatives:
            nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D2_DS1DS2, 1)
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D_DS3, 1)
        if useCrossDerivatives:
            nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D2_DS1DS3, 1)
            nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D2_DS2DS3, 1)
            nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D3_DS1DS2DS3, 1)

        mesh = fieldmodule.findMeshByDimension(3)

        tricubichermite = eftfactory_tricubichermite(mesh, useCrossDerivatives)
        eft = tricubichermite.createEftBasic()
        elementtemplate = mesh.createElementtemplate()
        elementtemplate.setElementShapeType(Element.SHAPE_TYPE_CUBE)
        result = elementtemplate.defineField(coordinates, -1, eft)

        cache = fieldmodule.createFieldcache()

        # create nodes
        nodeIdentifier = 1
        x = [0.0, 0.0, 0.0]
        xLimit = [-500.0, 500.0]
        yLimit = [-500.0, 500.0]
        zLimit = [0.0, 1800.0]
        xSpan = xLimit[1] - xLimit[0]
        ySpan = yLimit[1] - yLimit[0]
        zSpan = zLimit[1] - zLimit[0]

        dx_ds1 = [xSpan , 0.0, 0.0]
        dx_ds2 = [0.0, ySpan, 0.0]
        dx_ds3 = [0.0, 0.0, zSpan]

        zero = [0.0, 0.0, 0.0]
        for n3 in range(2):
            x[2] = zLimit[n3]
            for n2 in range(2):
                x[1] = yLimit[n2]
                for n1 in range(2):
                    x[0] = xLimit[n1]
                    node = nodes.createNode(nodeIdentifier, nodetemplate)
                    cache.setNode(node)
                    coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, x)
                    coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, dx_ds1)
                    coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, dx_ds2)
                    coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, dx_ds3)
                    nodeIdentifier = nodeIdentifier + 1

        # create elements
        elementIdentifier = 1
        no2 = 2
        no3 = 2 * no2
        for e3 in range(1):
            for e2 in range(1):
                for e1 in range(1):
                    element = mesh.createElement(elementIdentifier, elementtemplate)
                    bni = e3 * no3 + e2 * no2 + e1 + 1
                    nodeIdentifiers = [bni, bni + 1, bni + no2, bni + no2 + 1, bni + no3, bni + no3 + 1,
                                       bni + no2 + no3, bni + no2 + no3 + 1]
                    result = element.setNodesByIdentifier(eft, nodeIdentifiers)
                    elementIdentifier = elementIdentifier + 1

        fieldmodule.endChange()

        nodes = fieldmodule.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        nodetemplate = nodes.createNodetemplate()
        nodetemplate.defineField(coordinates)
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_VALUE, 1)

        filename1 = "C:\\Users\\mlin865\\map\\packages\\sparc\\scaffoldmaker\\inputFile\\annotatedAcupoints_v1.json"

        with open(filename1) as json_data:
            d1 = json.load(json_data)
            json_data.close()

        nameList = []
        coordinatesList = []
        xiList = []
        for feature in d1:
            marker_name = feature['group']
            marker_point = feature['feature']['geometry']['coordinates'][0]
            nameList.append(marker_name)
            coordinatesList.append(marker_point)
            xi = [marker_point[0]/xSpan + 0.5,
                  marker_point[1]/ySpan + 0.5,
                  marker_point[2]/zSpan]
            xiList.append(xi)

        # Make markers
        markerGroup = findOrCreateFieldGroup(fieldmodule, "marker")
        markerName = findOrCreateFieldStoredString(fieldmodule, name="marker_name")
        markerLocation = findOrCreateFieldStoredMeshLocation(fieldmodule, mesh, name="marker_location")
        markerCoordinates = findOrCreateFieldCoordinates(fieldmodule, name="marker coordinates").castFiniteElement()

        markerPoints = markerGroup.getOrCreateNodesetGroup(nodes)
        markerTemplateInternal = nodes.createNodetemplate()
        markerTemplateInternal.defineField(markerCoordinates)
        markerTemplateInternal.defineField(markerName)
        markerTemplateInternal.defineField(markerLocation)

        annotationGroups = []
        for i in range(len(nameList)):
            group = findOrCreateAnnotationGroupForTerm(annotationGroups, region, (nameList[i], 'None'))
            markerPoint = markerPoints.createNode(nodeIdentifier, markerTemplateInternal)
            nodeIdentifier += 1
            cache.setNode(markerPoint)
            markerCoordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, coordinatesList[i])
            markerName.assignString(cache, nameList[i])
            element = mesh.findElementByIdentifier(1)
            markerLocation.assignMeshLocation(cache, element, xiList[i])
            group.getNodesetGroup(nodes).addNode(markerPoint)
            annotationGroups.append(group)

        return annotationGroups, None
