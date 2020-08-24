"""
Generates a 3-D esophagus mesh along the central line,
with variable numbers of elements around, along and through
wall, with variable radius and thickness along.
"""

import copy
import math
from scaffoldmaker.annotation.annotationgroup import AnnotationGroup
from scaffoldmaker.annotation.esophagus_terms import get_esophagus_term
from scaffoldmaker.meshtypes.meshtype_1d_path1 import MeshType_1d_path1, extractPathParametersFromRegion
from scaffoldmaker.meshtypes.scaffold_base import Scaffold_base
from scaffoldmaker.scaffoldpackage import ScaffoldPackage
from scaffoldmaker.utils import interpolation as interp
from scaffoldmaker.utils import tubemesh
from scaffoldmaker.utils import vector
from scaffoldmaker.utils.zinc_utils import exnodeStringFromNodeValues
from opencmiss.zinc.node import Node

class MeshType_3d_esophagus1(Scaffold_base):
    '''
    Generates a 3-D esophagus mesh with variable numbers
    of elements around, along the central line, and through wall.
    The esophagus is created by a function that generates
    an elliptical tube segment and uses tubemesh to map the segment
    along a central line profile.
    '''

    centralPathDefaultScaffoldPackages = {
        'Human 1' : ScaffoldPackage(MeshType_1d_path1, {
            'scaffoldSettings' : {
                'Coordinate dimensions' : 3,
                'Length' : 1.0,
                'Number of elements' : 3
                },
            'meshEdits' : exnodeStringFromNodeValues(
                [ Node.VALUE_LABEL_VALUE, Node.VALUE_LABEL_D_DS1, Node.VALUE_LABEL_D_DS2, Node.VALUE_LABEL_D2_DS1DS2  ], [
                [ [ -5.0, 250.0, 0.0 ], [  8.2, -51.6, 0.0 ], [ 1.0, 0.0, 0.0 ], [ 0.0, 0.0, 0.5 ] ],
                [ [  1.1, 192.3, 0.0 ], [  1.8, -88.3, 0.0 ], [ 1.0, 0.0, 0.0 ], [ 0.0, 0.0, 0.5 ] ],
                [ [  5.8,  86.5, 0.0 ], [ 14.0, -69.6, 0.0 ], [ 1.0, 0.0, 0.0 ], [ 0.0, 0.0, 0.5 ] ],
                [ [ 28.6,  -0.1, 0.0 ], [ 29.1, -47.3, 0.0 ], [ 1.0, 0.0, 0.0 ], [ 0.0, 0.0, 0.5 ] ] ] )
            } )
        }

    @staticmethod
    def getName():
        return '3D Esophagus 1'

    @staticmethod
    def getParameterSetNames():
        return [
            'Default',
            'Human 1']

    @classmethod
    def getDefaultOptions(cls, parameterSetName='Default'):
        centralPathOption = cls.centralPathDefaultScaffoldPackages['Human 1']
        options = {
            'Central path': copy.deepcopy(centralPathOption),
            'Number of elements around': 8,
            'Number of elements along': 10,
            'Number of elements through wall': 1,
            'Cervical esophagus length': 50.0,
            'Thoracic esophagus length': 180.0,
            'Abdominal esophagus length': 20.0,
            'Upper esophageal sphincter diameter': 20.0, # 15mm
            'Esophagus lumen lateral width': 20.0, # up to 30mm
            'Esophagus lumen anterior-posterior width': 20.0, # up to 20mm
            'Wall thickness': 3.0, # 5.0mm when contracted
            'Use cross derivatives': False,
            'Use linear through wall': True,
            'Refine': False,
            'Refine number of elements around': 1,
            'Refine number of elements along': 1,
            'Refine number of elements through wall': 1
            }
        return options

    @staticmethod
    def getOrderedOptionNames():
        return [
            'Central path',
            'Number of elements around',
            'Number of elements along',
            'Number of elements through wall',
            'Cervical esophagus length',
            'Thoracic esophagus length',
            'Abdominal esophagus length',
            'Upper esophageal sphincter diameter',
            'Esophagus lumen lateral width',
            'Esophagus lumen anterior-posterior width',
            'Wall thickness',
            'Use cross derivatives',
            'Use linear through wall',
            'Refine',
            'Refine number of elements around',
            'Refine number of elements along',
            'Refine number of elements through wall' ]

    @classmethod
    def getOptionValidScaffoldTypes(cls, optionName):
        if optionName == 'Central path':
            return [ MeshType_1d_path1 ]
        return []

    @classmethod
    def getOptionScaffoldTypeParameterSetNames(cls, optionName, scaffoldType):
        if optionName == 'Central path':
            return list(cls.centralPathDefaultScaffoldPackages.keys())
        assert scaffoldType in cls.getOptionValidScaffoldTypes(optionName), \
            cls.__name__ + '.getOptionScaffoldTypeParameterSetNames.  ' + \
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
                'Invalid parameter set ' + str(parameterSetName) + ' for scaffold ' + str(scaffoldType.getName()) + \
                ' in option ' + str(optionName) + ' of scaffold ' + cls.getName()
        if optionName == 'Central path':
            if not parameterSetName:
                parameterSetName = list(cls.centralPathDefaultScaffoldPackages.keys())[0]
            return copy.deepcopy(cls.centralPathDefaultScaffoldPackages[parameterSetName])
        assert False, cls.__name__ + '.getOptionScaffoldPackage:  Option ' + optionName + ' is not a scaffold'

    @classmethod
    def checkOptions(cls, options):
        if not options['Central path'].getScaffoldType() in cls.getOptionValidScaffoldTypes('Central path'):
            options['Central path'] = cls.getOptionScaffoldPackage('Central path', MeshType_1d_path1)
        for key in [
            'Number of elements around',
            'Number of elements along',
            'Number of elements through wall',
            'Refine number of elements around',
            'Refine number of elements along',
            'Refine number of elements through wall']:
            if options[key] < 1:
                options[key] = 1
        for key in [
            'Cervical esophagus length',
            'Thoracic esophagus length',
            'Abdominal esophagus length',
            'Upper esophageal sphincter diameter',
            'Esophagus lumen lateral width',
            'Esophagus lumen anterior-posterior width',
            'Wall thickness']:
            if options[key] < 0.0:
                options[key] = 0.0

    @classmethod
    def generateBaseMesh(cls, region, options):
        """
        Generate the base tricubic Hermite mesh. See also generateMesh().
        :param region: Zinc region to define model in. Must be empty.
        :param options: Dict containing options. See getDefaultOptions().
        :return: annotationGroups
        """
        centralPath = options['Central path']
        elementsCountAround = options['Number of elements around']
        elementsCountAlong = options['Number of elements along']
        elementsCountThroughWall = options['Number of elements through wall']
        cervicalLength = options['Cervical esophagus length']
        thoracicLength = options['Thoracic esophagus length']
        abdominalLength = options['Abdominal esophagus length']
        upperSphincterRadius = options['Upper esophageal sphincter diameter'] * 0.5
        majorRadius = options['Esophagus lumen lateral width'] * 0.5
        minorRadius = options['Esophagus lumen anterior-posterior width'] * 0.5
        wallThickness = options['Wall thickness']
        useCrossDerivatives = options['Use cross derivatives']
        useCubicHermiteThroughWall = not(options['Use linear through wall'])

        firstNodeIdentifier = 1
        firstElementIdentifier = 1

        # Central path
        tmpRegion = region.createRegion()
        centralPath.generate(tmpRegion)
        cx, cd1, cd2, cd12 = extractPathParametersFromRegion(tmpRegion)
        # for i in range(len(cx)):
        #     print(i, '[', cx[i], ',', cd1[i], ',', cd2[i],',', cd12[i], '],')
        del tmpRegion

        # find arclength of esophagus
        length = 0.0
        elementsCountIn = len(cx) - 1
        sd1 = interp.smoothCubicHermiteDerivativesLine(cx, cd1, fixAllDirections = True,
                                                       magnitudeScalingMode = interp.DerivativeScalingMode.HARMONIC_MEAN)
        for e in range(elementsCountIn):
            arcLength = interp.getCubicHermiteArcLength(cx[e], sd1[e], cx[e + 1], sd1[e + 1])
            # print(e+1, arcLength)
            length += arcLength
        elementAlongLength = length / elementsCountAlong
        # print('Length = ', length)

        # Sample central path
        sx, sd1, se, sxi, ssf = interp.sampleCubicHermiteCurves(cx, cd1, elementsCountAlong)
        sd2, sd12 = interp.interpolateSampleCubicHermite(cd2, cd12, se, sxi, ssf)

        # Generate variation of radius & tc width along length
        lengthList = [0.0, cervicalLength, cervicalLength + thoracicLength, length]
        minorRadiusList = [upperSphincterRadius, minorRadius, minorRadius, minorRadius]
        minorRadiusElementList = interp.sampleParameterAlongLine(lengthList, minorRadiusList, elementsCountAlong)[0]

        majorRadiusList = [upperSphincterRadius, majorRadius, majorRadius, majorRadius]
        majorRadiusElementList = interp.sampleParameterAlongLine(lengthList, majorRadiusList, elementsCountAlong)[0]

        # Create annotation groups for esophagus sections
        elementsAlongCervical = round(cervicalLength / elementAlongLength)
        elementsAlongThoracic = round(thoracicLength / elementAlongLength)
        elementsAlongAbdominal = elementsCountAlong - elementsAlongCervical - elementsAlongThoracic
        elementsCountAlongGroups = [elementsAlongCervical, elementsAlongThoracic, elementsAlongAbdominal]

        esophagusGroup = AnnotationGroup(region, get_esophagus_term("esophagus"))
        cervicalGroup = AnnotationGroup(region, get_esophagus_term("cervical part of esophagus"))
        thoracicGroup = AnnotationGroup(region, get_esophagus_term("thoracic part of esophagus"))
        abdominalGroup = AnnotationGroup(region, get_esophagus_term("abdominal part of esophagus"))

        annotationGroupAlong = [[esophagusGroup, cervicalGroup],
                                [esophagusGroup, thoracicGroup],
                                [esophagusGroup, abdominalGroup]]

        annotationGroupsAlong = []
        for i in range(len(elementsCountAlongGroups)):
            elementsCount = elementsCountAlongGroups[i]
            for n in range(elementsCount):
                annotationGroupsAlong.append(annotationGroupAlong[i])

        annotationGroupsAround = []
        for i in range(elementsCountAround):
            annotationGroupsAround.append([ ])

        annotationGroupsThroughWall = []
        for i in range(elementsCountThroughWall):
            annotationGroupsThroughWall.append([ ])

        xToSample = []
        d1ToSample = []
        for n2 in range(elementsCountAlong + 1):
            # Create inner points
            cx = [ 0.0, 0.0, elementAlongLength * n2 ]
            axis1 = [ majorRadiusElementList[n2], 0.0, 0.0 ]
            axis2 = [ 0.0, minorRadiusElementList[n2], 0.0 ]
            xInner, d1Inner = createEllipsePoints(cx, 2 * math.pi, axis1, axis2, elementsCountAround, startRadians=0.0)
            xToSample += xInner
            d1ToSample += d1Inner

        d2ToSample = [[0.0, 0.0, elementAlongLength]] * (elementsCountAround * (elementsCountAlong+1))

        # Sample along length
        xInnerRaw = []
        d2InnerRaw = []
        xToWarp = []
        d1ToWarp = []
        d2ToWarp = []
        flatWidthList = []
        xiList = []

        for n1 in range(elementsCountAround):
            xForSamplingAlong = []
            d2ForSamplingAlong = []
            for n2 in range(elementsCountAlong + 1):
                idx = n2 * elementsCountAround + n1
                xForSamplingAlong.append(xToSample[idx])
                d2ForSamplingAlong.append(d2ToSample[idx])
            xSampled, d2Sampled, se, sxi, _ = interp.sampleCubicHermiteCurves(xForSamplingAlong, d2ForSamplingAlong,
                                                                              elementsCountAlong,
                                                                              arcLengthDerivatives=True)
            xInnerRaw.append(xSampled)
            d2InnerRaw.append(d2Sampled)

        # Re-arrange sample order & calculate dx_ds1 and dx_ds3 from dx_ds2
        for n2 in range(elementsCountAlong + 1):
            xAround = []
            d2Around = []

            for n1 in range(elementsCountAround):
                x = xInnerRaw[n1][n2]
                d2 = d2InnerRaw[n1][n2]
                xAround.append(x)
                d2Around.append(d2)

            d1Around = []
            for n1 in range(elementsCountAround):
                v1 = xAround[n1]
                v2 = xAround[(n1 + 1) % elementsCountAround]
                d1 = d2 = [v2[c] - v1[c] for c in range(3)]
                arcLengthAround = interp.computeCubicHermiteArcLength(v1, d1, v2, d2, True)
                dx_ds1 = [c * arcLengthAround for c in vector.normalise(d1)]
                d1Around.append(dx_ds1)
            d1Smoothed = interp.smoothCubicHermiteDerivativesLoop(xAround, d1Around)

            xToWarp += xAround
            d1ToWarp += d1Smoothed
            d2ToWarp += d2Around

            # Flat width and xi
            flatWidth = 0.0
            xiFace = []
            for n1 in range(elementsCountAround):
                v1 = xAround[n1]
                d1 = d1Smoothed[n1]
                v2 = xAround[(n1 + 1) % elementsCountAround]
                d2 = d1Smoothed[(n1 + 1) % elementsCountAround]
                flatWidth += interp.getCubicHermiteArcLength(v1, d1, v2, d2)
            flatWidthList.append(flatWidth)

            for n1 in range(elementsCountAround + 1):
                xi = 1.0 / elementsCountAround * n1
                xiFace.append(xi)
            xiList.append(xiFace)

        # Project reference point for warping onto central path
        sxRefList, sd1RefList, sd2ProjectedListRef, zRefList = \
            tubemesh.getPlaneProjectionOnCentralPath(xToWarp, elementsCountAround, elementsCountAlong,
                                                     length, sx, sd1, sd2, sd12)

        # Warp points
        segmentAxis = [0.0, 0.0, 1.0]
        closedProximalEnd = False

        innerRadiusAlong = []
        for n2 in range(elementsCountAlong + 1):
            firstNodeAlong = xToWarp[n2 * elementsCountAround]
            midptSegmentAxis = [0.0, 0.0, elementAlongLength * n2]
            radius = vector.magnitude(firstNodeAlong[c] - midptSegmentAxis[c] for c in range(3))
            innerRadiusAlong.append(radius)

        xWarpedList, d1WarpedList, d2WarpedList, d3WarpedUnitList = \
            tubemesh.warpSegmentPoints(xToWarp, d1ToWarp, d2ToWarp, segmentAxis, sxRefList, sd1RefList,
                                       sd2ProjectedListRef, elementsCountAround, elementsCountAlong,
                                       zRefList, innerRadiusAlong, closedProximalEnd)

        # Create coordinates and derivatives
        transitElementList = [0]*elementsCountAround
        xList, d1List, d2List, d3List, curvatureList = tubemesh.getCoordinatesFromInner(xWarpedList, d1WarpedList,
            d2WarpedList, d3WarpedUnitList, [wallThickness]*(elementsCountAlong+1),
            elementsCountAround, elementsCountAlong, elementsCountThroughWall, transitElementList)

        # Create flat and texture coordinates
        xFlat, d1Flat, d2Flat, xTexture, d1Texture, d2Texture = tubemesh.createFlatAndTextureCoordinates(
            xiList, flatWidthList, length, wallThickness, elementsCountAround,
            elementsCountAlong, elementsCountThroughWall, transitElementList)

        # Create nodes and elements
        nextNodeIdentifier, nextElementIdentifier, annotationGroups = tubemesh.createNodesAndElements(
            region, xList, d1List, d2List, d3List, xFlat, d1Flat, d2Flat, xTexture, d1Texture, d2Texture,
            elementsCountAround, elementsCountAlong, elementsCountThroughWall,
            annotationGroupsAround, annotationGroupsAlong, annotationGroupsThroughWall,
            firstNodeIdentifier, firstElementIdentifier, useCubicHermiteThroughWall, useCrossDerivatives,
            closedProximalEnd)

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

def createEllipsePoints(cx, radian, axis1, axis2, elementsCountAround, startRadians = 0.0):
    '''
    Create ellipse points centred at cx, from axis1 around through axis2.
    Assumes axis1 and axis2 are orthogonal.
    Dimension 3 only.
    :param cx: centre
    :param axis1: Vector from cx to inside at zero angle
    :param axis2: Vector from cx to inside at 90 degree angle.
    :param elementsCountAround: Number of elements around.
    :return: lists px, pd1
    '''
    px = []
    pd1 = []
    radiansPerElementAround = radian / elementsCountAround
    radiansAround = startRadians
    for n in range(elementsCountAround):
        cosRadiansAround = math.cos(radiansAround)
        sinRadiansAround = math.sin(radiansAround)
        x = [
            cx[0] + cosRadiansAround * axis1[0] - sinRadiansAround * axis2[0],
            cx[1] + cosRadiansAround * axis1[1] + sinRadiansAround * axis2[1],
            cx[2] + cosRadiansAround * axis1[2] + sinRadiansAround * axis2[2]
        ]
        px.append(x)
        pd1.append([radiansPerElementAround * (-sinRadiansAround * axis1[c] + cosRadiansAround * axis2[c]) for c in range(3)])
        radiansAround += radiansPerElementAround

    return px, pd1