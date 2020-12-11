"""
Generates a 3-D mesh for the last segment of the cecum along the central line, with variable
numbers of elements around, along and through wall, with
variable radius and thickness along.
"""

import copy
import math
from scaffoldmaker.annotation.annotationgroup import AnnotationGroup
from scaffoldmaker.annotation.colon_terms import get_colon_term
from scaffoldmaker.meshtypes.meshtype_1d_path1 import MeshType_1d_path1, extractPathParametersFromRegion
from scaffoldmaker.meshtypes.meshtype_3d_colonsegment1 import ColonSegmentTubeMeshInnerPoints, \
    createHalfSetInterHaustralSegment, createHalfSetIntraHaustralSegment, getFullProfileFromHalfHaustrum,\
    getTeniaColi, createNodesAndElementsTeniaColi, getCircleXandD1FromRadians
from scaffoldmaker.meshtypes.meshtype_3d_ostium1 import MeshType_3d_ostium1, generateOstiumMesh
from scaffoldmaker.meshtypes.scaffold_base import Scaffold_base
from scaffoldmaker.scaffoldpackage import ScaffoldPackage
from scaffoldmaker.utils.annulusmesh import createAnnulusMesh3d
from scaffoldmaker.utils.bifurcation import get_bifurcation_triple_point
from scaffoldmaker.utils.eft_utils import remapEftNodeValueLabel, scaleEftNodeValueLabels, setEftScaleFactorIds, remapEftLocalNodes
from scaffoldmaker.utils import interpolation as interp
from scaffoldmaker.utils import matrix
from scaffoldmaker.utils.tracksurface import TrackSurface, TrackSurfacePosition
from scaffoldmaker.utils import tubemesh
from scaffoldmaker.utils import vector
from scaffoldmaker.utils.zinc_utils import exnodeStringFromNodeValues, mesh_destroy_elements_and_nodes_by_identifiers
from opencmiss.utils.zinc.general import ChangeManager
from opencmiss.zinc.field import Field, FieldGroup
from opencmiss.zinc.node import Node
from opencmiss.utils.zinc.field import findOrCreateFieldCoordinates #km
from opencmiss.zinc.element import Element, Elementbasis # km
from scaffoldmaker.utils.eftfactory_bicubichermitelinear import eftfactory_bicubichermitelinear # KM
from scaffoldmaker.utils.eftfactory_tricubichermite import eftfactory_tricubichermite # KM


class MeshType_3d_cecumjunctionsegment1(Scaffold_base):
    '''
    Generates a 3-D mesh for the last segment of the cecum with variable numbers
    of elements around, along the central line, and through wall.
    The cecum is created by a function that generates a cecum
    segment.
    '''

    ostiumDefaultScaffoldPackages = {
        'Pig 1': ScaffoldPackage(MeshType_3d_ostium1, {
            'scaffoldSettings': {
                'Number of vessels': 1,
                'Number of elements across common': 2,
                'Number of elements around ostium': 8,
                'Number of elements along': 2,
                'Number of elements through wall': 1,  # not implemented for > 1
                'Unit scale': 1.0,
                'Outlet': False,
                'Ostium diameter': 20.0,
                'Ostium length': 10.0,
                'Ostium wall thickness': 2.0,
                'Ostium inter-vessel distance': 0.0,
                'Ostium inter-vessel height': 0.0,
                'Use linear through ostium wall': True,
                'Vessel end length factor': 1.0,
                'Vessel inner diameter': 10.0,
                'Vessel wall thickness': 2.0,
                'Vessel angle 1 degrees': 0.0,
                'Vessel angle 1 spread degrees': 0.0,
                'Vessel angle 2 degrees': 0.0,
                'Use linear through vessel wall': True,
                'Use cross derivatives': False,
                'Refine': False,
                'Refine number of elements around': 4,
                'Refine number of elements along': 4,
                'Refine number of elements through wall': 1
            },
        })
    }

    @staticmethod
    def getName():
        return '3D Cecum Junction Segment 1'

    @staticmethod
    def getParameterSetNames():
        return [
            'Default',
            'Pig 1']

    @classmethod
    def getDefaultOptions(cls, parameterSetName='Default'):
        ostiumOption = cls.ostiumDefaultScaffoldPackages['Pig 1']

        options = {
            'Number of elements around tenia coli': 2,
            'Number of elements around haustrum': 8,
            'Number of elements along segment': 8,
            'Number of elements through wall': 1,
            'Segment length': 36.0,
            'Start inner radius': 38.0,
            'Start inner radius derivative': 0.0,
            'End inner radius': 38.0,
            'End inner radius derivative': 0.0,
            'Corner inner radius factor': 0.5,
            'Haustrum inner radius factor': 0.25,
            'Segment length end derivative factor': 1.0,
            'Segment length mid derivative factor': 4.0,
            'Number of tenia coli': 3,
            'Start tenia coli width': 5.0,
            'Start tenia coli width derivative': 0.0,
            'End tenia coli width': 5.0,
            'End tenia coli width derivative': 0.0,
            'Tenia coli thickness': 0.5,
            'Wall thickness': 2.0,
            'Ileocecal junction': copy.deepcopy(ostiumOption),
            'Ileocecal junction position along factor': 0.5,
            'Use cross derivatives': False,
            'Use linear through wall': True,
            'Refine': False,
            'Refine number of elements around': 1,
            'Refine number of elements along': 1,
            'Refine number of elements through wall': 1
        }
        cls.updateSubScaffoldOptions(options)
        return options

    @staticmethod
    def getOrderedOptionNames():
        return [
            'Number of elements around tenia coli',
            'Number of elements around haustrum',
            'Number of elements along segment',
            'Number of elements through wall',
            'Segment length',
            'Start inner radius',
            'Start inner radius derivative',
            'End inner radius',
            'End inner radius derivative',
            'Corner inner radius factor',
            'Haustrum inner radius factor',
            'Segment length end derivative factor',
            'Segment length mid derivative factor',
            'Number of tenia coli',
            'Start tenia coli width',
            'Start tenia coli width derivative',
            'End tenia coli width',
            'End tenia coli width derivative',
            'Tenia coli thickness',
            'Wall thickness',
            'Ileocecal junction',
            'Ileocecal junction position along factor',
            'Use cross derivatives',
            'Use linear through wall',
            'Refine',
            'Refine number of elements around',
            'Refine number of elements along',
            'Refine number of elements through wall']

    @classmethod
    def getOptionValidScaffoldTypes(cls, optionName):
        if optionName == 'Ileocecal junction':
            return [MeshType_3d_ostium1]
        return []

    @classmethod
    def getOptionScaffoldTypeParameterSetNames(cls, optionName, scaffoldType):
        if optionName == 'Ileocecal junction':
            return list(cls.ostiumDefaultScaffoldPackages.keys())
        assert scaffoldType in cls.getOptionValidScaffoldTypes(
            optionName), cls.__name__ + '.getOptionScaffoldTypeParameterSetNames.  ' + \
                         'Invalid option \'' + optionName + '\' scaffold type ' + scaffoldType.getName()
        return scaffoldType.getParameterSetNames()

    @classmethod
    def getOptionScaffoldPackage(cls, optionName, scaffoldType, parameterSetName=None):
        '''
        :param parameterSetName:  Name of valid parameter set for option Scaffold, or None for default.
        :return: ScaffoldPackage.
        '''
        if parameterSetName:
            assert parameterSetName in cls.getOptionScaffoldTypeParameterSetNames(optionName, scaffoldType), \
                'Invalid parameter set ' + str(parameterSetName) + ' for scaffold ' + str(
                    scaffoldType.getName()) + ' in option ' + str(optionName) + ' of scaffold ' + cls.getName()
        if optionName == 'Ileocecal junction':
            if not parameterSetName:
                parameterSetName = list(cls.ostiumDefaultScaffoldPackages.keys())[0]
            return copy.deepcopy(cls.ostiumDefaultScaffoldPackages[parameterSetName])
        assert False, cls.__name__ + '.getOptionScaffoldPackage:  Option ' + optionName + ' is not a scaffold'

    @classmethod
    def checkOptions(cls, options):
        if not options['Ileocecal junction'].getScaffoldType() in cls.getOptionValidScaffoldTypes('Ileocecal junction'):
            options['Ileocecal junction'] = cls.getOptionScaffoldPackage('Ileocecal junction', MeshType_3d_ostium1)
        for key in [
            'Refine number of elements around',
            'Refine number of elements along',
            'Refine number of elements through wall']:
            if options[key] < 1:
                options[key] = 1
        for key in [
            'Number of elements around tenia coli',
            'Number of elements around haustrum',
            'Number of elements along segment',
            'Segment length',
            'Start inner radius',
            'Start inner radius derivative',
            'End inner radius',
            'End inner radius derivative',
            'Corner inner radius factor',
            'Haustrum inner radius factor',
            'Segment length end derivative factor',
            'Segment length mid derivative factor',
            'Number of tenia coli',
            'Start tenia coli width',
            'Start tenia coli width derivative',
            'End tenia coli width',
            'End tenia coli width derivative',
            'Ileocecal junction position along factor',
            'Tenia coli thickness',
            'Wall thickness']:
            if options[key] < 0.0:
                options[key] = 0.0
            if options['Number of elements through wall'] != 1:
                options['Number of elements through wall'] = 1
            if options['Ileocecal junction position along factor'] > 1.0:
                options['Ileocecal junction position along factor'] = 1.0

    @classmethod
    def updateSubScaffoldOptions(cls, options):
        '''
        Update ostium sub-scaffold options which depend on parent options.
        '''
        wallThickness = options['Wall thickness']
        ostiumOptions = options['Ileocecal junction']
        ostiumSettings = ostiumOptions.getScaffoldSettings()
        ostiumSettings['Ostium wall thickness'] = wallThickness

    @classmethod
    def generateBaseMesh(cls, region, options):
        """
        Generate the base tricubic Hermite mesh. See also generateMesh().
        :param region: Zinc region to define model in. Must be empty.
        :param options: Dict containing options. See getDefaultOptions().
        :return: annotationGroups
        """
        startPhase = 0.0
        elementsCountAroundTC = options['Number of elements around tenia coli']
        elementsCountAroundHaustrum = options['Number of elements around haustrum']
        elementsCountAlongSegment = options['Number of elements along segment']
        elementsCountThroughWall = options['Number of elements through wall']
        segmentLength = options['Segment length']
        startInnerRadius = options['Start inner radius']
        startInnerRadiusDerivative = options['Start inner radius derivative']
        endInnerRadius = options['End inner radius']
        endInnerRadiusDerivative = options['End inner radius derivative']
        cornerInnerRadiusFactor = options['Corner inner radius factor']
        haustrumInnerRadiusFactor = options['Haustrum inner radius factor']
        segmentLengthEndDerivativeFactor = options['Segment length end derivative factor']
        segmentLengthMidDerivativeFactor = options['Segment length mid derivative factor']
        tcCount = options['Number of tenia coli']
        startTCWidth = options['Start tenia coli width']
        startTCWidthDerivative = options['Start tenia coli width derivative']
        endTCWidth = options['End tenia coli width']
        endTCWidthDerivative = options['End tenia coli width derivative']
        tcThickness = options['Tenia coli thickness']
        wallThickness = options['Wall thickness']
        useCrossDerivatives = options['Use cross derivatives']
        useCubicHermiteThroughWall = not(options['Use linear through wall'])
        elementsCountAlong = elementsCountAlongSegment
        elementsCountAround = (elementsCountAroundTC + elementsCountAroundHaustrum)*tcCount
        wallThicknessList = [wallThickness] * (elementsCountAlongSegment + 1)

        # Factor when scaled with segmentLength will give distance between the
        # junction and distal end of the cecum
        ostiumPositionAlongFactor = options['Ileocecal junction position along factor']
        ostiumOptions = options['Ileocecal junction']
        ostiumSettings = ostiumOptions.getScaffoldSettings()
        ostiumDiameter = ostiumSettings['Ostium diameter']

        #############################################################################################################
        # nodeIdentifier = 1
        # elementIdentifier = 1
        zero = [0.0, 0.0, 0.0]

        fm = region.getFieldmodule()
        fm.beginChange()
        cache = fm.createFieldcache()

        # Coordinates field
        coordinates = findOrCreateFieldCoordinates(fm)
        nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        nodetemplate = nodes.createNodetemplate()
        nodetemplate.defineField(coordinates)
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_VALUE, 1)
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D_DS1, 1)
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D_DS2, 1)
        if useCrossDerivatives:
            nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D2_DS1DS2, 1)
        if useCubicHermiteThroughWall:
            nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D_DS3, 1)
            if useCrossDerivatives:
                nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D2_DS1DS3, 1)
                nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D2_DS2DS3, 1)
                nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D3_DS1DS2DS3, 1)
        ######################################################################################################

        firstNodeIdentifier = 1
        firstElementIdentifier = 1

        # Generate variation of radius & tc width along length
        innerRadiusAlongCecum = []
        dInnerRadiusAlongCecum = []
        tcWidthAlongCecum = []

        closedProximalEnd = True

        for n2 in range(elementsCountAlongSegment + 1):
            xi = 1/elementsCountAlongSegment * n2

            radius = interp.interpolateCubicHermite([startInnerRadius], [startInnerRadiusDerivative],
                                                    [endInnerRadius], [endInnerRadiusDerivative], xi)[0]
            innerRadiusAlongCecum.append(radius)
            dRadius = interp.interpolateCubicHermiteDerivative([startInnerRadius], [startInnerRadiusDerivative],
                                                               [endInnerRadius], [endInnerRadiusDerivative], xi)[0]
            dInnerRadiusAlongCecum.append(dRadius)
            tcWidth = interp.interpolateCubicHermite([startTCWidth], [startTCWidthDerivative],
                                                     [endTCWidth], [endTCWidthDerivative], xi)[0]
            tcWidthAlongCecum.append(tcWidth)

        haustrumInnerRadiusFactorAlongCecum = [haustrumInnerRadiusFactor] * (elementsCountAlong + 1)

        xToSample = []
        d1ToSample = []
        d2ToSample = []

        elementsCountAroundHalfHaustrum = int((elementsCountAroundTC + elementsCountAroundHaustrum)*0.5)

        # Create annotation
        cecumGroup = AnnotationGroup(region, get_colon_term("caecum"))

        annotationGroupsAlong = []
        for i in range(elementsCountAlong):
            annotationGroupsAlong.append([ ])

        annotationGroupsThroughWall = []
        for i in range(elementsCountThroughWall):
            annotationGroupsThroughWall.append([ ])

        annotationGroups = []

        sampleElementOut = 20
        xHalfSetStart, d1HalfSetStart = createHalfSetInterHaustralSegment(
            elementsCountAroundTC, elementsCountAroundHaustrum, tcCount, startTCWidth, startInnerRadius,
            cornerInnerRadiusFactor, sampleElementOut)

        d2HalfSetStart = []
        for i in range(len(xHalfSetStart)):
            d2HalfSetStart.append([0.0, 0.0, 0.0])

        xStart, d1Start, d2Start = getFullProfileFromHalfHaustrum(xHalfSetStart, d1HalfSetStart, d2HalfSetStart, tcCount)

        # d3UnitStart = []
        # for n in range(len(xStart)):
        #     print(d1Start[n], d2Start[n])
        #     d3 = vector.normalise(vector.crossproduct3(d1Start[n], d2Start[n]))
        #     d3UnitStart.append(d3)

        ##############################################################################################
        # for n in range(len(xStart)):
        #     node = nodes.createNode(nodeIdentifier, nodetemplate)
        #     cache.setNode(node)
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, xStart[n])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, zero)
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, d1Start[n])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, zero)
        #     if useCrossDerivatives:
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS3, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS2DS3, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D3_DS1DS2DS3, 1, zero)
        #     # print('NodeIdentifier = ', nodeIdentifier, d1Start[n]) #, d1[n], d2[n])
        #     nodeIdentifier = nodeIdentifier + 1
        ###########################################################################################

        # End cross-sectional profile
        endTCCount = 2
        endCornerInnerRadiusFactor = 0

        xHalfSetEnd, d1HalfSetEnd = createHalfSetInterHaustralSegment(
            elementsCountAroundTC, elementsCountAroundHaustrum, endTCCount, endTCWidth, endInnerRadius,
            endCornerInnerRadiusFactor, sampleElementOut)

        d2HalfSetEnd = []
        for i in range(len(xHalfSetEnd)):
            xHalfSetEnd[i][2] += segmentLength # sxRefList[-1][2]
            d2HalfSetEnd.append([0.0, 0.0, 0.0])

        x, d1, d2 = getFullProfileFromHalfHaustrum(xHalfSetEnd, d1HalfSetEnd, d2HalfSetEnd, endTCCount)

        # Rotate end profile such that third cecum tc sits between two colon tc
        xEnd = []
        d1End = []
        d2End = []
        # d3UnitEnd = []
        for n in range(len(x)):
            xEnd.append(matrix.rotateAboutZAxis(x[n], math.pi* -0.167))
            d1Rot = matrix.rotateAboutZAxis(d1[n], math.pi * -0.167)
            d1End.append(d1Rot)
            d2Rot = matrix.rotateAboutZAxis(d2[n], math.pi * -0.167)
            d2End.append(d2Rot)
            # d3UnitEnd.append(vector.normalise(vector.crossproduct3(d1, d2)))
        ##############################################################################################
        # for n in range(len(xEnd)):
        #     node = nodes.createNode(nodeIdentifier, nodetemplate)
        #     cache.setNode(node)
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, xEnd[n])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, d1End[n])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, d2End[n])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, zero)
        #     if useCrossDerivatives:
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS3, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS2DS3, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D3_DS1DS2DS3, 1, zero)
        #     # print('NodeIdentifier = ', nodeIdentifier, xEnd[n]) #, d1[n], d2[n])
        #     nodeIdentifier = nodeIdentifier + 1
        ###########################################################################################

        # Create track surface for ileo-cecal junction
        elementsAroundTrackSurface = elementsCountAroundHaustrum
        elementsAlongTrackSurface = elementsCountAlongSegment
        tc2StartIdx = int(elementsCountAroundTC * 0.5 + elementsCountAroundHaustrum)

        # Get outer coordinates for start and end profile for track surface
        tracksurfaceStartIdx = tc2StartIdx + elementsCountAroundTC + int(elementsCountAroundHaustrum * 0.5) + 1
        xStartInnerTracksurface = xStart[
                                  tracksurfaceStartIdx: tracksurfaceStartIdx + elementsCountAroundHaustrum + 1]
        d1StartInnerTracksurface = d1Start[
                                  tracksurfaceStartIdx: tracksurfaceStartIdx + elementsCountAroundHaustrum + 1]

        d2DV = vector.normalise([0.0, 0.0, segmentLength])
        xStartOuterTracksurface = getOuterTrackSurfaceFromInner(xStartInnerTracksurface, d1StartInnerTracksurface, d2DV, wallThicknessList[0])

        tracksurfaceEndIdx = tc2StartIdx + elementsCountAroundTC
        xEndInnerTracksurface = xEnd[tracksurfaceEndIdx: tracksurfaceEndIdx + elementsCountAroundHaustrum + 1]
        d1EndInnerTracksurface = d1End[tracksurfaceEndIdx: tracksurfaceEndIdx + elementsCountAroundHaustrum + 1]
        xEndOuterTracksurface = getOuterTrackSurfaceFromInner(xEndInnerTracksurface, d1EndInnerTracksurface, d2DV,
                                                                wallThicknessList[-1])

        xTrackSurfaceRaw = []
        d2TrackSurfaceRaw = []

        for n1 in range(elementsAroundTrackSurface + 1):
            nx = [xStartOuterTracksurface[n1], xEndOuterTracksurface[n1]]
            nd2 = [[0.0, 0.0, segmentLength], [0.0, 0.0, segmentLength]]
            sx, sd2 = interp.sampleCubicHermiteCurves(nx, nd2, elementsCountAlongSegment)[0:2]
            xTrackSurfaceRaw.append(sx)
            d2TrackSurfaceRaw.append(sd2)

        # Re-arrange sample order & calculate ds1
        xTrackSurface = []
        d1TrackSurface = []
        d2TrackSurface = []
        for n2 in range(elementsCountAlongSegment + 1):
            xAround = []
            d1Around = []

            for n1 in range(elementsAroundTrackSurface + 1):
                x = xTrackSurfaceRaw[n1][n2]
                d2 = d2TrackSurfaceRaw[n1][n2]
                xAround.append(x)
                d2TrackSurface.append(d2)

            for n1 in range(elementsAroundTrackSurface):
                v1 = xAround[n1]
                v2 = xAround[n1 + 1]
                d1 = d2 = [v2[c] - v1[c] for c in range(3)]
                arcLengthAround = interp.computeCubicHermiteArcLength(v1, d1, v2, d2, True)
                ds1 = [c * arcLengthAround for c in vector.normalise(d1)]
                d1Around.append(ds1)
            d1Around.append(ds1)
            d1SmoothedAround = interp.smoothCubicHermiteDerivativesLine(xAround, d1Around)

            xTrackSurface += xAround
            d1TrackSurface += d1SmoothedAround

        trackSurfaceOstium = TrackSurface(elementsAroundTrackSurface, elementsAlongTrackSurface,
                                         xTrackSurface, d1TrackSurface, d2TrackSurface)

        ##############################################################################################
        # nodeIdentifier = 1000000
        # for n in range(len(xTrackSurface)):
        #     node = nodes.createNode(nodeIdentifier, nodetemplate)
        #     cache.setNode(node)
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, xTrackSurface[n])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, zero)
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, zero)
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, zero)
        #     if useCrossDerivatives:
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS3, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS2DS3, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D3_DS1DS2DS3, 1, zero)
        #     print('NodeIdentifier = ', nodeIdentifier)
        #     nodeIdentifier = nodeIdentifier + 1
        ##########################################################################################

        # Find centre position of ostium
        # Ostium fixed in middle of 3rd tenia coli
        ei1Centre = int(elementsAroundTrackSurface * 0.5)
        xi1 = 0.0
        ostiumDistanceFromCecumDistal = segmentLength * ostiumPositionAlongFactor
        ei2Centre = (elementsCountAlongSegment - 1) if ostiumDistanceFromCecumDistal == 0.0 else int(
            (segmentLength - ostiumDistanceFromCecumDistal) / segmentLength * elementsCountAlongSegment)
        elementLengthAlong = segmentLength / elementsCountAlongSegment
        xi2 = (segmentLength - ostiumDistanceFromCecumDistal - ei2Centre*elementLengthAlong) / elementLengthAlong

        centrePosition = TrackSurfacePosition(ei1Centre, ei2Centre, xi1, xi2)
        xCentre, d1Centre, d2Centre = trackSurfaceOstium.evaluateCoordinates(centrePosition, derivatives=True)
        axis1 = d1Centre

        elementsCountAroundOstium = (elementsCountAlongSegment - 4) * 2 + 2
        ostiumSettings['Number of elements around ostium'] = elementsCountAroundOstium

        fm = region.getFieldmodule()
        mesh = fm.findMeshByDimension(3)
        nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)

        cecumMeshGroup = cecumGroup.getMeshGroup(mesh)

        nextNodeIdentifier, nextElementIdentifier, (o1_x, o1_d1, o1_d2, o1_d3, o1_NodeId, o1_Positions) = \
            generateOstiumMesh(region, ostiumSettings, trackSurfaceOstium, centrePosition, axis1,
                               firstNodeIdentifier, firstElementIdentifier, ostiumMeshGroups=[cecumMeshGroup])

        nodesCountOstium = nextNodeIdentifier - 1

        # Make body of cecum
        # Create first tc
        xSampledTC = []
        d2SampledTC = []

        tc2StartIdx = int(elementsCountAroundTC * 0.5 + elementsCountAroundHaustrum)
        tc1bStartIdx3 = int(elementsCountAroundTC * 2.5 + elementsCountAroundHaustrum * 3)
        tc1bStartIdx2 = int(elementsCountAroundTC * 1.5 + elementsCountAroundHaustrum * 2)

        # Indices for tc with 3 tc
        tcIdxList3 = list(range(0,int(elementsCountAroundTC * 0.5) + 1)) + \
                     list(range(tc2StartIdx, tc2StartIdx + elementsCountAroundTC + 1)) + \
                     list(range(tc1bStartIdx3, tc1bStartIdx3 + int(elementsCountAroundTC * 0.5)))
        # Indices for tc with 2 tc
        tcIdxList2 = list(range(0, int(elementsCountAroundTC * 0.5) + 1)) + \
                     list(range(tc2StartIdx, tc2StartIdx + elementsCountAroundTC + 1)) + \
                     list(range(tc1bStartIdx2, tc1bStartIdx2 + int(elementsCountAroundTC * 0.5)))

        for n in range(len(tcIdxList3)):
            nTC3 = tcIdxList3[n]
            nTC2 = tcIdxList2[n]

            nx = [xStart[nTC3], xEnd[nTC2]]
            nd2 = [[0.0, 0.0, segmentLength], [0.0, 0.0, segmentLength]]
            sx, sd2 = interp.sampleCubicHermiteCurves(nx, nd2, elementsCountAlongSegment)[0:2]

            xSampledTC.append(sx)
            d2SampledTC.append(sd2)

        #########################################################################################################
            # for i in range(len(sx)):
            #     node = nodes.createNode(nodeIdentifier, nodetemplate)
            #     cache.setNode(node)
            #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, sx[i])
            #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, zero)
            #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, sd2[i])
            #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, zero)
            #     if useCrossDerivatives:
            #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, zero)
            #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS3, 1, zero)
            #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS2DS3, 1, zero)
            #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D3_DS1DS2DS3, 1, zero)
            #     # print('NodeIdentifier = ', nodeIdentifier, sx[i])
            #     nodeIdentifier = nodeIdentifier + 1
        #####################################################################################################
        # Arrange xSampledTC such that we start at edge of tc instead of middle of first tc
        xArrangeTC = xSampledTC[-int(elementsCountAroundTC * 0.5):][:] + xSampledTC[:-int(elementsCountAroundTC * 0.5)][:]
        d1ArrangeTC = [d1Start[-int(elementsCountAroundTC * 0.5):] + d1Start[:int(elementsCountAroundTC * 0.5) + 1] + \
                        d1Start[tc2StartIdx: tc2StartIdx + elementsCountAroundTC + 1]] # use d1 from start profile

        for n2 in range(elementsCountAlongSegment - 1): # Just doing the ones between edges
            d1AroundTC = []
            for nTC in range(tcCount - 1):
                d1AroundTC.append([xArrangeTC[nTC * (elementsCountAroundTC + 1) + 1][n2][c] -
                              xArrangeTC[nTC * (elementsCountAroundTC + 1)][n2][c] for c in range(3)])
                for n1 in range(elementsCountAroundTC):
                    d1AroundTC.append([xArrangeTC[nTC * (elementsCountAroundTC + 1) + n1 + 1][n2][c] -
                                       xArrangeTC[nTC * (elementsCountAroundTC + 1) + n1][n2][c] for c in range(3)])

            d1ArrangeTC.append(d1AroundTC) # first index refers to n2, 2nd index for nTC, note nTC starts at edge of first tc, not middle

        d1ArrangeTC.append(d1End[-int(elementsCountAroundTC * 0.5):] + d1End[:int(elementsCountAroundTC * 0.5) + 1] +
                            d1End[tc2StartIdx: tc2StartIdx + elementsCountAroundTC + 1]) # use d1 from end profile

        # #########################################################################################################
        # for nTC in range(len(xArrangeTC)):
        #     for n2 in range(len(xArrangeTC[nTC])):
        #         node = nodes.createNode(nodeIdentifier, nodetemplate)
        #         cache.setNode(node)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, xArrangeTC[nTC][n2])
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, d1ArrangeTC[n2][nTC])
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, zero)
        #         if useCrossDerivatives:
        #             coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, zero)
        #             coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS3, 1, zero)
        #             coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS2DS3, 1, zero)
        #             coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D3_DS1DS2DS3, 1, zero)
        #         # print('NodeIdentifier = ', nodeIdentifier, sx[i])
        #         nodeIdentifier = nodeIdentifier + 1
        # #########################################################################################################

        # Mid haustrum for tc == 3
        xHalfSetMid3, d1HalfSetMid3 = createHalfSetIntraHaustralSegment(
            elementsCountAroundTC, elementsCountAroundHaustrum, tcCount, tcWidth, radius,
            cornerInnerRadiusFactor, sampleElementOut, haustrumInnerRadiusFactor)

        d2HalfSetMid3 = []
        for i in range(len(xHalfSetMid3)):
            xHalfSetMid3[i][2] += segmentLength * 0.5  # sxRefList[-1][2]
            d2HalfSetMid3.append([0.0, 0.0, 0.0])

        xMidTC3, d1MidTC3, d2MidTC3 = getFullProfileFromHalfHaustrum(xHalfSetMid3, d1HalfSetMid3, d2HalfSetMid3, tcCount)
        xMid3 = xMidTC3[int(elementsCountAroundTC * 0.5 + 1) : tc2StartIdx]
        d1Mid3 = d1MidTC3[int(elementsCountAroundTC * 0.5 + 1) : tc2StartIdx]
        d2Mid3 = d2MidTC3[int(elementsCountAroundTC * 0.5 + 1) : tc2StartIdx]

        # Mid haustrum for tc == 2
        xHalfSetMid2, d1HalfSetMid2 = createHalfSetIntraHaustralSegment(
            elementsCountAroundTC, elementsCountAroundHaustrum, endTCCount, tcWidth, radius,
            endCornerInnerRadiusFactor, sampleElementOut, haustrumInnerRadiusFactor)

        d2HalfSetMid2 = []
        for i in range(len(xHalfSetMid2)):
            xHalfSetMid2[i][2] += segmentLength * 0.5  # sxRefList[-1][2]
            d2HalfSetMid2.append([0.0, 0.0, 0.0])

        xMidTC2, d1MidTC2, d2MidTC2 = getFullProfileFromHalfHaustrum(xHalfSetMid2, d1HalfSetMid2, d2HalfSetMid2, endTCCount)

        # Rotate end profile such that third cecum tc sits between two colon tc
        xMidRot = []
        d1MidRot = []
        d2MidRot = []
        for n in range(len(xMidTC2)):
            xMidRot.append(matrix.rotateAboutZAxis(xMidTC2[n], -math.pi / 6))
            d1MidRot.append(matrix.rotateAboutZAxis(d1MidTC2[n], -math.pi / 6))
            d2MidRot.append(matrix.rotateAboutZAxis(d2MidTC2[n], -math.pi / 6))

        xMid2 = xMidRot[int(elementsCountAroundTC * 0.5 + 1) : tc2StartIdx]
        d1Mid2 = d1MidRot[int(elementsCountAroundTC * 0.5 + 1) : tc2StartIdx]
        d2Mid2 = d2MidRot[int(elementsCountAroundTC * 0.5 + 1) : tc2StartIdx]

        # Average xMid2 and xMid3
        xMidAve = []
        for i in range(len(xMid2)):
            xMidAve.append([(xMid3[i][c] + xMid2[i][c]) * 0.5 for c in range(3)])

        ##############################################################################################
        # for n in range(len(xMid3)):
        #     node = nodes.createNode(nodeIdentifier, nodetemplate)
        #     cache.setNode(node)
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, xMid3[n])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, d1Mid3[n])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, d2Mid3[n])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, zero)
        #     if useCrossDerivatives:
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS3, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS2DS3, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D3_DS1DS2DS3, 1, zero)
        #     # print('NodeIdentifier = ', nodeIdentifier, xMid3[n]) #, d1[n], d2[n])
        #     nodeIdentifier = nodeIdentifier + 1

        # for n in range(len(xMid2)):
        #     node = nodes.createNode(nodeIdentifier, nodetemplate)
        #     cache.setNode(node)
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, xMid2[n])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, d1Mid2[n])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, d2Mid2[n])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, zero)
        #     if useCrossDerivatives:
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS3, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS2DS3, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D3_DS1DS2DS3, 1, zero)
        #     # print('NodeIdentifier = ', nodeIdentifier) #, x[n], d1[n], d2[n])
        #     nodeIdentifier = nodeIdentifier + 1

        # for n in range(len(xMidAve)):
        #     node = nodes.createNode(nodeIdentifier, nodetemplate)
        #     cache.setNode(node)
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, xMidAve[n])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, zero)
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, zero)
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, zero)
        #     if useCrossDerivatives:
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS3, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS2DS3, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D3_DS1DS2DS3, 1, zero)
        #     print('NodeIdentifier = ', nodeIdentifier, xMidAve[n]) #, d1[n], d2[n])
        #     nodeIdentifier = nodeIdentifier + 1
        # ###########################################################################################

        # Sample along segment
        xSampledHaustrum = []
        d2SampledHaustrum = []
        for n1 in range(elementsCountAroundHaustrum - 1): # Just haustra
            n1OffsetTC = n1 + int(elementsCountAroundTC * 0.5 + 1)
            nx = [xStart[n1OffsetTC], xMidAve[n1], xEnd[n1OffsetTC]]
            d2 = [0.0, 0.0, segmentLength * 0.5]
            nd2 = [[c * segmentLengthEndDerivativeFactor for c in d2],
                   [c * segmentLengthMidDerivativeFactor for c in d2],
                   [c * segmentLengthEndDerivativeFactor for c in d2]]

            sx, sd2 = interp.sampleCubicHermiteCurves(nx, nd2, elementsCountAlongSegment)[0:2]

            xSampledHaustrum.append(sx)
            d2SampledHaustrum.append(sd2)
            ###########################################################################################################
            # for n in range(len(sx)):
            #     node = nodes.createNode(nodeIdentifier, nodetemplate)
            #     cache.setNode(node)
            #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, sx[n])
            #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, zero)
            #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, sd2[n])
            #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, zero)
            #     if useCrossDerivatives:
            #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, zero)
            #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS3, 1, zero)
            #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS2DS3, 1, zero)
            #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D3_DS1DS2DS3, 1, zero)
            #     print('NodeIdentifier = ', nodeIdentifier)
            #     nodeIdentifier = nodeIdentifier + 1
            ###########################################################################################################

        # Sample around
        xHaustrum = []
        d1Haustrum = []

        xHaustrum.append(xStart[int(elementsCountAroundTC * 0.5) : tc2StartIdx + 1])
        d1Haustrum.append(d1Start[int(elementsCountAroundTC * 0.5) : tc2StartIdx + 1])

        for n2 in range(elementsCountAlongSegment + 1):
            xAround = []
            d1Around = []
            xAround.append(xArrangeTC[elementsCountAroundTC][n2])

            for n1 in range(len(xSampledHaustrum)):
                x = xSampledHaustrum[n1][n2]
                d2 = d2SampledHaustrum[n1][n2]
                xAround.append(x)

            xAround.append(xArrangeTC[elementsCountAroundTC + 1][n2])

            for n1 in range(len(xAround)):
                if n1 == 0:
                    d1Around.append(d1ArrangeTC[n2][elementsCountAroundTC])
                elif n1 == len(xAround) - 1:
                    d1Around.append(d1ArrangeTC[n2][elementsCountAroundTC + 1])
                else:
                    v1 = xAround[n1]
                    v2 = xAround[n1 + 1]
                    d1 = [v2[c] - v1[c] for c in range(3)]
                    arcLengthAround = interp.computeCubicHermiteArcLength(v1, d1, v2, d2, True)
                    d1 = [c * arcLengthAround for c in vector.normalise(d1)]
                    d1Around.append(d1)

            if n2 > 0 and n2 < elementsCountAlongSegment:
                sxAround, sd1Around = interp.sampleCubicHermiteCurves(xAround, d1Around, elementsCountAroundHaustrum)[0:2]
                d1Smoothed = interp.smoothCubicHermiteDerivativesLine(sxAround, sd1Around, fixStartDirection=True, fixEndDirection=True)
                xHaustrum.append(sxAround)
                d1Haustrum.append(d1Smoothed)

        xHaustrum.append(xEnd[int(elementsCountAroundTC * 0.5) : tc2StartIdx + 1])
        d1Haustrum.append(d1End[int(elementsCountAroundTC * 0.5) : tc2StartIdx + 1])

        # Calculate new d2
        d2Raw = []
        for n1 in range(elementsCountAroundHaustrum - 1): # Do not touch tc
            xAlong = []
            d2Along = []
            xAlong.append(xSampledHaustrum[n1][0])
            d2Along.append(d2SampledHaustrum[n1][0])

            for n2 in range(1, elementsCountAlongSegment): # Do not touch start and end profiles
                v1 = xHaustrum[n2][n1 + 1]
                v2 = xHaustrum[n2 + 1][n1 + 1]
                d2 = [v2[c] - v1[c] for c in range(3)]
                arcLengthAlong = interp.computeCubicHermiteArcLength(v1, d1, v2, d2, True)
                d2 = [c * arcLengthAlong for c in vector.normalise(d2)]
                xAlong.append(v1)
                d2Along.append(d2)

            xAlong.append(xSampledHaustrum[n1][-1])
            d2Along.append(d2SampledHaustrum[n1][-1])

            # Smooth d2
            d2Smoothed = interp.smoothCubicHermiteDerivativesLine(xAlong, d2Along, fixStartDerivative= True, fixEndDerivative= True)
            d2Raw.append(d2Smoothed)

        d2Haustrum = []
        for n2 in range(elementsCountAlongSegment + 1):
            d2Around = []
            for n1 in range(elementsCountAroundHaustrum + 1):
                if n1 == 0:
                    d2Around.append(d2SampledTC[int(elementsCountAroundTC * 0.5)][n2])
                elif n1 == elementsCountAroundHaustrum:
                    d2Around.append(d2SampledTC[int(elementsCountAroundTC * 0.5) + 1][n2])
                # elif n2 == 0 or n2 == elementsCountAlongSegment:
                #     d2Around.append(d2SampledHaustrum[n1 - 1][n2])
                else:
                    d2Around.append(d2Raw[n1 - 1][n2])
            d2Haustrum.append(d2Around)

        xAll1 = []
        d1All1 = []
        d2All1 = []
        d3All1 = []

        for n2 in range(elementsCountAlongSegment + 1):
            for nTC in range(int(elementsCountAroundTC * 0.5 + 1)):
                xAll1.append(xArrangeTC[int(elementsCountAroundTC * 0.5) + nTC][n2])
                d1All1.append(d1ArrangeTC[n2][int(elementsCountAroundTC * 0.5) + nTC])
                d2All1.append(d2SampledTC[nTC][n2])
            for n1 in range(1, elementsCountAroundHaustrum):
                xAll1.append(xHaustrum[n2][n1])
                if n2 == 1:
                    d1All1.append(vector.setMagnitude(d1Haustrum[n2][n1], vector.magnitude(d1Haustrum[n2][n1 + 1])))
                elif n2 == elementsCountAroundHaustrum - 1:
                    d1All1.append(vector.setMagnitude(d1Haustrum[n2][n1], vector.magnitude(d1Haustrum[n2][n1 - 1])))
                else:
                    d1All1.append(d1Haustrum[n2][n1])
                d2All1.append(d2Haustrum[n2][n1])
            for nTC in range(elementsCountAroundTC + 1):
                xAll1.append(xArrangeTC[elementsCountAroundTC + 1 + nTC][n2])
                d1All1.append(d1ArrangeTC[n2][elementsCountAroundTC + 1 + nTC])
                d2All1.append(d2SampledTC[int(elementsCountAroundTC * 0.5) + 1 + nTC][n2])

        for n in range(len(xAll1)):
            d3All1.append(vector.normalise(vector.crossproduct3(d1All1[n], d2All1[n])))

        # # ############################################################################################################
        # for n2 in range(len(xAll1)):
        #     node = nodes.createNode(nodeIdentifier, nodetemplate)
        #     cache.setNode(node)
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, xAll1[n2])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, d1All1[n2])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, d2All1[n2])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, d3All1[n2])
        #     if useCrossDerivatives:
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS3, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS2DS3, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D3_DS1DS2DS3, 1, zero)
        #     # print('NodeIdentifier = ', nodeIdentifier, d1All[i])
        #     nodeIdentifier = nodeIdentifier + 1
        # ###########################################################################################################

        # Haustrum between tc 1 and tc 3
        # 3 tenia coli
        startIdx = tc2StartIdx + elementsCountAroundTC + int(elementsCountAroundHaustrum * 0.25)
        xMid3BetweenTC1And3 = xMidTC3[
                             startIdx: startIdx + int(elementsCountAroundHaustrum * 0.5)]
        d1Mid3BetweenTC1And3 = d1MidTC3[
                              startIdx: startIdx + int(elementsCountAroundHaustrum * 0.5)]

        # 2 tenia coli
        startIdx = tc2StartIdx + elementsCountAroundTC + 1
        xMid2BetweenTC1And3 = xMidRot[
                              startIdx: startIdx + int(elementsCountAroundHaustrum * 0.5)]
        d1Mid2BetweenTC1And3 = d1MidRot[
                               startIdx: startIdx + int(elementsCountAroundHaustrum * 0.5)]

        xMidAveBetweenTC1And3 = []
        for i in range(int(elementsCountAroundHaustrum * 0.5)):
            xMidAve = [(xMid3BetweenTC1And3[i][c] + xMid2BetweenTC1And3[i][c]) * 0.5 for c in range(3)]
            xMidAveBetweenTC1And3.append(xMidAve)

        ###########################################################################################
        # for n in range(len(xMidAveBetweenTC1And3)):
        #     node = nodes.createNode(nodeIdentifier, nodetemplate)
        #     cache.setNode(node)
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, xMidAveBetweenTC1And3[n])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, zero)
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, zero) #d1Mid2BetweenTC1And3[n])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, zero)
        #     if useCrossDerivatives:
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS3, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS2DS3, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D3_DS1DS2DS3, 1, zero)
        #     print('New nodeIdentifier = ', nodeIdentifier)
        #     nodeIdentifier = nodeIdentifier + 1
        ############################################################################################
        # Sample along first half of haustrum from start to end profile
        xSampledHaustrum2 = []
        d2SampledHaustrum2 = []
        for n1 in range(int(elementsCountAroundHaustrum * 0.5)):
            startIdxTrackSurfaceStartSegment = tc2StartIdx + elementsCountAroundTC + 1
            nx = [xStart[startIdxTrackSurfaceStartSegment + n1], xMidAveBetweenTC1And3[n1], xEnd[startIdxTrackSurfaceStartSegment + n1]]
            d2 = [0.0, 0.0, segmentLength * 0.5]
            nd2 = [[c * segmentLengthEndDerivativeFactor for c in d2],
                   [c * segmentLengthMidDerivativeFactor for c in d2],
                   [c * segmentLengthEndDerivativeFactor for c in d2]]
            sx, sd2 = interp.sampleCubicHermiteCurves(nx, nd2, elementsCountAlongSegment)[0:2]
            xSampledHaustrum2.append(sx)
            d2SampledHaustrum2.append(sd2)

        ###########################################################################################
            # for n in range(len(sx)):
            #     node = nodes.createNode(nodeIdentifier, nodetemplate)
            #     cache.setNode(node)
            #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, sx[n])
            #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, zero)
            #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, sd2[n])
            #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, zero)
            #     if useCrossDerivatives:
            #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, zero)
            #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS3, 1, zero)
            #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS2DS3, 1, zero)
            #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D3_DS1DS2DS3, 1, zero)
            #     # print('NodeIdentifier = ', nodeIdentifier, xTrackSurface[n]) #, d1[n], d2[n])
            #     nodeIdentifier = nodeIdentifier + 1
        ##############################################################################################

        # Sample around haustrum 2
        xHaustrum2 = []
        d1Haustrum2 = []

        startIdx = tc2StartIdx + elementsCountAroundTC
        xHaustrum2.append(xStart[startIdx: startIdx + int(elementsCountAroundHaustrum * 0.5 + 1)])
        d1Haustrum2.append(d1Start[startIdx: startIdx + int(elementsCountAroundHaustrum * 0.5 + 1)])

        for n2 in range(elementsCountAlongSegment + 1):
            xAround = []
            d1Around = []
            xAround.append(xArrangeTC[-1][n2])

            for n1 in range(len(xSampledHaustrum2)):
                x = xSampledHaustrum2[n1][n2]
                d2 = d2SampledHaustrum2[n1][n2]
                xAround.append(x)

            for n1 in range(len(xAround) - 1):
                if n1 == 0:
                    d1Around.append(d1ArrangeTC[n2][-1])
                else:
                    v1 = xAround[n1]
                    v2 = xAround[n1 + 1]
                    d1 = [v2[c] - v1[c] for c in range(3)]
                    arcLengthAround = interp.computeCubicHermiteArcLength(v1, d1, v2, d2, True)
                    d1 = [c * arcLengthAround for c in vector.normalise(d1)]
                    d1Around.append(d1)
            d1Around.append(d1)

            if n2 > 0 and n2 < elementsCountAlongSegment:
                sxAround, sd1Around = interp.sampleCubicHermiteCurves(xAround, d1Around,
                                                                      int(elementsCountAroundHaustrum * 0.5))[0:2]
                d1Smoothed = interp.smoothCubicHermiteDerivativesLine(sxAround, sd1Around, fixStartDirection=True,
                                                                      fixEndDirection=True)
                xHaustrum2.append(sxAround)
                d1Haustrum2.append(d1Smoothed)

        xHaustrum2.append(xEnd[startIdx: startIdx + int(elementsCountAroundHaustrum * 0.5 + 1)])
        d1Haustrum2.append(d1End[startIdx: startIdx + int(elementsCountAroundHaustrum * 0.5 + 1)])

        # Calculate new d2
        d2Raw = []
        for n1 in range(int(elementsCountAroundHaustrum * 0.5)):
            xAlong = []
            d2Along = []
            xAlong.append(xSampledHaustrum2[n1][0])
            d2Along.append(d2SampledHaustrum2[n1][0])

            for n2 in range(1, elementsCountAlongSegment):  # Do not touch start and end profiles
                v1 = xHaustrum2[n2][n1 + 1]
                v2 = xHaustrum2[n2 + 1][n1 + 1]
                d2 = [v2[c] - v1[c] for c in range(3)]
                arcLengthAlong = interp.computeCubicHermiteArcLength(v1, d1, v2, d2, True)
                d2 = [c * arcLengthAlong for c in vector.normalise(d2)]
                xAlong.append(v1)
                d2Along.append(d2)

            xAlong.append(xSampledHaustrum2[n1][-1])
            d2Along.append(d2SampledHaustrum2[n1][-1])

            # Smooth d2
            d2Smoothed = interp.smoothCubicHermiteDerivativesLine(xAlong, d2Along, fixStartDerivative=True,
                                                                  fixEndDerivative=True)
            d2Raw.append(d2Smoothed)

        d2Haustrum2 = []
        for n2 in range(elementsCountAlongSegment + 1):
            d2Around = []
            for n1 in range(int(elementsCountAroundHaustrum * 0.5) + 1):
                if n1 == 0:
                    d2Around.append(d2SampledTC[-1][n2])
                else:
                    d2Around.append(d2Raw[n1 - 1][n2])
            d2Haustrum2.append(d2Around)

        xAll2 = []
        d1All2 = []
        d2All2 = []
        d3All2 = []

        for n2 in range(elementsCountAlongSegment + 1):
            for n1 in range(1, int(elementsCountAroundHaustrum * 0.5) + 1):
                xAll2.append(xHaustrum2[n2][n1])
                if n1 == 1:
                    d1All2.append(vector.setMagnitude(d1Haustrum2[n2][n1], vector.magnitude(d1Haustrum2[n2][n1 + 1])))
                else:
                    d1All2.append(d1Haustrum2[n2][n1])
                d2All2.append(d2Haustrum2[n2][n1])

        for n in range(len(xAll2)):
            d3All2.append(vector.normalise(vector.crossproduct3(d1All2[n], d2All2[n])))

        # # ############################################################################################################
        # nodeIdentifier = 20000
        # for n2 in range(len(xAll2)):
        #     node = nodes.createNode(nodeIdentifier, nodetemplate)
        #     cache.setNode(node)
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, xAll2[n2])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, d1All2[n2])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, d2All2[n2])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, d3All2[n2])
        #     if useCrossDerivatives:
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS3, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS2DS3, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D3_DS1DS2DS3, 1, zero)
        #     # print('NodeIdentifier = ', nodeIdentifier)
        #     nodeIdentifier = nodeIdentifier + 1
        ###########################################################################################################

        # Reflect haustrum2 to get haustrum 3
        xAll3 = []
        d1All3 = []
        d2All3 = []

        for n2 in range(elementsCountAlongSegment + 1):
            xAround = []
            xAroundOrdered = []
            d2Around = []
            for n1 in range(int(elementsCountAroundHaustrum * 0.5)):
                i = n2 * int(elementsCountAroundHaustrum * 0.5) + n1
                x = xAll2[i]
                xRot = matrix.rotateAboutZAxis(x, -math.pi/180 * 15)
                xReflect = [xRot[1], xRot[0], xRot[2]]
                xRotBack = matrix.rotateAboutZAxis(xReflect, math.pi/180 * 15)
                xAround.append(xRotBack)

                d2 = d2All2[i]
                d2Rot = matrix.rotateAboutZAxis(d2, -math.pi / 180 * 15)
                d2Reflect = [d2Rot[1], d2Rot[0], d2Rot[2]]
                d2RotBack = matrix.rotateAboutZAxis(d2Reflect, math.pi / 180 * 15)
                d2Around.append(d2RotBack)

            # Re-order nodes
            for n1 in range(int(elementsCountAroundHaustrum * 0.5)):
                xAroundOrdered.append(xAround[int(elementsCountAroundHaustrum * 0.5 - 1) - n1])
                d2All3.append(d2Around[int(elementsCountAroundHaustrum * 0.5 - 1) - n1])

            # Add remaining tc
            for nTC in range(int(elementsCountAroundTC * 0.5)):
                tcIdx = nTC + int(elementsCountAroundTC * 1.5 + 1) + 1
                xAroundOrdered.append(xSampledTC[tcIdx][n2])
                d2All3.append(d2SampledTC[tcIdx][n2])

            xAll3 += xAroundOrdered

            # Calculate d1
            d1Around = []
            xAround = []
            for n1 in range(len(xAroundOrdered) - int(elementsCountAroundTC * 0.5)):
                xAround.append(xAroundOrdered[n1])
                v1 = xAroundOrdered[n1]
                v2 = xAroundOrdered[n1 + 1]
                d1 = d2 = [v2[c] - v1[c] for c in range(3)]
                arcLengthAround = interp.computeCubicHermiteArcLength(v1, d1, v2, d2, True)
                ds1 = [c * arcLengthAround for c in vector.normalise(d1)]
                d1Around.append(ds1)
            # Append edge of tc to do smoothing
            xAround.append(xAroundOrdered[n1 + 1])
            d1Around.append(d1ArrangeTC[n2][0])
            d1SmoothedAround = interp.smoothCubicHermiteDerivativesLine(xAround, d1Around, fixEndDerivative= True)
            # Scale magnitude of d1 to d1 of haustrum element next to it
            d1SmoothedAround[-2] = vector.setMagnitude(d1SmoothedAround[-2], vector.magnitude(d1SmoothedAround[-3]))
            # Append rest of tc
            for nTC in range(1, int(elementsCountAroundTC * 0.5)):
                d1SmoothedAround.append(d1ArrangeTC[n2][nTC])

            d1All3 += d1SmoothedAround

        d3All3 = []
        for n in range(len(xAll3)):
            d3All3.append(vector.normalise(vector.crossproduct3(d1All3[n], d2All3[n])))

        ##################################################################################################
        # for n in range(len(xAll3)):
        #     node = nodes.createNode(nodeIdentifier, nodetemplate)
        #     cache.setNode(node)
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, xAll3[n])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, d1All3[n])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, d2All3[n])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, zero)
        #     if useCrossDerivatives:
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS3, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS2DS3, 1, zero)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D3_DS1DS2DS3, 1, zero)
        #     # print('NodeIdentifier = ', nodeIdentifier, xAll3[n]) #, d1[n], d2[n])
        #     nodeIdentifier = nodeIdentifier + 1
        ######################################################################################################

        # Number of nodes around in each section
        nAround1 = int(elementsCountAroundTC * 1.5 + 1 + elementsCountAroundHaustrum)
        nAround2 = int(elementsCountAroundHaustrum * 0.5)
        nAround3 = int((elementsCountAroundHaustrum + elementsCountAroundTC) * 0.5)

        # Make 6 way junction near colon end
        p1x = o1_x[0][int(elementsCountAroundOstium * 0.5)]
        p1d = o1_d2[0][int(elementsCountAroundOstium * 0.5)]

        n2 = elementsCountAlongSegment - 1

        p2x = xAll3[n2 * nAround3]
        rotAxis = d3All3[n2 * nAround3]
        rotMat = matrix.getRotationMatrixFromAxisAngle(rotAxis, math.pi)
        d2 = d2All3[n2 * nAround3]
        p2d = [rotMat[j][0] * d2[0] + rotMat[j][1] * d2[1] + rotMat[j][2] * d2[2] for j in range(3)]

        p3x = xAll2[(n2 + 1) * nAround2 - 1]
        rotAxis = d3All2[(n2 + 1) * nAround2 - 1]
        rotMat = matrix.getRotationMatrixFromAxisAngle(rotAxis, math.pi)
        d2 = d2All2[(n2 + 1) * nAround2 - 1]
        p3d = [rotMat[j][0] * d2[0] + rotMat[j][1] * d2[1] + rotMat[j][2] * d2[2] for j in range(3)]

        xJunction, d1Junction, d2Junction = get_bifurcation_triple_point(p1x, p1d, p2x, p2d, p3x, p3d)
        d3Junction = vector.normalise(vector.crossproduct3(vector.normalise(d1Junction), vector.normalise(d2Junction)))

        # Connect elements around n2 == 3 v-> elementsCountSegment - 2 from tc2 to ostium
        xMiddleAlongS2 = []
        d1MiddleAlongS2 = []

        for n2 in range(3, elementsCountAlongSegment - 1):
            # nx = [xAll1[(n2 + 1) * nAround1 - 1]] + xAll2[n2 * nAround2: (n2 + 1) * nAround2] + [o1_x[0][n2 - 2]]
            # dOstium = o1_d2[0][n2 - 2]
            # rotAxis = vector.normalise(vector.crossproduct3(vector.normalise(o1_d1[0][n2 - 2]), vector.normalise(o1_d2[0][n2 - 2])))
            # rotMat = matrix.getRotationMatrixFromAxisAngle(rotAxis, math.pi)
            # dOstiumRot = [rotMat[j][0] * dOstium[0] + rotMat[j][1] * dOstium[1] + rotMat[j][2] * dOstium[2] for j in range(3)]
            # nd1 = [d1All1[(n2 + 1) * nAround1 - 1]] + d1All2[n2 * nAround2: (n2 + 1) * nAround2] + [dOstiumRot]
            # sx, sd1 = interp.sampleCubicHermiteCurves(nx, nd1, int(elementsCountAroundHaustrum * 0.5 + 1), addLengthStart = 0.5 * vector.magnitude(nd1[0]), lengthFractionStart = 0.5)[0:2]
            #
            # # Exclude node on tc and ostium
            # xMiddleAlongS2.append(sx[1:-1])
            # d1MiddleAlongS2.append(sd1[1:-1])

            xMiddleAlongS2.append(xAll2[n2 * nAround2: (n2 + 1) * nAround2])
            d1MiddleAlongS2.append(d1All2[n2 * nAround2: (n2 + 1) * nAround2])

        # Sample from n2 == 3 to end profile node before TC3
        n2 = 3
        nx = [xAll2[(n2 + 1) * nAround2 - 1], xStart[int(elementsCountAroundTC * 1.5 + elementsCountAroundHaustrum * 2) - 1]]
        nd1 = [d1All2[(n2 + 1) * nAround2 - 1], [0.0, 0.0, -1.0]]
        sx, sd1 = interp.sampleCubicHermiteCurves(nx, nd1, 2, arcLengthDerivatives = True)[0:2]
        xNew2 = sx[1]
        dNew2 = sd1[1]

        # Sample the elements around in row below end profile
        n2 = elementsCountAlongSegment - 1
        # nx = [xAll1[(n2 + 1) * nAround1 - 1]] + xAll2[n2 * nAround2: (n2 + 1) * nAround2] + [xJunction]
        dJunction = d2Junction
        rotAxis = vector.normalise(vector.crossproduct3(vector.normalise(d1Junction), vector.normalise(d2Junction)))
        rotMat = matrix.getRotationMatrixFromAxisAngle(rotAxis, math.pi)
        dJunctionRot = [rotMat[j][0] * dJunction[0] + rotMat[j][1] * dJunction[1] + rotMat[j][2] * dJunction[2] for j in
                      range(3)]

        xRowBelowEndProfile = xAll2[n2 * nAround2: (n2 + 1) * nAround2 - 1] + [xJunction]
        d1RowBelowEndProfile = d1All2[n2 * nAround2: (n2 + 1) * nAround2 - 1] + [dJunctionRot]

        # Smooth derivatives at junction with surrounding derivatives in the path
        xPrevNode = xRowBelowEndProfile[-2]
        dPrevNode = d1RowBelowEndProfile[-2]
        n2 = elementsCountAlongSegment - 2
        x = xMiddleAlongS2[-1][-1]
        xRot = matrix.rotateAboutZAxis(x, -math.pi / 180 * 15)
        xReflect = [xRot[1], xRot[0], xRot[2]]
        xNextNode = matrix.rotateAboutZAxis(xReflect, math.pi / 180 * 15)
        d = [xMiddleAlongS2[-2][-1][c] - xMiddleAlongS2[-1][-1][c] for c in range(3)]
        dRot = matrix.rotateAboutZAxis(d, -math.pi / 180 * 15)
        dReflect = [dRot[1], dRot[0], dRot[2]]
        dNextNode = matrix.rotateAboutZAxis(dReflect, math.pi / 180 * 15)
        xForSmoothing = [xPrevNode, xJunction, xNextNode]
        dForSmoothing = [dPrevNode, dJunctionRot, dNextNode]
        dSmoothed = interp.smoothCubicHermiteDerivativesLine(xForSmoothing, dForSmoothing, fixStartDerivative= True, fixEndDerivative= True)

        d1Junction1stSmoothing = dSmoothed[1]
        d1RowBelowEndProfile[-1] = dSmoothed[1]

        # Sample elements around in row n2 = 2
        n2 = 2
        xRow3 = xAll2[n2 * nAround2: (n2 + 1) * nAround2]
        d1Row3 = d1All2[n2 * nAround2: (n2 + 1) * nAround2]

        x1 = xAll2[(n2 + 1) * nAround2 - 1]
        x2 = xStart[int(elementsCountAroundTC * 1.5 + elementsCountAroundHaustrum * 2) - 2]
        nx = [x1, x2]
        d1 = d1All2[(n2 + 1) * nAround2 - 1]
        d2 = [0.0, 0.0, -1.0]
        nd1 = [d1, d2]
        sx, sd1 = interp.sampleCubicHermiteCurves(nx, nd1, 2, arcLengthDerivatives=True)[0:2]
        xNew1 = sx[1]
        dNew1 = sd1[1]

        # Sample elements around in row n2 = 1
        n2 = 1
        xRow2 = xAll2[n2 * nAround2: (n2 + 1) * nAround2]
        d1Row2 = d1All2[n2 * nAround2: (n2 + 1) * nAround2]

        # Sample connection between tc3 and ostium
        xAlongBetweenTC3Ostium = []
        d2AlongBetweenTC3Ostium = []

        for nTC in range(int(elementsCountAroundTC * 0.5 + 1)):
            xTC = xStart[nTC + int(elementsCountAroundTC * 1.5 + elementsCountAroundHaustrum * 2)]
            ostiumIdx = int(elementsCountAroundTC * 0.5) - nTC
            xOstium = o1_x[0][ostiumIdx]
            nx = [xTC, xOstium]
            dTC = [0.0, 0.0, segmentLength]
            if nTC < int(elementsCountAroundTC * 0.5):
                dOstium = o1_d1[0][ostiumIdx]
            else:
                rotAxis = vector.normalise(vector.crossproduct3(vector.normalise(o1_d1[0][ostiumIdx]), vector.normalise(o1_d2[0][ostiumIdx])))
                rotMat = matrix.getRotationMatrixFromAxisAngle(rotAxis, math.pi)
                d = o1_d2[0][ostiumIdx]
                dOstium = [rotMat[j][0] * d[0] + rotMat[j][1] * d[1] + rotMat[j][2] * d[2] for j in range(3)]
            nd = [dTC, dOstium]
            sx, sd = interp.sampleCubicHermiteCurves(nx, nd, 2, arcLengthDerivatives=True)[0:2] # Number of elementsAlong between start profile and ostium is hardcoded to 2!

            # Include nodes on start profile and ostium
            xAlongBetweenTC3Ostium.append(sx)
            d2AlongBetweenTC3Ostium.append(sd)

        # Find triple point
        # p1x = xAll2[(n2 + 1) * nAround2 - 1]
        # d = d1All2[(n2 + 1) * nAround2 - 1]
        # rotAxis = getD3(d, d2All2[(n2 + 1) * nAround2 - 1])
        # rotMat = matrix.getRotationMatrixFromAxisAngle(rotAxis, math.pi)
        # p1d = [rotMat[j][0] * d[0] + rotMat[j][1] * d[1] + rotMat[j][2] * d[2] for j in range(3)]
        #
        # p2x = xStart[int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5) + 1]
        # d = d1Start[int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5) + 1]
        # rotAxis = getD3(d, [0.0, 0.0, 1.0])
        # rotMat = matrix.getRotationMatrixFromAxisAngle(rotAxis, math.pi)
        # p2d = [rotMat[j][0] * d[0] + rotMat[j][1] * d[1] + rotMat[j][2] * d[2] for j in range(3)]
        #
        # p3x = xNew1
        # d1 = [xNew2[c] - xNew1[c] for c in range(3)]
        # d2 = [ xAlongBetweenTC3Ostium[0][1][c] - xNew2[c] for c in range(3)]
        # arcLengthAround = interp.computeCubicHermiteArcLength(xNew1, d1, xNew2, d2, True)
        # p3d = [c * arcLengthAround for c in vector.normalise(d1)]
        #
        # xNew0, d1New0, d2New0 = get_bifurcation_triple_point(p1x, p1d, p2x, p2d, p3x, p3d)

        # Find triple point using alternative method
        xToSample = [xStart[int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5) + 1], xNew1]
        dToSample = [[0.0, 0.0, 1.0], [xNew2[c] - xNew1[c] for c in range(3)]]
        sx, sd1 = interp.sampleCubicHermiteCurves(xToSample, dToSample, 2, arcLengthDerivatives= True)[0:2]
        xNew0 = sx[1]
        d2New0 = sd1[1]
        d1New0 = [xStart[int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5) + 2][c] - xNew0[c] for c in range(3)]

        xToSmooth = xRow2[-2:] + [xNew0] + [xStart[int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5) + 2]]
        d1ToSmooth = d1Row2[-2:] + [d1New0] + [d1Start[int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5) + 2]]
        d1Smoothed = interp.smoothCubicHermiteDerivativesLine(xToSmooth, d1ToSmooth, fixStartDerivative= True, fixEndDirection=True)
        d1Row2[-1] = d1Smoothed[1]
        d1New0 = d1Smoothed[2]

        # nodeIdentifier = 80000
        # for n in range(len(xToSmooth)):
        #     node = nodes.createNode(nodeIdentifier, nodetemplate)
        #     cache.setNode(node)
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, xToSmooth[n])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, zero)
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, d1ToSmooth[n])
        #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, zero)
        #     nodeIdentifier += 1

        xRow2 += [xNew0, xNew1, xNew2]
        d1Row2 += [d1New0, dNew1, dNew2]

        # Correct d1 on node joining to xNew1 on xRow3
        xToSmooth = xRow3[-2:] + [xNew1, xStart[int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5) + 2]]
        d1New1 = [xToSmooth[-1][c] - xToSmooth[-2][c] for c in range(3)]
        d1ToSmooth = d1Row3[-2:] + [d1New1, [0.0, 0.0, -1.0]]
        d1Row3[-1] = interp.smoothCubicHermiteDerivativesLine(xToSmooth, d1ToSmooth, fixStartDerivative=True, fixEndDirection=True)[1]

        # Correct d1 on node joining to xNew1 on xRow3
        xToSmooth = xMiddleAlongS2[0][-2:] + [xNew2, xStart[int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5) + 3]]
        d1New1 = [xToSmooth[-1][c] - xToSmooth[-2][c] for c in range(3)]
        d1ToSmooth = d1MiddleAlongS2[0][-2:] + [d1New1, [0.0, 0.0, -1.0]]
        d1MiddleAlongS2[0][-1] = interp.smoothCubicHermiteDerivativesLine(xToSmooth, d1ToSmooth, fixStartDerivative=True, fixEndDirection=True)[1]

        # Number of nodes around in each section
        nAround1 = int(elementsCountAroundTC * 1.5 + 1 + elementsCountAroundHaustrum)
        nAround2 = int(elementsCountAroundHaustrum * 0.5)

        xInnerMat = []
        d1InnerMat = []
        d2InnerMat = []
        d3InnerMat = []
        curvatureAlongMat = []
        transitElementMat = []

        # nodeIdentifier = 80000
        for n2 in range(elementsCountAlongSegment + 1):
            xAround = []
            d1Around = []
            d2Around = []
            d3Around = []
            curvatureAlongAround = []

            xAround += xAll1[n2 * nAround1: (n2 + 1) * nAround1]
            d1Around += d1All1[n2 * nAround1: (n2 + 1) * nAround1]
            d2Around += d2All1[n2 * nAround1: (n2 + 1) * nAround1]

            # Get half of tc2 into xFirstHalf so we can transform later
            xFirstHalf = xAll1[n2 * nAround1 + elementsCountAroundHaustrum + elementsCountAroundTC + 1:
                               n2 * nAround1 + elementsCountAroundHaustrum + int(elementsCountAroundTC * 1.5) + 1]
            d1FirstHalf = d1All1[n2 * nAround1 + elementsCountAroundHaustrum + elementsCountAroundTC + 1:
                                 n2 * nAround1 + elementsCountAroundHaustrum + int(elementsCountAroundTC * 1.5) + 1]
            d2FirstHalf = d2All1[n2 * nAround1 + elementsCountAroundHaustrum + elementsCountAroundTC + 1:
                                 n2 * nAround1 + elementsCountAroundHaustrum + int(elementsCountAroundTC * 1.5) + 1]

            transitElementAround = ([0] * int(elementsCountAroundTC * 0.5) + [1] +
                                    [0] * int(elementsCountAroundHaustrum - 2) + [1] +
                                    [0] * int(elementsCountAroundTC))

            # print('n2 = ', n2, '1st part transitElement = ', transitElementAround)
            if n2 < elementsCountAlongSegment:
                if n2 == 0:
                    xLen = len(xAll2[n2 * nAround2: (n2 + 1) * nAround2] + xStart[nAround1 + nAround2: int((elementsCountAroundTC + elementsCountAroundHaustrum) * 2.0) + 1])
                    xFirstHalf += xAll2[n2 * nAround2: (n2 + 1) * nAround2] + xStart[nAround1 + nAround2: int((elementsCountAroundTC + elementsCountAroundHaustrum) * 2.0) + 1]
                    d1FirstHalf += d1All2[n2 * nAround2: (n2 + 1) * nAround2] + d1Start[nAround1 + nAround2: int((elementsCountAroundTC + elementsCountAroundHaustrum) * 2.0) + 1]
                    d2FirstHalf += d2All2[n2 * nAround2: (n2 + 1) * nAround2] + [[0.0, 0.0, 0.0]] * len(xStart[nAround1 + nAround2: int((elementsCountAroundTC + elementsCountAroundHaustrum) * 2.0) + 1])

                elif n2 == 1:
                    xLen = len(xRow2)
                    xFirstHalf += xRow2
                    d1FirstHalf += d1Row2[:int(-elementsCountAroundHaustrum * 0.5)]
                    d2FirstHalf += [[0.0, 0.0, 0.0]] * xLen

                    # Find d1 for TC3
                    d1TC3 = []
                    for nTC in range(int(elementsCountAroundTC * 0.5)):
                        v1 = xAlongBetweenTC3Ostium[nTC][n2]
                        v2 = xAlongBetweenTC3Ostium[nTC + 1][n2]
                        d1 = d1Start[nAround1 + elementsCountAroundHaustrum + nTC - 1]
                        d2 = d1Start[nAround1 + elementsCountAroundHaustrum + nTC]
                        arcLengthAlong = interp.computeCubicHermiteArcLength(v1, d1, v2, d2, True)
                        d1 = [c * arcLengthAlong for c in vector.normalise(d1)]
                        d1TC3.append(d1)

                        xLen += 1
                        xFirstHalf += [xAlongBetweenTC3Ostium[nTC][n2]]
                        d2FirstHalf += [[0.0, 0.0, 0.0]]

                    d1TC3.append([c * arcLengthAlong for c in vector.normalise(d2)])
                    xLen += 1
                    xFirstHalf += [xAlongBetweenTC3Ostium[nTC + 1][n2]]
                    d2FirstHalf += [[0.0, 0.0, 0.0]]

                    # Find d1 for nodes before triple point to tc3
                    xToSmooth = []
                    d1ToSmooth = []
                    xToSmooth.append(xRow2[int(elementsCountAroundHaustrum * 0.5 - 2)])
                    d1ToSmooth.append(d1Row2[int(elementsCountAroundHaustrum * 0.5 - 2)])
                    for n1 in range(int(elementsCountAroundHaustrum * 0.5)):
                        idx = int(elementsCountAroundHaustrum * 0.5 - 1) + n1
                        v1 = xRow2[idx]
                        v2 = xRow2[(idx + 1)] if n1 < int(elementsCountAroundHaustrum * 0.5 - 1) else xAlongBetweenTC3Ostium[0][n2]
                        d1 = [v2[c] - v1[c] for c in range(3)]
                        arcLengthAround = interp.computeCubicHermiteArcLength(v1, d1, v2, d1, False)
                        ds1 = [c * arcLengthAround for c in vector.normalise(d1)]
                        xToSmooth.append(v1)
                        d1ToSmooth.append(ds1)
                    xToSmooth.append(xAlongBetweenTC3Ostium[0][n2])
                    d1ToSmooth.append(d1TC3[0])
                    d1Smoothed = interp.smoothCubicHermiteDerivativesLine(xToSmooth, d1ToSmooth, fixStartDerivative = True, fixEndDerivative = True)
                    d1FirstHalf += d1Smoothed[1:-1] + d1TC3

                    # nodeIdentifier = 80000
                    # for n in range(len(xToSmooth)):
                    #     node = nodes.createNode(nodeIdentifier, nodetemplate)
                    #     cache.setNode(node)
                    #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, xToSmooth[n])
                    #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, zero)
                    #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, d1Smoothed[n])
                    #     coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, zero)
                    #     nodeIdentifier += 1

                elif n2 == 2:
                    xLen = len(xRow3)
                    xFirstHalf += xRow3
                    d1FirstHalf += d1Row3
                    d2FirstHalf += [[0.0, 0.0, 0.0]] * xLen

                elif n2 < elementsCountAlongSegment - 1: # Middle
                    xLen = len(xMiddleAlongS2[n2 - 3])
                    xFirstHalf += xMiddleAlongS2[n2 - 3]
                    d1FirstHalf += d1MiddleAlongS2[n2 - 3]
                    d2FirstHalf += [[0.0, 0.0, 0.0]] * xLen

                elif n2 == elementsCountAlongSegment - 1:
                    xLen = len(xRowBelowEndProfile)
                    xFirstHalf += xRowBelowEndProfile
                    d1FirstHalf += d1RowBelowEndProfile
                    d2FirstHalf += [[0.0, 0.0, 0.0]] * xLen

            else:
                xLen = len(xAll2[n2 * nAround2: (n2 + 1) * nAround2])
                xFirstHalf  += xAll2[n2 * nAround2: (n2 + 1) * nAround2]
                d1FirstHalf += d1All2[n2 * nAround2: (n2 + 1) * nAround2]
                d2FirstHalf += d2All2[n2 * nAround2: (n2 + 1) * nAround2]

            # Transform so that we get second half
            xSecondHalf, d1SecondHalf, d2SecondHalf = getSecondHalfNodesAndDerivatives(xFirstHalf,
                                                                                       d1FirstHalf,
                                                                                       d2FirstHalf,
                                                                                       elementsCountAroundTC,
                                                                                       d1ArrangeTC[n2])

            # Replace d1 on TC3 in second half -
            # CHECK TO SEE IF THERE ARE OTHER SPECIAL CASES THAT NEEDS TO BE ADDRESSED
            if n2 == 1:
                for nTC in range(int(elementsCountAroundTC * 0.5)):
                    d1SecondHalf[nTC + 1] = vector.setMagnitude(d1InnerMat[0][nAround1 + elementsCountAroundHaustrum + int(elementsCountAroundTC * 0.5) + nTC], vector.magnitude(d1FirstHalf[-(nTC + 1)]))

            # Add both halves to xAround
            xAround += xFirstHalf[1:] + (xSecondHalf if 1 < n2 < elementsCountAlongSegment - 1 else xSecondHalf[1:])
            d1Around += d1FirstHalf[1:] + (d1SecondHalf if 1 < n2 < elementsCountAlongSegment - 1 else d1SecondHalf[1:])
            d2Around += d2FirstHalf[1:] + (d2SecondHalf if 1 < n2 < elementsCountAlongSegment - 1 else d2SecondHalf[1:])

            if n2 < 2:
                transitElementAround += ([1] + [0] * (xLen - 1 - int(elementsCountAroundTC * 0.5 + 1)) + [1] +
                                         [0] * elementsCountAroundTC +
                                         [1] + [0] * (xLen - 1 - int(elementsCountAroundTC * 0.5 + 1)) + [1] +
                                         [0]*int(elementsCountAroundTC * 0.5))
            elif n2 > elementsCountAlongSegment - 2:
                transitElementAround += ([1] + [0] * ((xLen - 1) * 2) + [1] + [0] * int(elementsCountAroundTC * 0.5))
            else:
                transitElementAround += ([1] + [0] * ((xLen - 1) * 2 + 1) + [1] + [0] * int(elementsCountAroundTC * 0.5))
            # print('n2 = ', n2, '2nd part transitElement = ', transitElementAround)
            xInnerMat.append(xAround)
            d1InnerMat.append(d1Around)
            d2InnerMat.append(d2Around)
            d3Around = [0.0, 0.0, 0.0] * len(xAround)
            d3InnerMat.append(d3Around)
            curvatureAlongAround = [[0.0]] * len(xAround)
            curvatureAlongMat.append(curvatureAlongAround)
            transitElementMat.append(transitElementAround)

        # Re-calculate d1 at junction
        xToSmooth = [xInnerMat[elementsCountAlongSegment - 2][int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5)],
                     xJunction,
                     xInnerMat[elementsCountAlongSegment - 1][int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5 + 1)]]
        dToSmooth = [d1InnerMat[elementsCountAlongSegment - 2][int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5)],
                     d1Junction,
                     d1InnerMat[elementsCountAlongSegment - 1][int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5 + 1)]]
        d1Junction = interp.smoothCubicHermiteDerivativesLine(xToSmooth, dToSmooth, fixStartDerivative= True, fixEndDerivative= True)[1]
        d1InnerMat[elementsCountAlongSegment - 1][int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5)] = d1Junction

        # Calculate curvature along
        # Section 1
        for n1 in range(nAround1):
            xAlong = []
            d2Along = []
            d3Along = []
            for n2 in range(len(xInnerMat)):
                xAlong.append(xInnerMat[n2][n1])
                d2Along.append(d2InnerMat[n2][n1])
                d3Along.append(getD3(d1InnerMat[n2][n1], d2InnerMat[n2][n1]))
            curvature = getCurvatureAlong(xAlong, d2Along, d3Along)
            # Arrange in matrix form
            for n2 in range(len(xInnerMat)):
                curvatureAlongMat[n2][n1] = curvature[n2]

        # Find d2 in section 2 & transform to section 3
        # First elements along that connects from start to end profile
        for n1 in range(nAround1, nAround1 + int(elementsCountAroundHaustrum * 0.5 - 1)):
            xAlong = []
            d1Along = []
            d2Along = []
            d3Along = []
            xAlong.append(xInnerMat[0][n1])
            d1Along.append(d1InnerMat[0][n1])
            d2Along.append(d2InnerMat[0][n1]) # Start profile

            for n2 in range(1, elementsCountAlongSegment):
                v1 = xInnerMat[n2][n1]
                v2 = xInnerMat[n2 + 1][n1]
                d = [v2[c] - v1[c] for c in range(3)]
                arcLengthAlong = interp.computeCubicHermiteArcLength(v1, d, v2, d, False)
                ds2 = [c * arcLengthAlong for c in vector.normalise(d)]
                xAlong.append(v1)
                d2Along.append(ds2)
                d1Along.append(d1InnerMat[n2][n1])

            xAlong.append(xInnerMat[elementsCountAlongSegment][n1])
            d1Along.append(d1InnerMat[elementsCountAlongSegment][n1])
            d2Along.append(d2InnerMat[elementsCountAlongSegment][n1]) # End profile

            d2Smoothed = interp.smoothCubicHermiteDerivativesLine(xAlong, d2Along, fixStartDerivative=True,
                                                                  fixEndDerivative=True)
            d2SmoothedSecondHalf = getSymmetricalPointsInHaustrum(d2Smoothed)
            for n2 in range(len(d2Smoothed)):
                d3Along.append(getD3(d1Along[n2], d2Smoothed[n2]))
            curvature = getCurvatureAlong(xAlong, d2Smoothed, d3Along)

            for n2 in range(len(xInnerMat)):
                d2InnerMat[n2][n1] = d2Smoothed[n2]
                d2InnerMat[n2][-(n1 - nAround1 + 2)] = d2SmoothedSecondHalf[n2]
                curvatureAlongMat[n2][n1] = curvature[n2]
                curvatureAlongMat[n2][-(n1 - nAround1 + 2)] = curvature[n2]

        # Elements along that join to 6 points junction
        xAlong = []
        d1Along = []
        d2Along = []
        d3Along = []
        n1 = nAround1 + int(elementsCountAroundHaustrum * 0.5 - 1)
        xAlong.append(xInnerMat[0][n1])
        d1Along.append(d1InnerMat[0][n1])
        d2Along.append(d2InnerMat[0][n1])  # Start profile

        for n2 in range(1, elementsCountAlongSegment - 1):
            v1 = xInnerMat[n2][n1]
            v2 = xInnerMat[n2 + 1][n1]
            d = [v2[c] - v1[c] for c in range(3)]
            arcLengthAlong = interp.computeCubicHermiteArcLength(v1, d, v2, d, False)
            ds2 = [c * arcLengthAlong for c in vector.normalise(d)]
            xAlong.append(v1)
            d1Along.append(d1InnerMat[n2][n1])
            d2Along.append(ds2)

        # End at junction
        xAlong.append(xJunction)
        d2Along.append(d1Junction)

        # d2 for junction
        dRot = matrix.rotateAboutZAxis(d1Junction, -math.pi / 180 * 15)
        dReflect = [dRot[1], dRot[0], dRot[2]]
        d2Junction = matrix.rotateAboutZAxis(dReflect, math.pi / 180 * 15)
        d2InnerMat[-2][nAround1 + int(elementsCountAroundHaustrum * 0.5) - 1] = d2Junction

        # d3 for junction
        d3Junction = getD3(d1Junction, d2Junction)

        d2Smoothed = interp.smoothCubicHermiteDerivativesLine(xAlong, d2Along, fixStartDerivative=True,
                                                              fixEndDerivative=True)
        d2SmoothedSecondHalf = getSymmetricalPointsInHaustrum(d2Smoothed)

        for n2 in range(len(d2Smoothed) - 1): # To exclude junction
            d3Along.append(getD3(d1Along[n2], d2Smoothed[n2]))
        d3Along.append(d3Junction) # add d3 for junction
        curvature = getCurvatureAlong(xAlong, d2Smoothed, d3Along)

        for n2 in range(elementsCountAlongSegment - 1):  # Exclude d2 junction
            d2InnerMat[n2][n1] = d2Smoothed[n2]
            d2InnerMat[n2][-int(elementsCountAroundHaustrum * 0.5 + 1)] = d2SmoothedSecondHalf[n2]

        for n2 in range(elementsCountAlongSegment):
            curvatureAlongMat[n2][n1] = curvature[n2]
            curvatureAlongMat[n2][-int(elementsCountAroundHaustrum * 0.5 + 1)] = curvature[n2]

        # Curvature from 6 point junction, end profile
        n1AboveJunction = int((elementsCountAroundHaustrum + elementsCountAroundTC) * 1.5)
        x = xInnerMat[len(xInnerMat) - 1][n1AboveJunction]
        d2 = d2InnerMat[len(xInnerMat) - 1][n1AboveJunction]
        d1 = d1InnerMat[len(xInnerMat) - 1][n1AboveJunction]
        d3 = getD3(d1, d2)

        xPrev = xJunction
        dPrev = [x[i] - xPrev[i] for i in range(3)]

        curvatureAlongMat[len(xInnerMat) - 1][n1AboveJunction] = interp.getCubicHermiteCurvature(xPrev, dPrev, x, d2, d3, 1.0)

        # Elements along 2 columns before TC3 (same function as column before tc3)
        xAlong = []
        d1Along = []
        d2Along = []
        d3Along = []
        n1 = nAround1 + int(elementsCountAroundHaustrum * 0.5) + 1
        xAlong.append(xInnerMat[0][n1])
        d1Along.append(d1InnerMat[0][n1])
        d2Along.append([0.0, 0.0, segmentLength / elementsCountAlongSegment])

        xAlong += [xInnerMat[1][n1],
                   xInnerMat[2][int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5)],
                   xInnerMat[2][int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5) - 1]]

        d1Along += [d1InnerMat[1][n1],
                    d2InnerMat[2][int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5)]]

        for n2 in range(1, 3):  # might have to work on changing 3 to depend on some variable
            v1 = xAlong[n2]
            v2 = xAlong[n2 + 1]
            d = [v2[c] - v1[c] for c in range(3)]
            arcLengthAlong = interp.computeCubicHermiteArcLength(v1, d, v2, d, False)
            ds2 = [c * arcLengthAlong for c in vector.normalise(d)]
            d2Along.append(ds2)

        xToSmooth = xAlong[:-1]

        d2Smoothed = interp.smoothCubicHermiteDerivativesLine(xToSmooth, d2Along, fixStartDirection=True, fixEndDerivative=True)
        d2SmoothedSecondHalf = getSymmetricalPointsInHaustrum(d2Smoothed)
        for n2 in range(len(d2Smoothed)):
            d3Along.append(getD3(d1Along[n2], d2Smoothed[n2]))
        curvature = getCurvatureAlong(xToSmooth, d2Smoothed, d3Along)

        for n2 in range(2):  # exclude derivatives at last point
            d2InnerMat[n2][n1] = d2Smoothed[n2]
            d2InnerMat[n2][-int(elementsCountAroundHaustrum * 0.5 + 3)] = d2SmoothedSecondHalf[n2]
            curvatureAlongMat[n2][n1] = curvature[n2]
            curvatureAlongMat[n2][-int(elementsCountAroundHaustrum * 0.5 + 3)] = curvature[n2]

        # Elements along where triple point sits
        n1 = nAround1 + int(elementsCountAroundHaustrum * 0.5)
        triplePointRow = 1
        triplePoint = xInnerMat[triplePointRow][n1]
        d1InnerMat[triplePointRow][n1] = d1TriplePoint = vector.setMagnitude(d1New0, vector.magnitude(d2New0)) # need to make the same for reflected side
        d1Reflected = getSymmetricalPointsInHaustrum([d1TriplePoint])[0]

        d2InnerMat[triplePointRow][n1] = d2TriplePoint = d2New0
        d2InnerMat[triplePointRow][-int(elementsCountAroundHaustrum * 0.5 + 2)] = \
        getSymmetricalPointsInHaustrum([d2TriplePoint])[0]
        d3TriplePoint = getD3(d1TriplePoint, d2TriplePoint)

        rotAxis = getD3(d1Reflected, d2InnerMat[triplePointRow][-int(elementsCountAroundHaustrum * 0.5 + 2)])
        rotMat = matrix.getRotationMatrixFromAxisAngle(rotAxis, math.pi)
        d1InnerMat[triplePointRow][-int(elementsCountAroundHaustrum * 0.5 + 2)] = [rotMat[j][0] * d1Reflected[0] + rotMat[j][1] * d1Reflected[1] + rotMat[j][2] * d1Reflected[2] for j in range(3)]

        startNodeToTriple = [triplePoint[c] - xInnerMat[0][n1][c] for c in range(3)]
        d2InnerMat[0][n1] = ([0.0, 0.0, vector.magnitude(startNodeToTriple)])
        d3Start = getD3(d1InnerMat[0][n1], d2InnerMat[0][n1])
        d2InnerMat[0][-int(elementsCountAroundHaustrum * 0.5 + 2)] = getSymmetricalPointsInHaustrum([d2InnerMat[0][n1]])[0]

        xAlong = [xInnerMat[0][n1], triplePoint, xInnerMat[triplePointRow][n1 + 1]]
        d2Along = [[0.0, 0.0, vector.magnitude(startNodeToTriple)], d2TriplePoint, d1InnerMat[triplePointRow][n1 + 1]]
        d3End = getD3(d1InnerMat[triplePointRow][n1 + 1], d2InnerMat[triplePointRow][n1 + 1])
        d3Along = [d3Start, d3TriplePoint, d3End]
        curvature = getCurvatureAlong(xAlong, d2Along, d3Along)
        for n2 in range(2):  # exclude derivatives at last point
            curvatureAlongMat[n2][n1] = curvature[n2]
            curvatureAlongMat[n2][-int(elementsCountAroundHaustrum * 0.5 + 2)] = curvature[n2]

        # ##################################################################################################
        # nodeIdentifier = 80000
        # # for n in range(len(xAlong)):
        # node = nodes.createNode(nodeIdentifier, nodetemplate)
        # cache.setNode(node)
        # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, triplePointTest)
        # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, zero)
        # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, zero)
        # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, zero)
        # nodeIdentifier += 1
        # ######################################################################################################

        # Elements along column before TC3
        xAlong = []
        d1Along = []
        d2Along = []
        d3Along = []
        n1 = int(elementsCountAroundTC * 1.5 + elementsCountAroundHaustrum * 2) - 1
        xAlong.append(xInnerMat[0][n1])
        d1Along.append(d1InnerMat[0][n1])
        d2Along.append([0.0, 0.0, segmentLength / elementsCountAlongSegment])

        xAlong += [xInnerMat[1][n1],
                   xInnerMat[3][int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5)],
                   xInnerMat[3][int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5) - 1]]

        d1Along += [d1InnerMat[1][n1],
                   d2InnerMat[3][int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5)]]

        for n2 in range(1, 3):  # might have to work on changing 3 to depend on some variable
            v1 = xAlong[n2]
            v2 = xAlong[n2 + 1]
            d = [v2[c] - v1[c] for c in range(3)]
            arcLengthAlong = interp.computeCubicHermiteArcLength(v1, d, v2, d, False)
            ds2 = [c * arcLengthAlong for c in vector.normalise(d)]
            d2Along.append(ds2)

        xToSmooth = xAlong[:-1]

        d2Smoothed = interp.smoothCubicHermiteDerivativesLine(xToSmooth, d2Along, fixStartDirection=True, fixEndDerivative=True)
        d2SmoothedSecondHalf = getSymmetricalPointsInHaustrum(d2Smoothed)
        for n2 in range(len(d2Smoothed)):
            d3Along.append(getD3(d1Along[n2], d2Smoothed[n2]))
        curvature = getCurvatureAlong(xToSmooth, d2Smoothed, d3Along)

        for n2 in range(2):  # exclude derivatives at last point
            d2InnerMat[n2][n1] = d2Smoothed[n2]
            d2InnerMat[n2][-elementsCountAroundHaustrum] = d2SmoothedSecondHalf[n2]
            curvatureAlongMat[n2][n1] = curvature[n2]
            curvatureAlongMat[n2][-elementsCountAroundHaustrum] = curvature[n2]

        # Elements along column between tc3 and ostium
        for n2 in range(2):  # assuming only 2 elements between start profile and ostium along TC
            for nTC in range(int(elementsCountAroundTC * 0.5 + 1)):
                d2InnerMat[n2][int(elementsCountAroundTC * 1.5 + elementsCountAroundHaustrum * 2) + nTC] = d2AlongBetweenTC3Ostium[nTC][n2]
                d2InnerMat[n2][-int(elementsCountAroundHaustrum + 1 + nTC)] = getSymmetricalPointsInHaustrum([d2AlongBetweenTC3Ostium[nTC][n2]])[0]

        for nTC in range(int(elementsCountAroundTC * 0.5 + 1)):
            xAlong = []
            d2Along = []
            d3Along = []
            for n2 in range(2):
                xAlong.append(xAlongBetweenTC3Ostium[nTC][n2])
                d2Along.append(d2AlongBetweenTC3Ostium[nTC][n2])
                d3Along.append(getD3(d1InnerMat[n2][nAround1 + nAround2 + nTC], d2AlongBetweenTC3Ostium[nTC][n2]))
            curvature = getCurvatureAlong(xAlong, d2Along, d3Along)
            # Arrange in matrix form
            for n2 in range(2):
                curvatureAlongMat[n2][int(elementsCountAroundTC * 1.5 + elementsCountAroundHaustrum * 2) + nTC] = curvature[n2]
                curvatureAlongMat[n2][-int(elementsCountAroundHaustrum + 1)] = curvature[n2]

        # Append curvature for second half of tc1
        for n2 in range(len(xInnerMat)):
            for nTC in range(int(elementsCountAroundTC * 0.5)):
                curvature = curvatureAlongMat[n2][nAround1 - 1 - nTC]
                curvatureAlongMat[n2][-int(elementsCountAroundTC * 0.5 - nTC)] = curvature

        # Transform d1 on bottom 4 rows so that first half matches second half
        for n2 in range(2):
            for n1 in range(int(elementsCountAroundHaustrum * 0.5) + 1):
                nodeIdx = int((elementsCountAroundHaustrum + elementsCountAroundTC) * 1.5) + n1
                d1 = d1InnerMat[n2][nodeIdx]
                d1Mirror = getSymmetricalPointsInHaustrum([d1])[0]
                rotAxis = vector.normalise(
                    vector.crossproduct3(vector.normalise(d1Mirror), vector.normalise(d2InnerMat[n2][nodeIdx])))
                rotMat = matrix.getRotationMatrixFromAxisAngle(rotAxis, math.pi)
                d1Rot = [rotMat[j][0] * d1Mirror[0] + rotMat[j][1] * d1Mirror[1] + rotMat[j][2] * d1Mirror[2] for j in
                         range(3)]
                d1InnerMat[n2][-(n1 + int((elementsCountAroundHaustrum + elementsCountAroundTC) * 0.5))] = d1Rot

                # nodeIdentifier = 1000*(n2+1) + n1
                # node = nodes.createNode(nodeIdentifier, nodetemplate)
                # cache.setNode(node)
                # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, xInnerMat[n2][nodeIdx])
                # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, zero)
                # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, zero)
                # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, zero)
                # nodeIdentifier += 1
                #
                # nodeIdentifier = 10000*(n2+1) + n1
                # node = nodes.createNode(nodeIdentifier, nodetemplate)
                # cache.setNode(node)
                # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, xInnerMat[n2][-(n1 + int((elementsCountAroundHaustrum + elementsCountAroundTC) * 0.5))])
                # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, zero)
                # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, zero)
                # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, zero)
                # nodeIdentifier += 1

        # nodeIdentifier = 10000
        for n2 in range(2, 4):
            nodeIdx = int((elementsCountAroundHaustrum + elementsCountAroundTC) * 1.5)
            d1 = d1InnerMat[n2][nodeIdx]
            d1Mirror = getSymmetricalPointsInHaustrum([d1])[0]
            rotAxis = vector.normalise(vector.crossproduct3(vector.normalise(d1Mirror), vector.normalise(d2InnerMat[n2][nodeIdx])))
            rotMat = matrix.getRotationMatrixFromAxisAngle(rotAxis, math.pi)
            d1Rot = [rotMat[j][0] * d1Mirror[0] + rotMat[j][1] * d1Mirror[1] + rotMat[j][2] * d1Mirror[2] for j in range(3)]
            d1InnerMat[n2][nodeIdx + 1] = d1Rot

            # nodeIdentifier = 1000 * (n2 + 1)
            # node = nodes.createNode(nodeIdentifier, nodetemplate)
            # cache.setNode(node)
            # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, xInnerMat[n2][nodeIdx])
            # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, d1)
            # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, zero)
            # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, zero)
            # nodeIdentifier += 1
            #
            # nodeIdentifier = 10000*(n2+1)
            # node = nodes.createNode(nodeIdentifier, nodetemplate)
            # cache.setNode(node)
            # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, xInnerMat[n2][nodeIdx + 1])
            # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, zero)
            # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, zero)
            # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, d1Mirror)
            # nodeIdentifier += 1

        # Calculate unit d3
        for n2 in range(len(xInnerMat)):
            for n1 in range(len(xInnerMat[n2])):
                d3 = vector.crossproduct3(vector.normalise(d1InnerMat[n2][n1]), vector.normalise(d2InnerMat[n2][n1]))
                d3InnerMat[n2][n1] = vector.normalise(d3)

        # # ##################################################################################################
        # nodeIdentifier = 8000 # nextNodeIdentifier
        # for n2 in range(len(xInnerMat)):
        #     for n1 in range(len(xInnerMat[n2])):
        #         node = nodes.createNode(nodeIdentifier, nodetemplate)
        #         cache.setNode(node)
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, xInnerMat[n2][n1])
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, d1InnerMat[n2][n1])
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, d2InnerMat[n2][n1])
        #         coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, zero)
        #         if useCrossDerivatives:
        #             coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, zero)
        #             coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS3, 1, zero)
        #             coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS2DS3, 1, zero)
        #             coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D3_DS1DS2DS3, 1, zero)
        #         # print('NodeIdentifier = ', nodeIdentifier, xAll3[n]) #, d1[n], d2[n])
        #         nodeIdentifier = nodeIdentifier + 1
        # # ######################################################################################################

        xMat, d1Mat, d2Mat, d3Mat = getCoordinatesFromInner(xInnerMat, d1InnerMat, d2InnerMat, d3InnerMat,
                                              wallThicknessList, elementsCountThroughWall, transitElementMat,
                                              curvatureAlongMat)

        # Need to correct derivatives on outer surface at 6 way junction as getCoordinatesFromInner uses
        # curvature to scale d2 but it's d1 that should be scaled at the junction (dealing with just one element through wall)
        n2 = elementsCountAlongSegment - 1
        n3 = 1
        n1 = int((elementsCountAroundHaustrum + elementsCountAroundTC) * 1.5)

        curvatureJunction = curvatureAlongMat[n2][n1]
        distance = vector.magnitude([xMat[n2][n3][n1][i] - xMat[n2][0][n1][i] for i in range(3)])
        factor = 1.0 - curvatureJunction * distance
        d1OuterJunction = [factor * c for c in d1InnerMat[n2][n1]]
        d1Mat[n2][n3][n1] = d1OuterJunction
        dRot = matrix.rotateAboutZAxis(d1OuterJunction, -math.pi / 180 * 15)
        dReflect = [dRot[1], dRot[0], dRot[2]]
        d2Mat[n2][n3][n1] = matrix.rotateAboutZAxis(dReflect, math.pi / 180 * 15)

        # Need to correct derivative on outer surface for node on xRow3 connecting to xNew1, and same for nodes above
        # as getCoordinatesFromInner saw that node as joining directly to the reflected node
        for i in range(2):
            n2 = 2 + i
            n1 = int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5)
            prevIdx = n1 - 1
            kappam = interp.getCubicHermiteCurvatureSimple(xInnerMat[n2][prevIdx], d1InnerMat[n2][prevIdx],
                                                           xInnerMat[n2][n1], d1InnerMat[n2][n1], 1.0)
            kappap = interp.getCubicHermiteCurvatureSimple(xInnerMat[n2][n1], d1InnerMat[n2][n1],
                                                           xInnerMat[1][n1 + (2 if i == 0 else 3)], [-1.0 * d2InnerMat[1][n1 + (2 if i == 0 else 3)][c] for c in range(3)], 0.0)
            curvatureAround = 0.5 * (kappam + kappap)
            factor = 1.0 - wallThickness * curvatureAround
            d1Mat[n2][1][n1] = [factor * c for c in d1InnerMat[n2][n1]]
            # d1Mat[n2][1][-int(elementsCountAroundHaustrum * 0.5 + 1)] = [factor * c for c in d1InnerMat[n2][-int(elementsCountAroundHaustrum * 0.5 + 1)]]

        # Need to correct derivative on triple point
        n1 = nAround1 + int(elementsCountAroundHaustrum * 0.5)
        curvatureAtTriplePoint = curvatureAlongMat[triplePointRow][n1]
        factor = 1.0 - wallThickness * curvatureAround
        d1Mat[triplePointRow][1][n1] = [factor * c for c in d1InnerMat[triplePointRow][n1]]
        d1Mat[triplePointRow][1][-int(elementsCountAroundHaustrum * 0.5 + 2)] = \
            [factor * c for c in d1InnerMat[triplePointRow][-int(elementsCountAroundHaustrum * 0.5 + 2)]]

        # Correct derivative on outer surface for node next to triple point
        n1 = nAround1 + int(elementsCountAroundHaustrum * 0.5) + 1
        kappam = interp.getCubicHermiteCurvatureSimple(triplePoint, d2New0, xInnerMat[triplePointRow][n1],
                                                       d1InnerMat[triplePointRow][n1], 1.0)
        kappap = interp.getCubicHermiteCurvatureSimple(xInnerMat[triplePointRow][n1], d1InnerMat[triplePointRow][n1],
                                                       xInnerMat[triplePointRow][n1 + 1], d1InnerMat[triplePointRow][n1 + 1],
                                                       0.0)
        curvatureAround = 0.5 * (kappam + kappap)
        factor = 1.0 + wallThickness * curvatureAround
        d1Mat[triplePointRow][1][n1] = [factor * c for c in d1InnerMat[triplePointRow][n1]]
        d1Mat[triplePointRow][1][-int(elementsCountAroundHaustrum * 0.5 + 3)] = \
            [factor * c for c in d1InnerMat[triplePointRow][-int(elementsCountAroundHaustrum * 0.5 + 3)]]

        # Create nodes and elements
        annotationGroupsAround = []
        for i in range(elementsCountAround):
            annotationGroupsAround.append([ ])

        nextNodeIdentifier, nextElementIdentifier, annotationGroups = createNodesAndElements(
            region, xMat, d1Mat, d2Mat, d3Mat,
            elementsCountAroundTC, elementsCountAroundHaustrum,
            elementsCountAlongSegment, elementsCountThroughWall,
            annotationGroupsAround, annotationGroupsAlong, annotationGroupsThroughWall,
            nextNodeIdentifier, nextElementIdentifier, useCubicHermiteThroughWall, useCrossDerivatives, elementsCountAroundOstium)

        # Annulus
        endPoints_x = [[None] * elementsCountAroundOstium, [None] * elementsCountAroundOstium]
        endPoints_d1 = [[None] * elementsCountAroundOstium, [None] * elementsCountAroundOstium]
        endPoints_d2 = [[None] * elementsCountAroundOstium, [None] * elementsCountAroundOstium]
        endPoints_Id = [[None] * elementsCountAroundOstium, [None] * elementsCountAroundOstium]
        endDerivativesMap = [[None] * elementsCountAroundOstium, [None] * elementsCountAroundOstium]

        count = 0
        n2 = 1
        n1 = int((elementsCountAroundTC + elementsCountAroundHaustrum) * 2)
        for n3 in range(2):
            endPoints_x[n3][count] = xMat[n2][n3][n1]
            endPoints_d1[n3][count] = d1Mat[n2][n3][n1]
            endPoints_d2[n3][count] = d2Mat[n2][n3][n1]
            endPoints_Id[n3][count] = findNodeIdFromMatIdx(n1, n2, n3, nodesCountOstium, xMat)
            endDerivativesMap[n3][count] = ((-1, 0, 0), (0, -1, 0), None)
        count += 1

        for nOstium in range(1, int(elementsCountAroundOstium * 0.5) + 1):
            n2 = nOstium + 2
            n1 = int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5)
            for n3 in range(2):
                endPoints_x[n3][count] = xMat[n2][n3][n1]
                endPoints_d1[n3][count] = d1Mat[n2][n3][n1]
                endPoints_d2[n3][count] = d2Mat[n2][n3][n1]
                endPoints_Id[n3][count] = findNodeIdFromMatIdx(n1, n2, n3, nodesCountOstium, xMat)
                # if nOstium == 1:
                #     endDerivativesMap[n3][count] = ((-1, 0, 0), (-1, -1, 0), None, (0, 1, 0))
                if nOstium == int(elementsCountAroundOstium * 0.5): # 6 way junction
                    endDerivativesMap[n3][count] = ((1, 0, 0), (1, 1, 0), None, (0, -1, 0))
                elif nOstium > int(elementsCountAroundOstium * 0.5):
                    endDerivativesMap[n3][count] = ((0, -1, 0), (1, 0, 0), None)
                else:
                    endDerivativesMap[n3][count] = ((0, 1, 0), (-1, 0, 0), None)
            count += 1

        for nOstium in range(1, int(elementsCountAroundOstium * 0.5)):
            n2 = len(xMat) - nOstium - 2
            n1 = int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5) + 1

            for n3 in range(2):
                endPoints_x[n3][count] = xMat[n2][n3][n1]
                endPoints_d1[n3][count] = d1Mat[n2][n3][n1]
                endPoints_d2[n3][count] = d2Mat[n2][n3][n1]
                endPoints_Id[n3][count] = findNodeIdFromMatIdx(n1, n2, n3, nodesCountOstium, xMat)
                endDerivativesMap[n3][count] = ((0, -1, 0), (1, 0, 0), None)
            count += 1

        nextNodeIdentifier, nextElementIdentifier = createAnnulusMesh3d(
            nodes, mesh, nextNodeIdentifier, nextElementIdentifier,
            o1_x, o1_d1, o1_d2, None, o1_NodeId, None,
            endPoints_x, endPoints_d1, endPoints_d2, None, endPoints_Id, endDerivativesMap)

        # Delete annulus mesh elements near bottom
        # deleteElementIdentifier = [nextElementIdentifier - len(o1_x[0]), nextElementIdentifier - len(o1_x[0]) + 1, nextElementIdentifier - 1, nextElementIdentifier - 2]
        deleteElementIdentifier = [nextElementIdentifier - len(o1_x[0]), nextElementIdentifier - 1]
        mesh_destroy_elements_and_nodes_by_identifiers(mesh, deleteElementIdentifier)

        # Make elements between tc and ostium - Need to renumber elements later!!!
        #nextElementIdentifier =
        # #nextNodeIdentifier =

        fm.endChange()

        return annotationGroups

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

def getCoordinatesFromInner(xInnerMat, d1InnerMat, d2InnerMat, d3InnerMat,
    wallThicknessList, elementsCountThroughWall, transitElementMat, curvatureAlongMat):
    """
    EDIT
    Generates coordinates from inner to outer surface using coordinates
    and derivatives of inner surface.
    :param xInner: Coordinates on inner surface
    :param d1Inner: Derivatives on inner surface around tube
    :param d2Inner: Derivatives on inner surface along tube
    :param d3Inner: Derivatives on inner surface through wall
    :param wallThicknessList: Wall thickness for each element along tube
    :param elementsCountAround: Number of elements around tube
    :param elementsCountAlong: Number of elements along tube
    :param elementsCountThroughWall: Number of elements through tube wall
    :param transitElementList: stores true if element around is a transition
    element that is between a big and a small element.
    return nodes and derivatives for mesh, and curvature along inner surface.
    """
    xOuterMat = []
    curvatureAroundInnerMat = []
    xMat = []
    d1Mat = []
    d2Mat = []
    d3Mat = []

    for n2 in range(len(xInnerMat)):
        wallThickness = wallThicknessList[n2]
        xAlong = []
        curvatureAroundAlong = []
        transitElementAround = transitElementMat[n2]
        xMatAround = []
        d1MatAround = []
        d2MatAround = []
        d3MatAround = []

        for n1 in range(len(xInnerMat[n2])):
            norm = d3InnerMat[n2][n1]
            # Calculate outer coordinates
            x = [xInnerMat[n2][n1][i] + norm[i]*wallThickness for i in range(3)]
            xAlong.append(x)

            # Calculate curvature along elements around
            prevIdx = n1 - 1 if n1 != 0 else -1
            nextIdx = n1 + 1 if (n1 < len(xInnerMat[n2]) - 1) else 0
            kappam = interp.getCubicHermiteCurvatureSimple(xInnerMat[n2][prevIdx], d1InnerMat[n2][prevIdx],
                                                           xInnerMat[n2][n1], d1InnerMat[n2][n1], 1.0)
            kappap = interp.getCubicHermiteCurvatureSimple(xInnerMat[n2][n1], d1InnerMat[n2][n1],
                                                           xInnerMat[n2][nextIdx], d1InnerMat[n2][nextIdx], 0.0)
            if not transitElementAround[n1] and not transitElementAround[n1-1]:
                curvatureAround = 0.5*(kappam + kappap)
            elif transitElementAround[n1]:
                curvatureAround = kappam
            elif transitElementAround[n1 - 1]:
                curvatureAround = kappap

            curvatureAroundAlong.append(curvatureAround)

        curvatureAroundInnerMat.append(curvatureAroundAlong)
        xOuterMat.append(xAlong)

        for n3 in range(elementsCountThroughWall + 1):
            xi3 = 1/elementsCountThroughWall * n3
            xThroughWall = []
            d1ThroughWall = []
            d2ThroughWall = []
            d3ThroughWall = []

            for n1 in range(len(xInnerMat[n2])):
                norm = d3InnerMat[n2][n1]
                innerx = xInnerMat[n2][n1]
                outerx = xOuterMat[n2][n1]
                dWall = [wallThickness*c for c in norm]
                # x
                x = interp.interpolateCubicHermite(innerx, dWall, outerx, dWall, xi3)
                xThroughWall.append(x)

                # dx_ds1
                factor = 1.0 + wallThickness*xi3 * curvatureAroundInnerMat[n2][n1]
                d1 = [ factor*c for c in d1InnerMat[n2][n1]]
                d1ThroughWall.append(d1)

                # dx_ds2
                curvature = curvatureAlongMat[n2][n1]
                distance = vector.magnitude([x[i] - xInnerMat[n2][n1][i] for i in range(3)])
                # print(n2, n1, curvature, distance)
                factor = 1.0 - curvature * distance
                d2 = [factor * c for c in d2InnerMat[n2][n1]]
                d2ThroughWall.append(d2)

                # dx_ds3
                d3 = [c * wallThickness / elementsCountThroughWall for c in norm]
                d3ThroughWall.append(d3)

            xMatAround.append(xThroughWall)
            d1MatAround.append(d1ThroughWall)
            d2MatAround.append(d2ThroughWall)
            d3MatAround.append(d3ThroughWall)

        xMat.append(xMatAround)
        d1Mat.append(d1MatAround)
        d2Mat.append(d2MatAround)
        d3Mat.append(d3MatAround)

    return xMat, d1Mat, d2Mat, d3Mat

def createNodesAndElements(region,
    xMat, d1Mat, d2Mat, d3Mat,
    elementsCountAroundTC, elementsCountAroundHaustrum, elementsCountAlong, elementsCountThroughWall,
    annotationGroupsAround, annotationGroupsAlong, annotationGroupsThroughWall,
    firstNodeIdentifier, firstElementIdentifier,
    useCubicHermiteThroughWall, useCrossDerivatives, elementsCountAroundOstium):
    """
    Create nodes and elements for the coordinates, flat coordinates,
    and texture coordinates field.
    :param x, d1, d2, d3: coordinates and derivatives of coordinates field.
    :param xFlat, d1Flat, d2Flat, d3Flat: coordinates and derivatives of
    flat coordinates field.
    :param xTexture, d1Texture, d2Texture, d3Texture: coordinates and derivatives
    of texture coordinates field.
    :param elementsCountAround: Number of elements around tube.
    :param elementsCountAlong: Number of elements along tube.
    :param elementsCountThroughWall: Number of elements through wall.
    :param annotationGroupsAround: Annotation groups of elements around.
    :param annotationGroupsAlong: Annotation groups of elements along.
    :param annotationGroupsThroughWall: Annotation groups of elements through wall.
    :param firstNodeIdentifier, firstElementIdentifier: first node and
    element identifier to use.
    :param useCubicHermiteThroughWall: use linear when false
    :param useCrossDerivatives: use cross derivatives when true
    :return nodeIdentifier, elementIdentifier, allAnnotationGroups
    """

    nodeIdentifier = firstNodeIdentifier
    elementIdentifier = firstElementIdentifier
    zero = [ 0.0, 0.0, 0.0 ]

    fm = region.getFieldmodule()
    fm.beginChange()
    cache = fm.createFieldcache()

    # Coordinates field
    coordinates = findOrCreateFieldCoordinates(fm)
    nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
    nodetemplate = nodes.createNodetemplate()
    nodetemplate.defineField(coordinates)
    nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_VALUE, 1)
    nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D_DS1, 1)
    nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D_DS2, 1)
    if useCrossDerivatives:
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D2_DS1DS2, 1)
    if useCubicHermiteThroughWall:
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D_DS3, 1)
        if useCrossDerivatives:
            nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D2_DS1DS3, 1)
            nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D2_DS2DS3, 1)
            nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D3_DS1DS2DS3, 1)

    mesh = fm.findMeshByDimension(3)

    if useCubicHermiteThroughWall:
        eftfactory = eftfactory_tricubichermite(mesh, useCrossDerivatives)
    else:
        eftfactory = eftfactory_bicubichermitelinear(mesh, useCrossDerivatives)
    eft = eftfactory.createEftBasic()

    elementtemplate = mesh.createElementtemplate()
    elementtemplate.setElementShapeType(Element.SHAPE_TYPE_CUBE)
    result = elementtemplate.defineField(coordinates, -1, eft)

    elementtemplateX = mesh.createElementtemplate()
    elementtemplateX.setElementShapeType(Element.SHAPE_TYPE_CUBE)

    # Create nodes
    # Coordinates field
    for n2 in range(len(xMat)):
        for n3 in range(len(xMat[n2])):
            for n1 in range(len(xMat[n2][n3])):
                node = nodes.createNode(nodeIdentifier, nodetemplate)
                cache.setNode(node)
                coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, xMat[n2][n3][n1])
                coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, d1Mat[n2][n3][n1])
                coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, d2Mat[n2][n3][n1])
                coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS3, 1, d3Mat[n2][n3][n1])
                if useCrossDerivatives:
                        coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, zero)
                        coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS3, 1, zero)
                        coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS2DS3, 1, zero)
                        coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D3_DS1DS2DS3, 1, zero)
                # if nodeIdentifier == 168:# or nodeIdentifier == 175:
                #     print('NodeIdentifier = ', nodeIdentifier, d1Mat[n2][n3][n1])
                nodeIdentifier = nodeIdentifier + 1

    # # create elements
    allAnnotationGroups = []

    # Create regular elements
    for e2 in range(len(xMat) - 1):
        startIdx = firstNodeIdentifier
        for n2 in range(e2):
            startIdx += len(xMat[n2][0]) * len(xMat[n2])
        for e3 in range(len(xMat[e2]) - 1):
            elementsCountAround1 = len(xMat[e2][e3])
            elementsCountAround2 = len(xMat[e2 + 1][e3])

            if e2 == 0:
                for e1 in range(elementsCountAround1):
                    bni1 = startIdx + e3 * (elementsCountAround1) + e1
                    bni2 = startIdx + e3 * (elementsCountAround1) + (e1 + 1 if e1 < elementsCountAround1 - 1 else 0)
                    bni3 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + e1
                    bni4 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + (
                        e1 + 1 if e1 < elementsCountAround1 - 1 else 0)
                    nodeIdentifiers = [bni1, bni2, bni3, bni4, bni1 + elementsCountAround1, bni2 + elementsCountAround1,
                                       bni3 + elementsCountAround2, bni4 + elementsCountAround2]

                    if e1 == int(elementsCountAroundTC + elementsCountAroundHaustrum)*1.5:
                        eft1 = eftfactory.createEftBasic()
                        setEftScaleFactorIds(eft1, [1], [])
                        scalefactors = [-1.0]
                        remapEftNodeValueLabel(eft1, [4, 8], Node.VALUE_LABEL_D_DS1,
                                               [(Node.VALUE_LABEL_D_DS1, []), (Node.VALUE_LABEL_D_DS2, [])])
                        elementtemplateX.defineField(coordinates, -1, eft1)
                        elementtemplate1 = elementtemplateX

                    elif e1 == int(elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5 + 1:
                        eft1 = eftfactory.createEftBasic()
                        setEftScaleFactorIds(eft1, [1], [])
                        scalefactors = [-1.0]
                        remapEftNodeValueLabel(eft1, [3, 7], Node.VALUE_LABEL_D_DS1,[(Node.VALUE_LABEL_D_DS1, []), (Node.VALUE_LABEL_D_DS2, [])])
                        elementtemplateX.defineField(coordinates, -1, eft1)
                        elementtemplate1 = elementtemplateX

                    elif e1 == int((elementsCountAroundTC + elementsCountAroundHaustrum) * 2) + elementsCountAroundTC + 1:
                        eft1 = eftfactory.createEftBasic()
                        setEftScaleFactorIds(eft1, [1], [])
                        scalefactors = [-1.0]
                        remapEftNodeValueLabel(eft1, [4, 8], Node.VALUE_LABEL_D_DS1,
                                               [(Node.VALUE_LABEL_D_DS1, []), (Node.VALUE_LABEL_D_DS2, [1])])
                        elementtemplateX.defineField(coordinates, -1, eft1)
                        elementtemplate1 = elementtemplateX

                    elif e1 == int(
                            (elementsCountAroundTC + elementsCountAroundHaustrum) * 2) + elementsCountAroundTC + 2:
                        eft1 = eftfactory.createEftBasic()
                        setEftScaleFactorIds(eft1, [1], [])
                        scalefactors = [-1.0]
                        remapEftNodeValueLabel(eft1, [3, 7], Node.VALUE_LABEL_D_DS1,
                                               [(Node.VALUE_LABEL_D_DS1, []), (Node.VALUE_LABEL_D_DS2, [1])])
                        elementtemplateX.defineField(coordinates, -1, eft1)
                        elementtemplate1 = elementtemplateX

                    else:
                        elementtemplate1 = elementtemplate
                        eft1 = eft
                        scalefactors = None

                    element = mesh.createElement(elementIdentifier, elementtemplate1)
                    element.setNodesByIdentifier(eft1, nodeIdentifiers)
                    element.setScaleFactors(eft1, scalefactors) if scalefactors else None
                    elementIdentifier = elementIdentifier + 1

            if e2 == len(xMat) - 2: # e2 < 1 or
                for e1 in range(elementsCountAround1):
                    bni1 = startIdx + e3 * (elementsCountAround1) + e1
                    bni2 = startIdx + e3 * (elementsCountAround1) + (e1 + 1 if e1 < elementsCountAround1 - 1 else 0)
                    bni3 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + e1
                    bni4 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + (e1 + 1 if e1 < elementsCountAround1 - 1 else 0)
                    nodeIdentifiers = [bni1, bni2, bni3, bni4, bni1 + elementsCountAround1, bni2 + elementsCountAround1,
                                       bni3 + elementsCountAround2, bni4 + elementsCountAround2]

                    if e2 == len(xMat) - 2 and e1 == (int(elementsCountAroundTC + elementsCountAroundHaustrum)*1.5 - 1):
                        eft1 = eftfactory.createEftBasic()
                        setEftScaleFactorIds(eft1, [1], [])
                        scalefactors = [-1.0]
                        remapEftNodeValueLabel(eft1, [2, 6], Node.VALUE_LABEL_D_DS1, [(Node.VALUE_LABEL_D_DS2, [1])])
                        remapEftNodeValueLabel(eft1, [2, 6], Node.VALUE_LABEL_D_DS2, [(Node.VALUE_LABEL_D_DS1, [ ]), (Node.VALUE_LABEL_D_DS2, [ ])])
                        elementtemplateX.defineField(coordinates, -1, eft1)
                        elementtemplate1 = elementtemplateX

                    elif e2 == len(xMat) - 2 and e1 == (int(elementsCountAroundTC + elementsCountAroundHaustrum)*1.5):
                        eft1 = eftfactory.createEftBasic()
                        setEftScaleFactorIds(eft1, [1], [])
                        scalefactors = [-1.0]
                        remapEftNodeValueLabel(eft1, [1, 5], Node.VALUE_LABEL_D_DS2,
                                               [(Node.VALUE_LABEL_D_DS1, [ ]), (Node.VALUE_LABEL_D_DS2, [ ])])
                        elementtemplateX.defineField(coordinates, -1, eft1)
                        elementtemplate1 = elementtemplateX

                    else:
                        elementtemplate1 = elementtemplate
                        eft1 = eft
                        scalefactors = None

                    element = mesh.createElement(elementIdentifier, elementtemplate1)
                    element.setNodesByIdentifier(eft1, nodeIdentifiers)
                    element.setScaleFactors(eft1, scalefactors) if scalefactors else None
                    elementIdentifier = elementIdentifier + 1

            if e2 == 1:
                for e1 in range(elementsCountAround1 - 6): # -6
                    if e1 < int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5): # +1
                        bni1 = startIdx + e3 * (elementsCountAround1) + e1
                        bni2 = startIdx + e3 * (elementsCountAround1) + (e1 + 1 if e1 < elementsCountAround1 - 1 else 0)
                        bni3 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + e1
                        bni4 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + (e1 + 1 if e1 < elementsCountAround1 - 1 else 0)
                        nodeIdentifiers = [bni1, bni2, bni3, bni4, bni1 + elementsCountAround1, bni2 + elementsCountAround1,
                                           bni3 + elementsCountAround2, bni4 + elementsCountAround2]
                        element = mesh.createElement(elementIdentifier, elementtemplate)
                        element.setNodesByIdentifier(eft, nodeIdentifiers)
                        elementIdentifier = elementIdentifier + 1

                    elif e1 == int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5):
                        bni1 = startIdx + e3 * (elementsCountAround1) + e1
                        bni2 = startIdx + e3 * (elementsCountAround1) + (e1 + 1 if e1 < elementsCountAround1 - 1 else 0)
                        bni3 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + e1
                        bni4 = bni2 + 1
                        nodeIdentifiers = [bni1, bni2, bni3, bni4, bni1 + elementsCountAround1,
                                           bni2 + elementsCountAround1,
                                           bni3 + elementsCountAround2, bni4 + elementsCountAround1]
                        eft1 = eftfactory.createEftBasic()
                        setEftScaleFactorIds(eft1, [1], [])
                        scalefactors = [-1.0]
                        remapEftNodeValueLabel(eft1, [2, 6], Node.VALUE_LABEL_D_DS1,
                                               [(Node.VALUE_LABEL_D_DS1, []), (Node.VALUE_LABEL_D_DS2, [])])
                        remapEftNodeValueLabel(eft1, [2, 6], Node.VALUE_LABEL_D_DS2,
                                               [(Node.VALUE_LABEL_D_DS1, []), (Node.VALUE_LABEL_D_DS2, [])])
                        remapEftNodeValueLabel(eft1, [4, 8], Node.VALUE_LABEL_D_DS1, [(Node.VALUE_LABEL_D_DS2, [1])])
                        remapEftNodeValueLabel(eft1, [4, 8], Node.VALUE_LABEL_D_DS2, [(Node.VALUE_LABEL_D_DS1, [])])
                        elementtemplateX.defineField(coordinates, -1, eft1)
                        elementtemplate1 = elementtemplateX
                        element = mesh.createElement(elementIdentifier, elementtemplate1)
                        element.setNodesByIdentifier(eft1, nodeIdentifiers)
                        # print('check 1 -', elementIdentifier, nodeIdentifiers)
                        elementIdentifier = elementIdentifier + 1

                    elif e1 > int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5) and \
                            e1 < int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5 + elementsCountAroundTC + 1):
                        pass

                    elif e1 == int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5 + 3):
                        # pass
                        # Need to remap derivatives
                        bni1 = startIdx + e3 * (elementsCountAround1) + e1 + 4 + elementsCountAroundTC
                        bni2 = startIdx + e3 * (elementsCountAround1) + (e1 + 4 + elementsCountAroundTC + 1)
                        bni3 = bni1 - 1
                        bni4 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + (e1 - 2)
                        nodeIdentifiers = [bni1, bni2, bni3, bni4, bni1 + elementsCountAround1,
                                           bni2 + elementsCountAround1,
                                           bni3 + elementsCountAround1, bni4 + elementsCountAround2]
                        eft1 = eftfactory.createEftBasic()
                        setEftScaleFactorIds(eft1, [1], [])
                        scalefactors = [-1.0]
                        remapEftNodeValueLabel(eft1, [1, 5], Node.VALUE_LABEL_D_DS1,
                                               [(Node.VALUE_LABEL_D_DS1, []), (Node.VALUE_LABEL_D_DS2, [1])])
                        remapEftNodeValueLabel(eft1, [1, 5], Node.VALUE_LABEL_D_DS2,
                                               [(Node.VALUE_LABEL_D_DS1, [1]), (Node.VALUE_LABEL_D_DS2, [])])
                        remapEftNodeValueLabel(eft1, [3, 7], Node.VALUE_LABEL_D_DS1, [(Node.VALUE_LABEL_D_DS2, [])])
                        remapEftNodeValueLabel(eft1, [3, 7], Node.VALUE_LABEL_D_DS2, [(Node.VALUE_LABEL_D_DS1, [1])])
                        elementtemplateX.defineField(coordinates, -1, eft1)
                        elementtemplate1 = elementtemplateX
                        element = mesh.createElement(elementIdentifier, elementtemplate1)
                        # print('check -', elementIdentifier, nodeIdentifiers)
                        element.setNodesByIdentifier(eft1, nodeIdentifiers)
                        elementIdentifier = elementIdentifier + 1

                    else:
                        bni1 = startIdx + e3 * (elementsCountAround1) + e1 + 4 + elementsCountAroundTC
                        bni2 = startIdx + e3 * (elementsCountAround1) + ((e1 + 4 + elementsCountAroundTC + 1) if e1 < elementsCountAround1 - 7 else 0)
                        bni3 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + e1 - 3
                        bni4 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + (
                            e1 - 2 if e1 < elementsCountAround1 - 7 else 0)
                        nodeIdentifiers = [bni1, bni2, bni3, bni4,
                                           bni1 + elementsCountAround1, bni2 + elementsCountAround1,
                                           bni3 + elementsCountAround2, bni4 + elementsCountAround2]
                        # print('e2 = 1: elementIdentifier = ', elementIdentifier, nodeIdentifiers)
                        element = mesh.createElement(elementIdentifier, elementtemplate)
                        element.setNodesByIdentifier(eft, nodeIdentifiers)
                        elementIdentifier = elementIdentifier + 1

            if e2 == 2:
                countTCNode = 0
                ostiumTCIdx = list(range(int(elementsCountAroundTC * 0.5) + 1, 0, -1)) + \
                              list(range(elementsCountAroundOstium, elementsCountAroundOstium - (int(elementsCountAroundTC * 0.5)), -1))
                for e1 in range(elementsCountAround1 + 4 + int(elementsCountAroundTC * 0.5)):
                    if e1 < int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5):
                        bni1 = startIdx + e3 * (elementsCountAround1) + e1
                        bni2 = startIdx + e3 * (elementsCountAround1) + (e1 + 1 if e1 < elementsCountAround1 - 1 else 0)
                        bni3 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + e1
                        bni4 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + (e1 + 1 if e1 < elementsCountAround1 - 1 else 0)
                        nodeIdentifiers = [bni1, bni2, bni3, bni4, bni1 + elementsCountAround1, bni2 + elementsCountAround1,
                                           bni3 + elementsCountAround2, bni4 + elementsCountAround2]
                        element = mesh.createElement(elementIdentifier, elementtemplate)
                        element.setNodesByIdentifier(eft, nodeIdentifiers)
                        # print(elementIdentifier, e1)
                        elementIdentifier = elementIdentifier + 1

                    elif e1 == int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5):
                        # remap derivatives
                        bni1 = startIdx + e3 * (elementsCountAround1) + e1
                        bni2 = startIdx + e3 * (elementsCountAround1) + e1 - 2 * len(xMat[e2 - 1][0]) + 2
                        bni3 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + e1
                        bni4 = bni2 + 1
                        nodeIdentifiers = [bni1, bni2, bni3, bni4, bni1 + elementsCountAround1,
                                           bni2 + len(xMat[e2 - 1][e3]),
                                           bni3 + elementsCountAround2, bni4 + len(xMat[e2 - 1][e3])]
                        eft1 = eftfactory.createEftBasic()
                        setEftScaleFactorIds(eft1, [1], [])
                        scalefactors = [-1.0]
                        remapEftNodeValueLabel(eft1, [2, 6], Node.VALUE_LABEL_D_DS1, [(Node.VALUE_LABEL_D_DS2, [1])])
                        remapEftNodeValueLabel(eft1, [2, 6], Node.VALUE_LABEL_D_DS2, [(Node.VALUE_LABEL_D_DS1, [])])
                        remapEftNodeValueLabel(eft1, [4, 8], Node.VALUE_LABEL_D_DS1, [(Node.VALUE_LABEL_D_DS2, [1])])
                        remapEftNodeValueLabel(eft1, [4, 8], Node.VALUE_LABEL_D_DS2, [(Node.VALUE_LABEL_D_DS1, [])])
                        elementtemplateX.defineField(coordinates, -1, eft1)
                        elementtemplate1 = elementtemplateX
                        element = mesh.createElement(elementIdentifier, elementtemplate1)
                        element.setNodesByIdentifier(eft1, nodeIdentifiers)
                        # print('here, e = ', elementIdentifier, nodeIdentifiers)
                        elementIdentifier = elementIdentifier + 1

                    elif e1 == int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5 + 1): # Right PROBLEM!
                        # pass
                        # remap derivatives
                        bni1 = startIdx + e3 * (elementsCountAround1) + e1 - 2 * len(xMat[e2 - 1][0]) + 2
                        bni2 = bni1 + 1
                        bni3 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + e1 - 1
                        bni4 = 2
                        nodeIdentifiers = [bni1, bni2, bni3, bni4, bni1 + len(xMat[e2 - 1][e3]),
                                           bni2 + len(xMat[e2 - 1][e3]),
                                           bni3 + elementsCountAround2, bni4 + elementsCountAroundOstium]
                        eft1 = eftfactory.createEftBasic()
                        setEftScaleFactorIds(eft1, [1], [])
                        scalefactors = [-1.0]
                        # remapEftNodeValueLabel(eft1, [3, 7], Node.VALUE_LABEL_D_DS1, [(Node.VALUE_LABEL_D_DS2, [ ])])
                        remapEftNodeValueLabel(eft1, [3, 7], Node.VALUE_LABEL_D_DS2, [(Node.VALUE_LABEL_D_DS1, [1])])
                        remapEftNodeValueLabel(eft1, [4, 8], Node.VALUE_LABEL_D_DS1, [(Node.VALUE_LABEL_D_DS2, [1])])
                        remapEftNodeValueLabel(eft1, [4, 8], Node.VALUE_LABEL_D_DS2, [(Node.VALUE_LABEL_D_DS1, [])])
                        elementtemplateX.defineField(coordinates, -1, eft1)
                        elementtemplate1 = elementtemplateX
                        element = mesh.createElement(elementIdentifier, elementtemplate1)
                        # print('e = ', elementIdentifier, nodeIdentifiers)
                        element.setNodesByIdentifier(eft1, nodeIdentifiers)
                        elementIdentifier = elementIdentifier + 1

                    elif e1 > int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5 + 1) and \
                         e1 < int(elementsCountAroundTC * 2 + elementsCountAroundHaustrum * 1.5 + 3): # TC3
                        bni1 = startIdx + e3 * (elementsCountAround1) + e1 - 2 * len(xMat[e2 - 1][0]) + 2
                        bni2 = bni1 + 1
                        bni3 = ostiumTCIdx[countTCNode]
                        bni4 = ostiumTCIdx[countTCNode + 1]
                        countTCNode += 1
                        nodeIdentifiers = [bni1, bni2, bni3, bni4, bni1 + len(xMat[e2 - 1][e3]),
                                           bni2 + len(xMat[e2 - 1][e3]),
                                           bni3 + elementsCountAroundOstium, bni4 + elementsCountAroundOstium]

                        eft1 = eftfactory.createEftBasic()
                        setEftScaleFactorIds(eft1, [1], [])
                        scalefactors = [-1.0]

                        remapEftNodeValueLabel(eft1, [3, 7], Node.VALUE_LABEL_D_DS1, [(Node.VALUE_LABEL_D_DS1, [1])])
                        remapEftNodeValueLabel(eft1, [4, 8], Node.VALUE_LABEL_D_DS1, [(Node.VALUE_LABEL_D_DS1, [1])])

                        if e1 == int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5 + 2): # Left
                            remapEftNodeValueLabel(eft1, [3, 7], Node.VALUE_LABEL_D_DS2, [(Node.VALUE_LABEL_D_DS1, [ ])])
                            remapEftNodeValueLabel(eft1, [4, 8], Node.VALUE_LABEL_D_DS2, [(Node.VALUE_LABEL_D_DS2, [1])])
                        elif e1 == int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5 + 3):  # Right
                            remapEftNodeValueLabel(eft1, [3, 7], Node.VALUE_LABEL_D_DS2, [(Node.VALUE_LABEL_D_DS2, [1])])
                            remapEftNodeValueLabel(eft1, [4, 8], Node.VALUE_LABEL_D_DS2, [(Node.VALUE_LABEL_D_DS1, [1])])

                        elementtemplateX.defineField(coordinates, -1, eft1)
                        elementtemplate1 = elementtemplateX
                        element = mesh.createElement(elementIdentifier, elementtemplate1)
                        element.setNodesByIdentifier(eft1, nodeIdentifiers)
                        elementIdentifier = elementIdentifier + 1

                    elif e1 == int(elementsCountAroundTC * 2 + elementsCountAroundHaustrum * 1.5 + 3): # Left PROBLEM
                        # pass
                        # remap derivatives
                        bni1 = startIdx + e3 * (elementsCountAround1) + e1 - 2 * len(xMat[e2 - 1][0]) + 2
                        bni2 = bni1 + 1
                        bni3 = elementsCountAroundOstium
                        bni4 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + e1 - 3

                        nodeIdentifiers = [bni1, bni2, bni3, bni4, bni1 + len(xMat[e2 - 1][e3]),
                                           bni2 + len(xMat[e2 - 1][e3]),
                                           bni3 + elementsCountAroundOstium, bni4 + elementsCountAround2 ]
                        eft1 = eftfactory.createEftBasic()
                        setEftScaleFactorIds(eft1, [1], [])
                        scalefactors = [-1.0]
                        remapEftNodeValueLabel(eft1, [3, 7], Node.VALUE_LABEL_D_DS1, [(Node.VALUE_LABEL_D_DS2, [])])
                        remapEftNodeValueLabel(eft1, [3, 7], Node.VALUE_LABEL_D_DS2, [(Node.VALUE_LABEL_D_DS1, [1])])
                        # remapEftNodeValueLabel(eft1, [4, 8], Node.VALUE_LABEL_D_DS1, [(Node.VALUE_LABEL_D_DS2, [1])])
                        # remapEftNodeValueLabel(eft1, [4, 8], Node.VALUE_LABEL_D_DS2, [(Node.VALUE_LABEL_D_DS1, [])])
                        elementtemplateX.defineField(coordinates, -1, eft1)
                        elementtemplate1 = elementtemplateX
                        element = mesh.createElement(elementIdentifier, elementtemplate1)
                        element.setNodesByIdentifier(eft1, nodeIdentifiers)
                        print('e = ', elementIdentifier, nodeIdentifiers)
                        elementIdentifier = elementIdentifier + 1

                    elif e1 == int(elementsCountAroundTC * 2 + elementsCountAroundHaustrum * 1.5 + 4):
                        # remap
                        # pass
                        bni1 = startIdx - len(xMat[e2][0]) * 2 + elementsCountAroundTC + 3
                        bni2 = startIdx + e3 * (elementsCountAround1) + (e1 - elementsCountAroundTC - 2)
                        bni3 = startIdx - len(xMat[e2][0]) * 2 + elementsCountAroundTC + 2
                        bni4 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + (
                            e1 - 2 - elementsCountAroundTC)

                        nodeIdentifiers = [bni1, bni2, bni3, bni4,
                                           bni1 + len(xMat[e2 - 1][0]), bni2 + elementsCountAround1,
                                           bni3 + len(xMat[e2 - 1][0]), bni4 + elementsCountAround2]
                        #print('e2 = 2: elementIdentifier = ', elementIdentifier, nodeIdentifiers)

                        eft1 = eftfactory.createEftBasic()
                        setEftScaleFactorIds(eft1, [1], [])
                        scalefactors = [-1.0]
                        remapEftNodeValueLabel(eft1, [1, 5], Node.VALUE_LABEL_D_DS1, [(Node.VALUE_LABEL_D_DS2, [])])
                        remapEftNodeValueLabel(eft1, [1, 5], Node.VALUE_LABEL_D_DS2, [(Node.VALUE_LABEL_D_DS1, [1])])
                        remapEftNodeValueLabel(eft1, [3, 7], Node.VALUE_LABEL_D_DS1, [(Node.VALUE_LABEL_D_DS2, [])])
                        remapEftNodeValueLabel(eft1, [3, 7], Node.VALUE_LABEL_D_DS2, [(Node.VALUE_LABEL_D_DS1, [1])])
                        elementtemplateX.defineField(coordinates, -1, eft1)
                        elementtemplate1 = elementtemplateX
                        element = mesh.createElement(elementIdentifier, elementtemplate1)
                        element.setNodesByIdentifier(eft1, nodeIdentifiers)
                        # print('check here, e = ', elementIdentifier, nodeIdentifiers)
                        elementIdentifier = elementIdentifier + 1

                    else:
                        bni1 = startIdx + e3 * (elementsCountAround1) + e1 - 3 - elementsCountAroundTC
                        bni2 = startIdx + e3 * (elementsCountAround1) + (e1 - elementsCountAroundTC - 2 if e1 < elementsCountAround1 + 3 + int(elementsCountAroundTC * 0.5) else 0)
                        bni3 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + e1 - 3 - elementsCountAroundTC
                        bni4 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + (
                            e1 - 2 - elementsCountAroundTC if e1 < elementsCountAround1 + 3 + int(elementsCountAroundTC * 0.5) else 0)
                        nodeIdentifiers = [bni1, bni2, bni3, bni4, bni1 + elementsCountAround1,
                                           bni2 + elementsCountAround1,
                                           bni3 + elementsCountAround2, bni4 + elementsCountAround2]
                        # print('e2 = 2: elementIdentifier = ', elementIdentifier, nodeIdentifiers)
                        element = mesh.createElement(elementIdentifier, elementtemplate)
                        element.setNodesByIdentifier(eft, nodeIdentifiers)
                        element.setScaleFactors(eft1, scalefactors) if scalefactors else None
                        elementIdentifier = elementIdentifier + 1

            # if e2 == 3:
            #     for e1 in range(elementsCountAround1):
            #         if e1 != int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5):
            #             bni1 = startIdx + e3 * (elementsCountAround1) + e1
            #             bni2 = startIdx + e3 * (elementsCountAround1) + (e1 + 1 if e1 < elementsCountAround1 - 1 else 0)
            #             if e1 < int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5):
            #                 bni3 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + e1
            #                 bni4 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + (e1 + 1)
            #             else:
            #                 bni3 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + e1
            #                 bni4 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + (e1 + 1 if e1 < elementsCountAround1 - 1 else 0)
            #
            #             nodeIdentifiers = [bni1, bni2, bni3, bni4,
            #                                bni1 + elementsCountAround1, bni2 + elementsCountAround1,
            #                                bni3 + elementsCountAround2, bni4 + elementsCountAround2]
            #             element = mesh.createElement(elementIdentifier, elementtemplate)
            #             element.setNodesByIdentifier(eft, nodeIdentifiers)
            #             elementIdentifier = elementIdentifier + 1
            #         else:
            #             bni1 = startIdx + e3 * (elementsCountAround1) + e1
            #             bni2 = int(elementsCountAroundTC * 0.5 + 1)
            #             bni3 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + e1
            #             bni4 = bni2 + 1
            #             nodeIdentifiers = [bni1, bni2, bni3, bni4,
            #                                bni1 + elementsCountAround1, bni2 + elementsCountAroundOstium,
            #                                bni3 + elementsCountAround2, bni4 + elementsCountAroundOstium]
            #             eft1 = eftfactory.createEftBasic()
            #             setEftScaleFactorIds(eft1, [1], [])
            #             scalefactors = [-1.0]
            #             remapEftNodeValueLabel(eft1, [2, 6], Node.VALUE_LABEL_D_DS1, [(Node.VALUE_LABEL_D_DS2, [1])])
            #             remapEftNodeValueLabel(eft1, [2, 6], Node.VALUE_LABEL_D_DS2, [(Node.VALUE_LABEL_D_DS1, [])])
            #             remapEftNodeValueLabel(eft1, [4, 8], Node.VALUE_LABEL_D_DS1, [(Node.VALUE_LABEL_D_DS2, [1])])
            #             remapEftNodeValueLabel(eft1, [4, 8], Node.VALUE_LABEL_D_DS2, [(Node.VALUE_LABEL_D_DS1, [])])
            #             elementtemplateX.defineField(coordinates, -1, eft1)
            #             elementtemplate1 = elementtemplateX
            #             element = mesh.createElement(elementIdentifier, elementtemplate1)
            #             element.setNodesByIdentifier(eft1, nodeIdentifiers)
            #             elementIdentifier = elementIdentifier + 1
            #
            #             # On the third section
            #             bni1 = elementsCountAroundOstium
            #             bni2 = startIdx + e3 * (elementsCountAround1) + e1 + 1
            #             bni3 = bni1 - 1
            #             bni4 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + e1 + 1
            #             nodeIdentifiers = [bni1, bni2, bni3, bni4,
            #                                bni1 + elementsCountAroundOstium, bni2 + elementsCountAround1,
            #                                bni3 + elementsCountAroundOstium, bni4 + elementsCountAround2]
            #             eft1 = eftfactory.createEftBasic()
            #             setEftScaleFactorIds(eft1, [1], [])
            #             scalefactors = [-1.0]
            #             remapEftNodeValueLabel(eft1, [1, 5], Node.VALUE_LABEL_D_DS1, [(Node.VALUE_LABEL_D_DS2, [ ])])
            #             remapEftNodeValueLabel(eft1, [1, 5], Node.VALUE_LABEL_D_DS2, [(Node.VALUE_LABEL_D_DS1, [1])])
            #             remapEftNodeValueLabel(eft1, [3, 7], Node.VALUE_LABEL_D_DS1, [(Node.VALUE_LABEL_D_DS2, [ ])])
            #             remapEftNodeValueLabel(eft1, [3, 7], Node.VALUE_LABEL_D_DS2, [(Node.VALUE_LABEL_D_DS1, [1])])
            #             elementtemplateX.defineField(coordinates, -1, eft1)
            #             elementtemplate1 = elementtemplateX
            #             element = mesh.createElement(elementIdentifier, elementtemplate1)
            #             element.setNodesByIdentifier(eft1, nodeIdentifiers)
            #             elementIdentifier = elementIdentifier + 1


            # Middle rows connecting to ostium
            if e2 > 2 and e2 < len(xMat) - 3:
                for e1 in range(elementsCountAround1):
                    if e1 != int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5):
                        bni1 = startIdx + e3 * (elementsCountAround1) + e1
                        bni2 = startIdx + e3 * (elementsCountAround1) + (e1 + 1 if e1 < elementsCountAround1 - 1 else 0)
                        if e1 < int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5):
                            bni3 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + e1
                            bni4 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + (e1 + 1)
                        else:
                            bni3 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + e1
                            bni4 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + (e1 + 1 if e1 < elementsCountAround1 - 1 else 0)

                        nodeIdentifiers = [bni1, bni2, bni3, bni4,
                                           bni1 + elementsCountAround1, bni2 + elementsCountAround1,
                                           bni3 + elementsCountAround2, bni4 + elementsCountAround2]
                        element = mesh.createElement(elementIdentifier, elementtemplate)
                        element.setNodesByIdentifier(eft, nodeIdentifiers)
                        elementIdentifier = elementIdentifier + 1

            # Penultimate row connected to 6 point junction
            if e2 == 6:
                # Need to make regular ones
                for e1 in range(elementsCountAround1):
                    if e1 != int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5):
                        bni1 = startIdx + e3 * (elementsCountAround1) + e1
                        bni2 = startIdx + e3 * (elementsCountAround1) + (e1 + 1 if e1 < elementsCountAround1 - 1 else 0)
                        if e1 < int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5):
                            bni3 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + e1
                            bni4 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + (e1 + 1)
                        else:
                            bni3 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + e1 - 1
                            bni4 = startIdx + len(xMat[e2][0]) * len(xMat[e2]) + e3 * elementsCountAround1 + (e1 if e1 < elementsCountAround1 - 1 else 0)

                        nodeIdentifiers = [bni1, bni2, bni3, bni4, bni1 + elementsCountAround1, bni2 + elementsCountAround1,
                                           bni3 + elementsCountAround2, bni4 + elementsCountAround2]

                        if e1 == int((elementsCountAroundTC + elementsCountAroundHaustrum) * 1.5 - 1):
                            eft1 = eftfactory.createEftBasic()
                            setEftScaleFactorIds(eft1, [1], [])
                            scalefactors = [-1.0]
                            remapEftNodeValueLabel(eft1, [4, 8], Node.VALUE_LABEL_D_DS1, [(Node.VALUE_LABEL_D_DS2, [1])])
                            remapEftNodeValueLabel(eft1, [4, 8], Node.VALUE_LABEL_D_DS2, [(Node.VALUE_LABEL_D_DS1, [ ])])
                            elementtemplateX.defineField(coordinates, -1, eft1)
                            elementtemplate1 = elementtemplateX

                        else:
                            elementtemplate1 = elementtemplate
                            eft1 = eft
                            scalefactors = None

                        element = mesh.createElement(elementIdentifier, elementtemplate1)
                        element.setNodesByIdentifier(eft1, nodeIdentifiers)
                        elementIdentifier = elementIdentifier + 1

    fm.endChange()

    return nodeIdentifier, elementIdentifier, allAnnotationGroups

def getOuterTrackSurfaceFromInner(xInner, d1Inner, d2DV, wallThickness):
    """

    :param x:
    :param d1:
    :param d2DV:
    :param wallThickness:
    :return:
    """

    xOuter = []
    for n in range(len(xInner)):
        d3Unit = vector.normalise(vector.crossproduct3(vector.normalise(d1Inner[n]), d2DV))
        xOuter.append([xInner[n][i] + d3Unit[i] * wallThickness for i in range(3)])

    return xOuter

def getSymmetricalPointsInHaustrum(x):
    """

    :param x:
    :return:
    """
    xOppositeOrder = []

    for n in range(len(x)):
        xRot = matrix.rotateAboutZAxis(x[n], -math.pi / 180 * 15)
        xReflect = [xRot[1], xRot[0], xRot[2]]
        xRotBack = matrix.rotateAboutZAxis(xReflect, math.pi / 180 * 15)
        xOppositeOrder.append(xRotBack)

    return xOppositeOrder

def getSecondHalfNodesAndDerivatives(xFirstHalf, d1FirstHalf, d2FirstHalf, elementsCountAroundTC, d1ArrangeTCRow):
    """

    :param xFirstHalf:
    :param d1FirstHalf:
    :param d2FirstHalf:
    :return:
    """
    xSecondHalf = []
    d1Mirror = []
    d1SecondHalf = []
    d2SecondHalf = []

    xOppositeOrder = getSymmetricalPointsInHaustrum(xFirstHalf)
    d2OppositeOrder = getSymmetricalPointsInHaustrum(d2FirstHalf)

    # Re-order nodes
    for n in range(len(xOppositeOrder)):
        xSecondHalf.append(xOppositeOrder[len(xOppositeOrder) - 1 - n])
        d2SecondHalf.append(d2OppositeOrder[len(d2OppositeOrder) - 1 - n])

    # Calculate d1
    d1Around = []
    xAround = []
    for n1 in range(len(xSecondHalf) - 1): # - int(elementsCountAroundTC * 0.5)):
        xAround.append(xSecondHalf[n1])
        v1 = xSecondHalf[n1]
        v2 = xSecondHalf[n1 + 1]
        d1 = d2 = [v2[c] - v1[c] for c in range(3)]
        arcLengthAround = interp.computeCubicHermiteArcLength(v1, d1, v2, d2, True)
        ds1 = [c * arcLengthAround for c in vector.normalise(d1)]
        d1Around.append(ds1)

    # Append edge of tc to do smoothing
    xAround.append(xSecondHalf[n1 + 1])
    d1Around.append(d1ArrangeTCRow[0])
    d1SmoothedAround = interp.smoothCubicHermiteDerivativesLine(xAround, d1Around, fixEndDerivative=True)
    # Scale magnitude of d1 to d1 of haustrum element next to it
    d1SmoothedAround[-2] = vector.setMagnitude(d1SmoothedAround[-2], vector.magnitude(d1SmoothedAround[-3]))
    # Append rest of tc
    for nTC in range(1, int(elementsCountAroundTC * 0.5)):
        d1SmoothedAround.append(d1ArrangeTCRow[nTC])

    return xSecondHalf, d1SmoothedAround, d2SecondHalf

def getCurvatureAlong(xAlong, d2Along, d3Along):
    """

    :param xAlong:
    :param d2Along:
    :param d3Along:
    :return:
    """
    curvatureAlong = []
    for n2 in range(len(xAlong)):
        if n2 == 0:
            curvature = interp.getCubicHermiteCurvature(xAlong[n2], d2Along[n2], xAlong[n2 + 1], d2Along[n2 + 1],
                                                        vector.normalise(d3Along[n2]), 0.0)
        elif n2 == len(xAlong) - 1:
            curvature = interp.getCubicHermiteCurvature(xAlong[n2 - 1], d2Along[n2 - 1], xAlong[n2], d2Along[n2],
                                                        vector.normalise(d3Along[n2]), 1.0)
        else:
            curvature = 0.5 * (
                    interp.getCubicHermiteCurvature(xAlong[n2 - 1], d2Along[n2 - 1], xAlong[n2], d2Along[n2],
                                                    vector.normalise(d3Along[n2]), 1.0) +
                    interp.getCubicHermiteCurvature(xAlong[n2], d2Along[n2], xAlong[n2 + 1], d2Along[n2 + 1],
                                                    vector.normalise(d3Along[n2]), 0.0))
        curvatureAlong.append(curvature)

    return curvatureAlong

def getD3(d1, d2):
    """

    :param d1:
    :param d2:
    :return:
    """
    d3 = vector.normalise(vector.crossproduct3(vector.normalise(d1), vector.normalise(d2)))

    return d3

def findNodeIdFromMatIdx(n1, n2, n3, nodesCountOstium, xMat):
    """

    :param n1:
    :param n2:
    :param n3:
    :param nodesOstium:
    :param xMat:
    :return:
    """

    idx = nodesCountOstium + n1 + 1 + n3*len(xMat[n2][0])

    for c2 in range(n2):
        for c3 in range(len(xMat[c2])):
            for c1 in range(len(xMat[c2][c3])):
                idx += 1

    return idx

