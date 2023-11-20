"""
Generates a hermite x bilinear 3-D vagus network mesh from a 1-D network layout.
"""

import copy

from cmlibs.maths.vectorops import add, sub
from cmlibs.utils.zinc.field import findOrCreateFieldCoordinates, findOrCreateFieldGroup, \
    findOrCreateFieldStoredMeshLocation, findOrCreateFieldStoredString
from cmlibs.utils.zinc.general import ChangeManager
from cmlibs.zinc.element import Element, Elementbasis
from cmlibs.zinc.field import Field
from cmlibs.zinc.node import Node
from scaffoldmaker.annotation.annotationgroup import AnnotationGroup, findOrCreateAnnotationGroupForTerm
from scaffoldmaker.annotation.vagus_terms import get_vagus_term
from scaffoldmaker.meshtypes.meshtype_1d_network_layout1 import MeshType_1d_network_layout1
from scaffoldmaker.meshtypes.scaffold_base import Scaffold_base
from scaffoldmaker.scaffoldpackage import ScaffoldPackage
from scaffoldmaker.utils.networkmesh import NetworkMesh
from scaffoldmaker.utils import interpolation as interp
from scaffoldmaker.utils import vector as vector
from scaffoldmaker.utils.zinc_utils import find_or_create_field_coordinates, \
    exnode_string_from_nodeset_field_parameters



class MeshType_3d_vagus1(Scaffold_base):
    """
    Generates a hermite x bilinear 3-D vagus network mesh from a 1-D network layout.
    """

    parameterSetStructureStrings = {
        'Human Left Trunk 1': ScaffoldPackage(MeshType_1d_network_layout1, {
            'scaffoldSettings': {
                "Structure": "1-2-3-4-5-6-7-8-9-10-11-12-13-14-15-16-17-18-19-20-21-22-23-24-25-26-27-28"
            },
            'meshEdits': exnode_string_from_nodeset_field_parameters(
                [Node.VALUE_LABEL_VALUE, Node.VALUE_LABEL_D_DS1, Node.VALUE_LABEL_D_DS2, Node.VALUE_LABEL_D2_DS1DS2, Node.VALUE_LABEL_D_DS3, Node.VALUE_LABEL_D2_DS1DS3], [
                (1, [[10.900,-70.490,1499.510], [9.150,-0.930,-4.870], [0.346,1.950,0.279], [1.533,-0.365,-0.374], [0.889,-0.408,1.748], [-2.075,1.852,1.176]]), 
                (2, [[22.740,-68.770,1496.060], [11.980,-14.040,2.890], [1.490,1.312,0.193], [0.755,-0.912,0.203], [-0.349,0.107,1.965], [-0.400,-0.823,-0.742]]),# superior jugular foramen
                (3, [[29.560,-73.560,1488.170], [3.880,-1.670,-10.580], [1.880,0.144,0.667], [0.215,-0.586,0.146], [0.036,-1.970,0.324], [0.171,-1.007,-0.752]]), # inferior jugular foramen
                (4, [[33.360,-75.230,1476.570], [3.180,-2.480,-11.680], [1.929,0.110,0.502], [0.055,-0.042,-0.218], [0.004,-1.961,0.417], [-0.019,0.020,0.103]]),
                (5, [[35.880,-78.480,1464.950], [1.290,-2.850,-10.360], [1.990,0.060,0.231], [0.032,-0.056,-0.237], [-0.003,-1.930,0.531], [-0.004,0.008,0.029]]), # c1 transverse
                (6, [[36.190,-80.900,1455.970], [0.080,-2.010,-7.870], [2.000,0.000,0.020], [0.004,-0.037,-0.151], [-0.005,-1.939,0.495], [0.003,-0.005,-0.025]]),
                (7, [[36.090,-82.530,1449.240], [-0.270,-1.470,-5.980], [2.000,-0.019,-0.086], [-0.011,-0.025,-0.142], [0.002,-1.941,0.477], [0.004,-0.012,-0.047]]), # angle of mandible
                (8, [[35.690,-83.830,1444.020], [-0.640,-0.990,-4.750], [1.980,-0.049,-0.257], [-0.015,-0.014,-0.134], [0.004,-1.960,0.408], [-0.002,-0.020,-0.108]]), # hyoid
                (9, [[34.870,-84.550,1439.760], [-1.800,-1.310,-9.660], [1.970,-0.050,-0.360], [-0.011,0.004,-0.093], [-0.001,-1.980,0.269], [-0.004,-0.020,-0.136]]), # carotid
                (10, [[32.150,-86.090,1424.650], [-3.400,-1.160,-16.020], [1.959,-0.030,-0.414], [-0.010,0.006,-0.042], [-0.000,-2.000,0.145], [0.001,-0.006,-0.045]]),
                (11, [[28.020,-86.810,1407.770], [-4.970,-2.060,-21.660], [1.949,-0.040,-0.443], [0.014,-0.002,0.104], [0.002,-1.990,0.189], [0.001,0.021,0.132]]), # laryngeal
                (12, [[22.380,-90.690,1381.470], [-1.830,-6.320,-26.820], [2.000,-0.030,-0.129], [0.002,0.100,0.435], [0.001,-1.950,0.459], [-0.007,0.068,0.283]]),
                (13, [[24.320,-99.350,1354.860], [5.200,-8.350,-20.380], [1.951,0.162,0.431], [-0.006,0.046,0.167], [-0.013,-1.854,0.756], [-0.001,0.018,0.064]]), 
                (14, [[28.340,-107.070,1333.920], [2.520,-5.360,-16.050], [1.980,0.090,0.281], [0.023,-0.078,-0.212], [-0.003,-1.899,0.634], [0.006,-0.049,-0.168]]), # clavicle
                (15, [[29.470,-110.340,1323.140], [0.290,-3.340,-14.700], [2.000,0.009,0.037], [0.011,-0.034,-0.217], [0.001,-1.949,0.443], [0.024,-0.049,-0.248]]), # jugular notch
                (16, [[28.140,-113.190,1304.790], [-1.680,-1.310,-24.890], [1.996,0.052,-0.137], [-0.029,0.122,-0.213], [0.059,-1.997,0.101], [-0.041,0.254,-0.877]]),
                (17, [[22.290,-105.060,1283.860], [-5.250,15.970,-14.400], [1.936,0.276,-0.400], [-0.017,0.107,-0.077], [-0.109,-1.356,-1.464], [-0.027,0.250,-0.703]]), # sternal
                (18, [[15.940,-88.060,1269.800], [-5.290,17.240,-19.070], [1.960,0.270,-0.300], [0.027,-0.095,0.108], [-0.001,-1.481,-1.339], [0.062,-0.254,0.389]]), # esophageal plexus
                (19, [[11.880,-72.040,1245.810], [-2.670,8.480,-26.320], [1.990,0.061,-0.182], [0.019,-0.141,0.099], [0.002,-1.899,-0.612], [-0.000,-0.235,0.862]]),
                (20, [[10.770,-71.120,1219.920], [-1.450,-5.310,-28.210], [2.000,-0.020,-0.099], [0.006,-0.011,0.119], [-0.001,-1.970,0.371], [0.008,0.034,0.752]]), 
                (21, [[9.600,-83.360,1191.320], [0.920,-9.860,-21.090], [2.000,0.051,0.063], [-0.032,-0.036,-0.199], [0.020,-1.811,0.848], [-0.003,-0.009,-0.052]]), 
                (22, [[5.120,-90.590,1164.810], [-5.050,-3.380,-20.740], [1.940,-0.080,-0.459], [-0.004,0.036,0.080], [-0.005,-1.970,0.322], [-0.010,0.037,0.077]]), 
                (23, [[3.090,-99.780,1139.270], [2.940,-11.930,-20.970], [1.990,0.120,0.211], [-0.143,0.074,0.788], [0.000,-1.740,0.990], [0.001,-0.017,-0.102]]), # esophageal hiatus
                (24, [[13.100,-112.050,1117.910], [12.700,-1.230,-18.820], [1.657,0.070,1.114], [-0.234,-0.501,0.359], [-0.002,-2.000,0.129], [0.000,0.095,-1.090]]),
                (25, [[24.520,-105.410,1105.460], [8.810,5.530,-8.220], [1.490,-0.740,1.100], [0.005,-0.394,-0.163], [0.000,-1.662,-1.118], [-0.000,0.280,-0.706]]), 
                (26, [[33.384,-99.699,1096.519], [6.310,6.250,-6.360], [1.630,-0.810,0.820], [0.005,0.611,0.016], [-0.002,-1.426,-1.404], [-0.001,-0.020,0.891]]),  # aortic hiatus
                (27, [[45.610,-93.440,1085.250], [9.730,-4.950,-9.260], [1.469,0.641,1.201], [0.095,0.770,-0.274], [-0.001,-1.760,0.940], [0.003,0.355,1.572]]),
                (28, [[54.870,-102.530,1076.880], [5.660,-10.510,-4.580], [1.789,0.811,0.350], [0.546,-0.430,-1.428], [0.002,-0.797,1.831], [0.004,1.571,0.211]])
                ]),
        }),

        'Human Right Trunk 1': ScaffoldPackage(MeshType_1d_network_layout1, {
            'scaffoldSettings': {
                "Structure": "1-2-3-4-5"
            },
            'meshEdits': exnode_string_from_nodeset_field_parameters(
                [Node.VALUE_LABEL_VALUE, Node.VALUE_LABEL_D_DS1, Node.VALUE_LABEL_D_DS2, Node.VALUE_LABEL_D2_DS1DS2, Node.VALUE_LABEL_D_DS3, Node.VALUE_LABEL_D2_DS1DS3], [
                    (1, [[0.394, -100.872, 1402.818], [-0.035, 12.367, -48.020], [8.730, -0.526, -0.142], [0.613, -0.153, -0.037], [-0.272, -4.224, -1.088], [-0.169, -1.491, -0.564]]),
                    (2, [[0.520, -86.043, 1340.066], [0.501, 16.682, -77.602], [9.142, -0.799, -0.113], [0.212, -0.392, 0.096], [-0.465, -5.159, -1.112], [-0.215, -0.377, 0.515]]),
                    (3, [[1.368, -67.733, 1247.932], [0.235, -3.685, -89.672], [9.061, -1.366, 0.080], [-0.833, -0.231, 0.187], [-0.714, -4.722, 0.192], [-0.167, 0.445, 1.659]]),
                    (4, [[0.361, -91.057, 1165.531], [-2.499, -24.560, -49.102], [7.540, -1.290, 0.261], [-0.809, 1.514, 2.095], [-0.806, -4.269, 2.176], [0.001, 0.896, 0.910]]),
                    (5, [[11.750, -111.874, 1127.887], [7.636, -5.715, -7.930], [5.678, 1.265, 4.556], [-8.397, 13.092, 24.878], [-0.708, -3.530, 1.862], [-0.807, -7.995, 7.596]])
                ]),
            }),
    }

    @staticmethod
    def getName():
        return "3D Vagus 1"

    @staticmethod
    def getParameterSetNames():
        return [
            'Default',
            'Human Left Trunk 1']
            # 'Human Right Trunk 1']

    @classmethod
    def getDefaultOptions(cls, parameterSetName="Default"):
        if 'Human Right Trunk 1' in parameterSetName:
            centralPathOption = cls.parameterSetStructureStrings['Human Right Trunk 1']
        else:
            centralPathOption = cls.parameterSetStructureStrings['Human Left Trunk 1']
        options = {
            "Network layout": copy.deepcopy(centralPathOption)
        }
        return options

    @staticmethod
    def getOrderedOptionNames():
        return [
            "Network layout"
        ]

    @classmethod
    def getOptionValidScaffoldTypes(cls, optionName):
        if optionName == "Network layout":
            return [MeshType_1d_network_layout1]
        return []

    @classmethod
    def getOptionScaffoldTypeParameterSetNames(cls, optionName, scaffoldType):
        assert scaffoldType in cls.getOptionValidScaffoldTypes(optionName), \
            cls.__name__ + ".getOptionScaffoldTypeParameterSetNames.  " + \
            "Invalid option \"" + optionName + "\" scaffold type " + scaffoldType.getName()
        return scaffoldType.getParameterSetNames()  # use the defaults from the network layout scaffold

    @classmethod
    def getOptionScaffoldPackage(cls, optionName, scaffoldType, parameterSetName=None):
        """
        :param parameterSetName:  Name of valid parameter set for option Scaffold, or None for default.
        :return: ScaffoldPackage.
        """
        if parameterSetName:
            assert parameterSetName in cls.getOptionScaffoldTypeParameterSetNames(optionName, scaffoldType), \
                "Invalid parameter set " + str(parameterSetName) + " for scaffold " + str(scaffoldType.getName()) + \
                " in option " + str(optionName) + " of scaffold " + cls.getName()
        if optionName == "Network layout":
            if not parameterSetName:
                parameterSetName = "Default"
            return ScaffoldPackage(scaffoldType, defaultParameterSetName=parameterSetName)
        assert False, cls.__name__ + ".getOptionScaffoldPackage:  Option " + optionName + " is not a scaffold"

    @classmethod
    def checkOptions(cls, options):
        if not options["Network layout"].getScaffoldType() in cls.getOptionValidScaffoldTypes("Network layout"):
            options["Network layout"] = cls.getOptionScaffoldPackage("Network layout")
        dependentChanges = False
        return dependentChanges

    @classmethod
    def generateBaseMesh(cls, region, options):
        """
        Generate the base hermite-bilinear mesh. See also generateMesh().
        :param region: Zinc region to define model in. Must be empty.
        :param options: Dict containing options. See getDefaultOptions().
        :return: list of AnnotationGroup, None
        """

        firstNodeIdentifier = 1
        firstElementIdentifier = 1
        nodeIdentifier = firstNodeIdentifier
        elementIdentifier = firstElementIdentifier

        lengthToDiameterRatio = 312.5 # calculated from total length of nerve/average diameter of nerve
        halfBoxWidth = 1.0

        fieldmodule = region.getFieldmodule()
        coordinates = find_or_create_field_coordinates(fieldmodule)

        networkLayout = options["Network layout"]
        layoutRegion = region.createRegion()
        layoutFieldmodule = layoutRegion.getFieldmodule()
        layoutNodes = layoutFieldmodule.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        layoutMesh = layoutFieldmodule.findMeshByDimension(1)
        networkLayout.generate(layoutRegion)  # ask scaffold to generate to get user-edited parameters
        layoutAnnotationGroups = networkLayout.getAnnotationGroups()
        layoutCoordinates = findOrCreateFieldCoordinates(layoutFieldmodule)
        layoutFieldcache = layoutFieldmodule.createFieldcache()

        networkMesh = networkLayout.getConstructionObject()

        fieldcache = fieldmodule.createFieldcache()

        # Geometric coordinates
        nodes = fieldmodule.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        nodetemplate = nodes.createNodetemplate()
        nodetemplate.defineField(coordinates)
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D_DS1, 1)

        mesh = fieldmodule.findMeshByDimension(3)
        hermiteBilinearBasis = fieldmodule.createElementbasis(3, Elementbasis.FUNCTION_TYPE_LINEAR_LAGRANGE)
        hermiteBilinearBasis.setFunctionType(1, Elementbasis.FUNCTION_TYPE_CUBIC_HERMITE)
        eft = mesh.createElementfieldtemplate(hermiteBilinearBasis)
        elementtemplate = mesh.createElementtemplate()
        elementtemplate.setElementShapeType(Element.SHAPE_TYPE_CUBE)
        elementtemplate.defineField(coordinates, -1, eft)

        # Material coordinates
        vagusCoordinates = findOrCreateFieldCoordinates(fieldmodule, name="vagus coordinates")
        vagusNodetemplate = nodes.createNodetemplate()
        vagusNodetemplate.defineField(vagusCoordinates)
        vagusNodetemplate.setValueNumberOfVersions(vagusCoordinates, -1, Node.VALUE_LABEL_VALUE, 1)
        vagusNodetemplate.setValueNumberOfVersions(vagusCoordinates, -1, Node.VALUE_LABEL_D_DS1, 1)

        eftVagus = mesh.createElementfieldtemplate(hermiteBilinearBasis)
        vagusElementtemplate = mesh.createElementtemplate()
        vagusElementtemplate.setElementShapeType(Element.SHAPE_TYPE_CUBE)
        vagusElementtemplate.defineField(vagusCoordinates, -1, eftVagus)

        # make box annotation groups from network layout annotations
        annotationGroups = []
        layoutBoxMeshGroups = {}  # map from group name
        for layoutAnnotationGroup in layoutAnnotationGroups:
            if layoutAnnotationGroup.getDimension() == 1:
                annotationGroup = AnnotationGroup(region, layoutAnnotationGroup.getTerm())
                annotationGroups.append(annotationGroup)
                layoutBoxMeshGroups[layoutAnnotationGroup.getName()] = \
                    (layoutAnnotationGroup.getMeshGroup(layoutMesh), annotationGroup.getMeshGroup(mesh))

        networkSegments = networkMesh.getNetworkSegments()
        slices = {}  # map from network layout node identifier to list of 4 box node identifiers on slice
        lxAll = []
        ld1All = []
        for networkSegment in networkSegments:
            segmentNodes = networkSegment.getNetworkNodes()
            # segmentVersions = networkSegment.getNodeVersions()
            segmentElementIdentifiers = networkSegment.getElementIdentifiers()
            segmentSlices = []
            segmentNodeCount = len(segmentNodes)
            lastSlice = None
            for n in range(segmentNodeCount):
                segmentNode = segmentNodes[n]
                layoutNodeIdentifier = segmentNode.getNodeIdentifier()
                slice = slices.get(layoutNodeIdentifier)
                if slice:
                    segmentSlices.append(slice)
                    lastSlice = slice
                    continue
                layoutNode = layoutNodes.findNodeByIdentifier(layoutNodeIdentifier)
                layoutFieldcache.setNode(layoutNode)
                # currently only supports node version 1
                _, lx = layoutCoordinates.getNodeParameters(layoutFieldcache, -1, Node.VALUE_LABEL_VALUE, 1, 3)
                _, ld1 = layoutCoordinates.getNodeParameters(layoutFieldcache, -1, Node.VALUE_LABEL_D_DS1, 1, 3)
                _, ld2 = layoutCoordinates.getNodeParameters(layoutFieldcache, -1, Node.VALUE_LABEL_D_DS2, 1, 3)
                _, ld12 = layoutCoordinates.getNodeParameters(layoutFieldcache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, 3)
                _, ld3 = layoutCoordinates.getNodeParameters(layoutFieldcache, -1, Node.VALUE_LABEL_D_DS3, 1, 3)
                _, ld13 = layoutCoordinates.getNodeParameters(layoutFieldcache, -1, Node.VALUE_LABEL_D2_DS1DS3, 1, 3)
                lxAll.append(lx)
                ld1All.append(ld1)

                slice = []
                for n3 in range(2):
                    for n2 in range(2):
                        node = nodes.createNode(nodeIdentifier, nodetemplate)
                        fieldcache.setNode(node)
                        x = lx
                        d1 = ld1
                        if n2 == 0:
                            x = sub(x, ld2)
                            d1 = sub(d1, ld12)
                        else:
                            x = add(x, ld2)
                            d1 = add(d1, ld12)
                        if n3 == 0:
                            x = sub(x, ld3)
                            d1 = sub(d1, ld13)
                        else:
                            x = add(x, ld3)
                            d1 = add(d1, ld13)
                        coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_VALUE, 1, x)
                        coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D_DS1, 1, d1)
                        slice.append(nodeIdentifier)
                        nodeIdentifier += 1
                slices[layoutNodeIdentifier] = slice

                if lastSlice:
                    element = mesh.createElement(elementIdentifier, elementtemplate);
                    nids = [lastSlice[0], slice[0],
                            lastSlice[1], slice[1],
                            lastSlice[2], slice[2],
                            lastSlice[3], slice[3]]
                    element.setNodesByIdentifier(eft, nids)
                    layoutElementIdentifier = segmentElementIdentifiers[n - 1]
                    layoutElement = layoutMesh.findElementByIdentifier(layoutElementIdentifier)
                    for layoutBoxMeshGroup in layoutBoxMeshGroups.values():
                        if layoutBoxMeshGroup[0].containsElement(layoutElement):
                            layoutBoxMeshGroup[1].addElement(element)
                    elementIdentifier += 1

                lastSlice = slice

        # Scale length of each segment so that total length is lengthToDiameterRatio
        allLengthsFromCaudal = []
        for i in range(1, len(lxAll) + 1):
            allLengthsFromCaudal.append(interp.getCubicHermiteCurvesLength(lxAll[:i], ld1All[:i]))

        lxVagusCoordAll = []
        ld1VagusCoordAll = []
        for i in range(len(allLengthsFromCaudal)):
            z = allLengthsFromCaudal[i] * lengthToDiameterRatio / allLengthsFromCaudal[-1]
            lxVagusCoordAll.append([0.0, 0.0, z])

        for i in range(len(lxVagusCoordAll) - 1):
            d1 = sub(lxVagusCoordAll[i + 1], lxVagusCoordAll[i])
            ld1VagusCoordAll.append(d1)
        ld1VagusCoordAll.append(d1)

        # Merge material coordinates
        nodeIdentifier = firstNodeIdentifier
        elementIdentifier = firstElementIdentifier
        slices = {}
        for networkSegment in networkSegments:
            segmentNodes = networkSegment.getNetworkNodes()
            # segmentVersions = networkSegment.getNodeVersions()
            segmentElementIdentifiers = networkSegment.getElementIdentifiers()
            segmentSlices = []
            segmentNodeCount = len(segmentNodes)
            lastSlice = None
            for n in range(segmentNodeCount):
                segmentNode = segmentNodes[n]
                layoutNodeIdentifier = segmentNode.getNodeIdentifier()
                slice = slices.get(layoutNodeIdentifier)
                if slice:
                    segmentSlices.append(slice)
                    lastSlice = slice
                    continue

                slice = []
                for n3 in range(2):
                    for n2 in range(2):
                        x = lxVagusCoordAll[n]
                        d1 = ld1VagusCoordAll[n]
                        if n2 == 0:
                            x = sub(x, [halfBoxWidth, 0.0, 0.0])
                        else:
                            x = add(x, [halfBoxWidth, 0.0, 0.0])
                        if n3 == 0:
                            x = sub(x, [0.0, halfBoxWidth, 0.0])
                        else:
                            x = add(x, [0.0, halfBoxWidth, 0.0])

                        node = nodes.findNodeByIdentifier(nodeIdentifier)
                        node.merge(vagusNodetemplate)
                        fieldcache.setNode(node)
                        vagusCoordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_VALUE, 1, x)
                        vagusCoordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D_DS1, 1, d1)
                        slice.append(nodeIdentifier)
                        nodeIdentifier += 1
                slices[layoutNodeIdentifier] = slice

                if lastSlice:
                    nids = [lastSlice[0], slice[0],
                            lastSlice[1], slice[1],
                            lastSlice[2], slice[2],
                            lastSlice[3], slice[3]]

                    element = mesh.findElementByIdentifier(elementIdentifier)
                    element.merge(vagusElementtemplate)
                    element.setNodesByIdentifier(eftVagus, nids)
                    layoutElementIdentifier = segmentElementIdentifiers[n - 1]
                    layoutElement = layoutMesh.findElementByIdentifier(layoutElementIdentifier)
                    for layoutBoxMeshGroup in layoutBoxMeshGroups.values():
                        if layoutBoxMeshGroup[0].containsElement(layoutElement):
                            layoutBoxMeshGroup[1].addElement(element)
                    elementIdentifier += 1

                lastSlice = slice

        # # Calculate distance between anatomical landmark levels
        # markersIDX = [2, 3, 5, 7, 8, 9, 11, 14, 15, 17, 18, 23, 26]
        # allLengthsLandmarksFromCaudal = []
        # for i in range(len(markersIDX)):
        #     lengthsLandmarksFromCaudal = interp.getCubicHermiteCurvesLength(lxAll[:markersIDX[i]], ld1All[:markersIDX[i]])
        #     allLengthsLandmarksFromCaudal.append(lengthsLandmarksFromCaudal * lengthToDiameterRatio / allLengthsFromCaudal[-1])
        # print(allLengthsLandmarksFromCaudal)

        # Add markers
        markerTermNameVagusCoordinatesMap = {
            "centroid of level of superior border of the jugular foramen on the vagal trunk": [0.0, 0.0, 8.6342],
            "centroid of level of inferior border of the jugular foramen on the vagal trunk": [0.0, 0.0, 16.7227],
            "centroid of level of C1 transverse process on the vagal trunk": [0.0, 0.0, 32.1129],
            "centroid of level of angle of mandible on the vagal trunk": [0.0, 0.0, 42.2450],
            "centroid of level of tubercles of the greater horn of hyoid bone on the vagal trunk": [0.0, 0.0, 45.6122],
            "centroid of level of carotid bifurcation on the vagal trunk": [0.0, 0.0, 48.3581],
            "centroid of level of laryngeal prominence on the vagal trunk": [0.0, 0.0, 68.8431],
            "centroid of level of superior border of clavicle on the vagal trunk": [0.0, 0.0, 117.5627],
            "centroid of level of jugular notch on the vagal trunk": [0.0, 0.0, 124.6407],
            "centroid of level of sternal angle on the vagal trunk": [0.0, 0.0, 151.2352],
            "centroid of 1 cm superior to esophageal plexus on the vagal trunk": [0.0, 0.0, 165.5876],
            "centroid of level of esophageal hiatus on the vagal trunk": [0.0, 0.0, 254.32879],
            "centroid of level of aortic hiatus on the vagal trunk": [0.0, 0.0, 291.3695]}

        for termName, vagusCoordinatesValues in markerTermNameVagusCoordinatesMap.items():
            annotationGroup = findOrCreateAnnotationGroupForTerm(
                annotationGroups, region, get_vagus_term(termName), isMarker=True)
            annotationGroup.createMarkerNode(nodeIdentifier, vagusCoordinates, vagusCoordinatesValues)
            nodeIdentifier += 1

        return annotationGroups, None
