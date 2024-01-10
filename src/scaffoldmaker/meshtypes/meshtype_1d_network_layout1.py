"""
Constructs a 1-D network layout mesh with specifiable structure.
"""
from cmlibs.maths.vectorops import cross, magnitude, mult, normalize, sub
from cmlibs.utils.zinc.field import find_or_create_field_coordinates
from cmlibs.utils.zinc.general import ChangeManager
from cmlibs.utils.zinc.scene import scene_get_selection_group
from cmlibs.zinc.field import Field, FieldGroup
from cmlibs.zinc.node import Node
from scaffoldmaker.meshtypes.scaffold_base import Scaffold_base
from scaffoldmaker.utils.interpolation import smoothCubicHermiteCrossDerivativesLine
from scaffoldmaker.utils.networkmesh import NetworkMesh
from scaffoldmaker.utils.zinc_utils import clearRegion, get_nodeset_field_parameters, \
    get_nodeset_path_field_parameters, make_nodeset_derivatives_orthogonal, \
    set_nodeset_field_parameters, setPathParameters
from enum import Enum
import math


class MeshType_1d_network_layout1(Scaffold_base):
    """
    Defines branching network layout with side dimensions.
    """

    parameterSetStructureStrings = {
        "Default": "1-2",
        "Bifurcation": "1-2.1,2.2-3,2.3-4",
        "Converging bifurcation": "1-3.1,2-3.2,3.3-4",
        "Loop": "1-2-3-4-5-6-7-8-1",
        "Sphere cube": "1.1-2.1,1.2-3.1,1.3-4.1,2.2-5.2,2.3-6.1,3.2-6.2,3.3-7.1,4.2-7.2,4.3-5.1,5.3-8.1,6.3-8.2,7.3-8.3",
        "Left vagus nerve": "1-2-3-4-5-6-7-8-9-10-11-12-13-14-15-16-17-18-19.1-20-21-22-23-24-25-26-27-28-29-30-31-32-33-34.1, 34.2-35-36, 19.2-37-38.1, 38.2-39-40, 38.3-41-42, 34.3-43.1-44, 43.2-45-46",
    }

    @classmethod
    def getName(cls):
        return "1D Network Layout 1"

    @classmethod
    def getParameterSetNames(cls):
        return list(cls.parameterSetStructureStrings.keys())

    @classmethod
    def getDefaultOptions(cls, parameterSetName="Default"):
        options = {}
        options["Base parameter set"] = parameterSetName
        options["Structure"] = cls.parameterSetStructureStrings[parameterSetName]
        options["Define inner coordinates"] = False  # can be overridden by parent scaffold
        return options

    @classmethod
    def getOrderedOptionNames(cls):
        return [
            #  "Base parameter set"  # Hidden.
            #  "Structure"  # Hidden so must edit via interactive function.
            #  "Define inner coordinates"  # Hidden as enabled by parent scaffold.
        ]

    @classmethod
    def checkOptions(cls, options):
        dependentChanges = False
        return dependentChanges

    @classmethod
    def generateBaseMesh(cls, region, options):
        """
        Generate the unrefined mesh.
        :param region: Zinc region to define model in. Must be empty.
        :param options: Dict containing options. See getDefaultOptions().
        :return: [] empty list of AnnotationGroup, NetworkMesh
        """
        parameterSetName = options['Base parameter set']
        structure = options["Structure"]
        defineInnerCoordinates = options["Define inner coordinates"]
        networkMesh = NetworkMesh(structure)
        networkMesh.create1DLayoutMesh(region)

        fieldmodule = region.getFieldmodule()
        coordinates = find_or_create_field_coordinates(fieldmodule).castFiniteElement()
        nodes = fieldmodule.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        fieldcache = fieldmodule.createFieldcache()
        if "Loop" in parameterSetName:
            loopRadius = 0.5
            tubeRadius = 0.1
            d1Mag = loopRadius * 0.25 * math.pi
            for n in range(8):
                angle = 0.25 * math.pi * n
                cosAngle = math.cos(angle)
                sinAngle = math.sin(angle)
                node = nodes.findNodeByIdentifier(n + 1)
                fieldcache.setNode(node)
                x = [loopRadius * cosAngle, loopRadius * sinAngle, 0.0]
                d1 = [-d1Mag * sinAngle, d1Mag * cosAngle, 0.0]
                d2 = [0.0, 0.0, tubeRadius]
                d3 = [tubeRadius * cosAngle, tubeRadius * sinAngle, 0.0]
                d13 = mult(d1, tubeRadius)
                coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_VALUE, 1, x)
                coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D_DS1, 1, d1)
                coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D_DS2, 1, d2)
                coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D2_DS1DS3, 1, d13)
                coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D_DS3, 1, d3)
        elif "Sphere cube" in parameterSetName:
            # edit node parameters
            sphereRadius = 0.5
            tubeRadius = 0.1
            edgeAngle = 2.0 * math.asin(math.sqrt(1.0 / 3.0))
            # get x and d3
            cx = []
            cd3 = []
            for i in range(4):
                angleUp = [0.0, edgeAngle, math.pi - edgeAngle, math.pi][i]
                cosAngleUp = math.cos(angleUp)
                sinAngleUp = math.sin(angleUp)
                z = -sphereRadius * cosAngleUp
                zRadius = sphereRadius * sinAngleUp
                jLimit = 1 if i in [0, 3] else 3
                for j in range(jLimit):
                    angleAround = math.radians(120.0 * ((j - 0.5) if (i == 2) else j))
                    cosAngleAround = math.cos(angleAround)
                    sinAngleAround = math.sin(angleAround)
                    px = [zRadius * cosAngleAround, zRadius * sinAngleAround, z]
                    cx.append(px)
                    cd3.append(mult(normalize(px), tubeRadius))
            # get d1, d2, d13
            cd1 = []
            cd2 = []
            cd13 = []
            for n in range(8):
                cd1.append([])
                cd2.append([])
                cd13.append([])
            edgeArcLength = sphereRadius * edgeAngle
            for networkSegment in networkMesh.getNetworkSegments():
                networkNodes = networkSegment.getNetworkNodes()
                nodeIndexes = [networkNode.getNodeIdentifier() - 1 for networkNode in networkNodes]
                delta = sub(cx[nodeIndexes[1]], cx[nodeIndexes[0]])
                for ln in range(2):
                    d3 = cd3[nodeIndexes[ln]]
                    d2 = mult(normalize(cross(d3, delta)), tubeRadius)
                    d1 = mult(normalize(cross(d2, d3)), edgeArcLength)
                    cd1[nodeIndexes[ln]].append(d1)
                    cd2[nodeIndexes[ln]].append(d2)
                    cd13[nodeIndexes[ln]].append(mult(d1, tubeRadius))
            # fix the one node out of order:
            for d in [cd1[4], cd2[4]]:
                d[0:2] = [d[1], d[0]]
            for n in range(8):
                node = nodes.findNodeByIdentifier(n + 1)
                fieldcache.setNode(node)
                coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_VALUE, 1, cx[n])
                for v in range(3):
                    coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D_DS1, v + 1, cd1[n][v])
                    coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D_DS2, v + 1, cd2[n][v])
                    coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D_DS3, v + 1, cd3[n])
                    coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D2_DS1DS3, v + 1, cd13[n][v])
        elif "Left vagus nerve" in parameterSetName:
            # outerPoints = [[[10.900,-70.490,1499.510], [9.150,-0.930,-4.870], [0.346,1.950,0.279], [1.533,-0.365,-0.374], [0.889,-0.408,1.748], [-2.075,1.852,1.176]],
            #                 [[22.740,-68.770,1496.060], [11.980,-14.040,2.890], [1.490,1.312,0.193], [0.755,-0.912,0.203], [-0.349,0.107,1.965], [-0.400,-0.823,-0.742]],# superior jugular foramen
            #                 [[29.560,-73.560,1488.170], [3.880,-1.670,-10.580], [1.880,0.144,0.667], [0.215,-0.586,0.146], [0.036,-1.970,0.324], [0.171,-1.007,-0.752]], # inferior jugular foramen
            #                 [[33.360,-75.230,1476.570], [3.180,-2.480,-11.680], [1.929,0.110,0.502], [0.055,-0.042,-0.218], [0.004,-1.961,0.417], [-0.019,0.020,0.103]],
            #                 [[35.880,-78.480,1464.950], [1.290,-2.850,-10.360], [1.990,0.060,0.231], [0.032,-0.056,-0.237], [-0.003,-1.930,0.531], [-0.004,0.008,0.029]], # c1 transverse
            #                 [[36.190,-80.900,1455.970], [0.080,-2.010,-7.870], [2.000,0.000,0.020], [0.004,-0.037,-0.151], [-0.005,-1.939,0.495], [0.003,-0.005,-0.025]],
            #                 [[36.090,-82.530,1449.240], [-0.270,-1.470,-5.980], [2.000,-0.019,-0.086], [-0.011,-0.025,-0.142], [0.002,-1.941,0.477], [0.004,-0.012,-0.047]], # angle of mandible
            #                 [[35.690,-83.830,1444.020], [-0.640,-0.990,-4.750], [1.980,-0.049,-0.257], [-0.015,-0.014,-0.134], [0.004,-1.960,0.408], [-0.002,-0.020,-0.108]], # hyoid
            #                 [[34.870,-84.550,1439.760], [-1.800,-1.310,-9.660], [1.970,-0.050,-0.360], [-0.011,0.004,-0.093], [-0.001,-1.980,0.269], [-0.004,-0.020,-0.136]], # carotid
            #                 [[32.150,-86.090,1424.650], [-3.400,-1.160,-16.020], [1.959,-0.030,-0.414], [-0.010,0.006,-0.042], [-0.000,-2.000,0.145], [0.001,-0.006,-0.045]],
            #                 [[28.020,-86.810,1407.770], [-4.970,-2.060,-21.660], [1.949,-0.040,-0.443], [0.014,-0.002,0.104], [0.002,-1.990,0.189], [0.001,0.021,0.132]], # laryngeal
            #                 [[22.380,-90.690,1381.470], [-1.830,-6.320,-26.820], [2.000,-0.030,-0.129], [0.002,0.100,0.435], [0.001,-1.950,0.459], [-0.007,0.068,0.283]],
            #                 [[24.320,-99.350,1354.860], [5.200,-8.350,-20.380], [1.951,0.162,0.431], [-0.006,0.046,0.167], [-0.013,-1.854,0.756], [-0.001,0.018,0.064]],
            #                 [[28.340,-107.070,1333.920], [2.520,-5.360,-16.050], [1.980,0.090,0.281], [0.023,-0.078,-0.212], [-0.003,-1.899,0.634], [0.006,-0.049,-0.168]], # clavicle
            #                 [[29.470,-110.340,1323.140], [0.290,-3.340,-14.700], [2.000,0.009,0.037], [0.011,-0.034,-0.217], [0.001,-1.949,0.443], [0.024,-0.049,-0.248]], # jugular notch
            #                 [[28.140,-113.190,1304.790], [-1.680,-1.310,-24.890], [1.996,0.052,-0.137], [-0.029,0.122,-0.213], [0.059,-1.997,0.101], [-0.041,0.254,-0.877]],
            #                 [[22.290,-105.060,1283.860], [-5.250,15.970,-14.400], [1.936,0.276,-0.400], [-0.017,0.107,-0.077], [-0.109,-1.356,-1.464], [-0.027,0.250,-0.703]], # sternal
            #                 [[15.940,-88.060,1269.800], [-5.290,17.240,-19.070], [1.960,0.270,-0.300], [0.027,-0.095,0.108], [-0.001,-1.481,-1.339], [0.062,-0.254,0.389]], # esophageal plexus
            #                 [[11.880,-72.040,1245.810], [-2.670,8.480,-26.320], [1.990,0.061,-0.182], [0.019,-0.141,0.099], [0.002,-1.899,-0.612], [-0.000,-0.235,0.862]],
            #                 [[10.770,-71.120,1219.920], [-1.450,-5.310,-28.210], [2.000,-0.020,-0.099], [0.006,-0.011,0.119], [-0.001,-1.970,0.371], [0.008,0.034,0.752]],
            #                 [[9.600,-83.360,1191.320], [0.920,-9.860,-21.090], [2.000,0.051,0.063], [-0.032,-0.036,-0.199], [0.020,-1.811,0.848], [-0.003,-0.009,-0.052]],
            #                 [[5.120,-90.590,1164.810], [-5.050,-3.380,-20.740], [1.940,-0.080,-0.459], [-0.004,0.036,0.080], [-0.005,-1.970,0.322], [-0.010,0.037,0.077]],
            #                 [[3.090,-99.780,1139.270], [2.940,-11.930,-20.970], [1.990,0.120,0.211], [-0.143,0.074,0.788], [0.000,-1.740,0.990], [0.001,-0.017,-0.102]], # esophageal hiatus
            #                 [[13.100,-112.050,1117.910], [12.700,-1.230,-18.820], [1.657,0.070,1.114], [-0.234,-0.501,0.359], [-0.002,-2.000,0.129], [0.000,0.095,-1.090]],
            #                 [[24.520,-105.410,1105.460], [8.810,5.530,-8.220], [1.490,-0.740,1.100], [0.005,-0.394,-0.163], [0.000,-1.662,-1.118], [-0.000,0.280,-0.706]],
            #                 [[33.384,-99.699,1096.519], [6.310,6.250,-6.360], [1.630,-0.810,0.820], [0.005,0.611,0.016], [-0.002,-1.426,-1.404], [-0.001,-0.020,0.891]],  # aortic hiatus
            #                 [[45.610,-93.440,1085.250], [9.730,-4.950,-9.260], [1.469,0.641,1.201], [0.095,0.770,-0.274], [-0.001,-1.760,0.940], [0.003,0.355,1.572]],
            #                 [[54.870,-102.530,1076.880], [5.660,-10.510,-4.580], [1.789,0.811,0.350], [0.546,-0.430,-1.428], [0.002,-0.797,1.831], [0.004,1.571,0.211]],
            #                 [[24.059, -86.658, 1274.884], [6.695, 13.319, -8.663], [1.980, -0.050, -0.260], [-0.010, -0.010, -0.130], [0.000, -1.960, 0.410], [-0.000, -0.020, -0.110]],
            #                 [[32.629, -79.240, 1268.122], [13.753, 6.687, -14.053], [1.970, -0.050, -0.360], [-0.010, 0.000, -0.090], [-0.000, -1.980, 0.270], [-0.000, -0.020, -0.140]],
            #                 [[49.145, -77.926, 1247.125], [21.943, -7.294, 0.719], [1.960, -0.030, -0.410], [-0.010, 0.010, -0.040], [-0.000, -2.000, 0.140], [0.000, -0.010, -0.040]],
            #                 [[52.019, -83.325, 1261.285], [-6.753, -1.461, 11.510], [1.950, -0.040, -0.440], [0.010, -0.000, 0.100], [0.000, -1.990, 0.190], [0.000, 0.020, 0.130]],
            #                 [[39.57, -106.36, 1081.58], [6.49, -5.27, -14.46], [1.47, 0.64, 1.20], [0.10, 0.77, -0.27], [-0.00, -1.76, 0.94], [0.00, 0.35, 1.57]],
            #                 [[46.18, -110.28, 1067.88], [6.71, -2.56, -12.90], [1.79, 0.81, 0.35], [0.55, -0.43, -1.43], [0.00, -0.80, 1.83], [0.00, 1.57, 0.21]],
            #                 [[38.81, -120.34, 1072.63], [-4.01, -15.21, -4.54], [1.79, 0.81, 0.35], [0.55, -0.43, -1.43], [0.00, -0.80, 1.83], [0.00, 1.57, 0.21]]
            #                ]
            outerPoints = [[[10.900,-70.490,1499.510], [3.058,1.607,-2.565], [0.350,1.950,0.280], [1.530,-0.360,-0.370], [0.890,-0.410,1.750], [-2.080,1.850,1.180]],
                            [[15.210,-68.890,1497.320], [5.470,1.545,-1.738], [1.490,1.310,0.190], [0.760,-0.910,0.200], [-0.350,0.110,1.970], [-0.400,-0.820,-0.740]],
                            [[21.640,-67.580,1496.360], [7.078,-1.968,-2.119], [1.490,1.310,0.190], [0.760,-0.910,0.200], [-0.350,0.110,1.970], [-0.400,-0.820,-0.740]],
                            [[27.230,-73.040,1493.470], [4.913,-3.320,-5.768], [1.880,0.140,0.670], [0.210,-0.590,0.150], [0.040,-1.970,0.320], [0.170,-1.010,-0.750]],
                            [[30.430,-73.620,1486.260], [3.272,-1.026,-8.446], [1.880,0.140,0.670], [0.210,-0.590,0.150], [0.040,-1.970,0.320], [0.170,-1.010,-0.750]],
                            [[33.620,-75.160,1476.690], [2.810,-2.377,-10.701], [1.930,0.110,0.500], [0.060,-0.040,-0.220], [0.000,-1.960,0.420], [-0.020,0.020,0.100]],
                            [[35.880,-78.480,1464.950], [1.174,-2.874,-10.412], [1.990,0.060,0.230], [0.030,-0.060,-0.240], [-0.000,-1.930,0.530], [-0.000,0.010,0.030]],
                            [[36.190,-80.900,1455.970], [0.077,-2.012,-7.865], [2.000,0.000,0.020], [0.000,-0.040,-0.150], [-0.010,-1.940,0.490], [0.000,-0.010,-0.030]],
                            [[36.090,-82.530,1449.240], [-0.273,-1.468,-5.977], [2.000,-0.020,-0.090], [-0.010,-0.030,-0.140], [0.000,-1.940,0.480], [0.000,-0.010,-0.050]],
                             [[35.690,-83.830,1444.020], [-0.459,-0.978,-4.847], [1.980,-0.050,-0.260], [-0.010,-0.010,-0.130], [0.000,-1.960,0.410], [-0.000,-0.020,-0.110]],
                             [[35.190,-84.520,1439.570], [-1.535,-1.266,-9.722], [1.970,-0.050,-0.360], [-0.010,0.000,-0.090], [-0.000,-1.980,0.270], [-0.000,-0.020,-0.140]],
                             [[32.150,-86.090,1424.650], [-3.898,-1.195,-17.097], [1.960,-0.030,-0.410], [-0.010,0.010,-0.040], [-0.000,-2.000,0.140], [0.000,-0.010,-0.040]],
                             [[27.300,-86.750,1405.430], [-4.991,-2.075,-21.658], [1.950,-0.040,-0.440], [0.010,-0.000,0.100], [0.000,-1.990,0.190], [0.000,0.020,0.130]],
                             [[22.310,-90.520,1381.490], [-1.732,-6.353,-25.914], [2.000,-0.030,-0.130], [0.000,0.100,0.430], [0.000,-1.950,0.460], [-0.010,0.070,0.280]],
                             [[24.420,-99.580,1354.430], [3.271,-8.211,-23.148], [1.950,0.160,0.430], [-0.010,0.050,0.170], [-0.010,-1.850,0.760], [-0.000,0.020,0.060]],
                             [[28.380,-106.780,1335.240], [2.320,-5.265,-15.766], [1.980,0.090,0.280], [0.020,-0.080,-0.210], [-0.000,-1.900,0.630], [0.010,-0.050,-0.170]],
                             [[29.470,-110.340,1323.140], [0.149,-3.408,-15.340], [2.000,0.010,0.040], [0.010,-0.030,-0.220], [0.000,-1.950,0.440], [0.020,-0.050,-0.250]],
                             [[28.210,-113.130,1304.780], [-3.637,2.138,-20.620], [2.000,0.050,-0.140], [-0.030,0.120,-0.210], [0.060,-2.000,0.100], [-0.040,0.250,-0.880]],
                             [[22.080,-105.130,1283.990], [[-6.244,13.100,-18.015],[-0.718,13.905,-13.121]], [[1.940,0.280,-0.400],[1.940,0.280,-0.400]], [[-0.020,0.110,-0.080],[-0.020,0.110,-0.080]], [[-0.110,-1.360,-1.460],[-0.110,-1.360,-1.460]], [[-0.030,0.250,-0.700],[-0.030,0.250,-0.700]]],
                             [[16.200,-88.020,1270.070], [-4.734,14.710,-14.740], [1.960,0.270,-0.300], [0.030,-0.100,0.110], [-0.000,-1.480,-1.340], [0.060,-0.250,0.390]],
                             [[12.590,-75.800,1255.040], [-2.455,9.070,-17.173], [1.960,0.270,-0.300], [0.030,-0.100,0.110], [-0.000,-1.480,-1.340], [0.060,-0.250,0.390]],
                             [[11.390,-70.270,1236.640], [-0.968,2.075,-17.928], [1.960,0.270,-0.300], [0.030,-0.100,0.110], [-0.000,-1.480,-1.340], [0.060,-0.250,0.390]],
                             [[10.670,-71.290,1219.990], [-0.754,-4.029,-18.499], [2.000,-0.020,-0.100], [0.010,-0.010,0.120], [-0.000,-1.970,0.370], [0.010,0.030,0.750]],
                             [[9.920,-78.850,1200.330], [-0.604,-7.415,-17.005], [2.000,0.050,0.060], [-0.030,-0.040,-0.200], [0.020,-1.810,0.850], [-0.000,-0.010,-0.050]],
                             [[9.450,-85.880,1185.970], [-1.682,-5.454,-14.731], [2.000,0.050,0.060], [-0.030,-0.040,-0.200], [0.020,-1.810,0.850], [-0.000,-0.010,-0.050]],
                             [[6.620,-89.700,1171.150], [-3.136,-3.360,-15.171], [1.940,-0.080,-0.460], [-0.000,0.040,0.080], [-0.010,-1.970,0.320], [-0.010,0.040,0.080]],
                             [[3.180,-92.570,1155.680], [-1.953,-4.067,-14.129], [1.940,-0.080,-0.460], [-0.000,0.040,0.080], [-0.010,-1.970,0.320], [-0.010,0.040,0.080]],
                             [[2.540,-97.510,1143.140], [0.861,-6.135,-11.183], [1.990,0.120,0.210], [-0.140,0.070,0.790], [0.000,-1.740,0.990], [0.000,-0.020,-0.100]],
                             [[4.700,-104.460,1133.610], [3.004,-6.082,-9.175], [1.990,0.120,0.210], [-0.140,0.070,0.790], [0.000,-1.740,0.990], [0.000,-0.020,-0.100]],
                             [[8.400,-109.640,1124.940], [5.234,-3.868,-9.301], [1.990,0.120,0.210], [-0.140,0.070,0.790], [0.000,-1.740,0.990], [0.000,-0.020,-0.100]],
                             [[15.040,-111.850,1115.450], [7.442,1.216,-8.984], [1.660,0.070,1.110], [-0.230,-0.500,0.360], [-0.000,-2.000,0.130], [0.000,0.100,-1.090]],
                             [[22.470,-107.440,1107.910], [6.570,4.713,-6.419], [1.490,-0.740,1.100], [0.010,-0.390,-0.160], [0.000,-1.660,-1.120], [-0.000,0.280,-0.710]],
                             [[28.110,-102.670,1102.620], [5.393,3.779,-5.902], [1.490,-0.740,1.100], [0.010,-0.390,-0.160], [0.000,-1.660,-1.120], [-0.000,0.280,-0.710]],
                             [[33.150,-99.910,1096.270], [[4.630,1.720,-6.715],[9.276,20.368,-11.397],[8.794,-0.387,-13.708]], [[1.630,-0.810,0.820],[1.630,-0.810,0.820],[1.630,-0.810,0.820]], [[0.010,0.610,0.020],[0.010,0.610,0.020],[0.010,0.610,0.020]], [[-0.000,-1.430,-1.400],[-0.000,-1.430,-1.400],[-0.000,-1.430,-1.400]], [[-0.000,-0.020,0.890],[-0.000,-0.020,0.890],[-0.000,-0.020,0.890]]],
                             [[45.239,-93.595,1085.478], [7.044,-0.868,-7.462], [2.026,-0.129,1.495], [0.100,0.770,-0.270], [-0.000,-1.760,0.940], [0.000,0.350,1.570]],
                             [[54.360,-102.450,1077.350], [1.669,-10.067,-4.216], [1.790,0.810,0.350], [0.550,-0.430,-1.430], [0.000,-0.800,1.830], [0.000,1.570,0.210]],
                             [[23.330,-88.250,1275.900], [3.463,14.329,-4.449], [1.980,-0.050,-0.260], [-0.010,-0.010,-0.130], [0.000,-1.960,0.410], [-0.000,-0.020,-0.110]],
                             [[32.287,-79.285,1268.902], [[11.678,3.730,-9.609],[5.310,-2.835,-11.763],[7.040,5.114,-10.458]], [[1.970,-0.050,-0.360],[1.970,-0.050,-0.360],[1.970,-0.050,-0.360]], [[-0.010,0.000,-0.090],[-0.010,0.000,-0.090],[-0.010,0.000,-0.090]], [[-0.000,-1.980,0.270],[-0.000,-1.980,0.270],[-0.000,-1.980,0.270]], [[-0.000,-0.020,-0.140],[-0.000,-0.020,-0.140],[-0.000,-0.020,-0.140]]],
                             [[39.200,-80.300,1257.430], [9.220,1.186,-9.464], [1.960,-0.030,-0.410], [-0.010,0.010,-0.040], [-0.000,-2.000,0.140], [0.000,-0.010,-0.040]],
                             [[49.150,-77.930,1247.120], [11.111,4.117,-9.268], [1.960,-0.030,-0.410], [-0.010,0.010,-0.040], [-0.000,-2.000,0.140], [0.000,-0.010,-0.040]],
                             [[42.582,-77.775,1260.806], [5.396,-1.511,-1.137], [1.950,-0.040,-0.440], [0.010,-0.000,0.100], [0.000,-1.990,0.190], [0.000,0.020,0.130]],
                             [[52.020,-83.330,1261.290], [8.778,-8.775,5.301], [1.950,-0.040,-0.440], [0.010,-0.000,0.100], [0.000,-1.990,0.190], [0.000,0.020,0.130]],
                           [[39.570, -106.360, 1081.580], [[1.676, -6.540, -9.622], [-4.285, -3.707, -2.507]],
                            [[1.470, 0.640, 1.200], [1.470, 0.640, 1.200]],
                            [[0.100, 0.770, -0.270], [0.100, 0.770, -0.270]],
                            [[-0.000, -1.760, 0.940], [-0.000, -1.760, 0.940]],
                            [[0.000, 0.350, 1.570], [0.000, 0.350, 1.570]]],
                           [[45.981, -110.526, 1067.815], [8.047, 0.871, -12.742], [1.790, 0.810, 0.350],
                            [0.550, -0.430, -1.430], [0.000, -0.800, 1.830], [0.000, 1.570, 0.210]],
                           [[39.021, -111.664, 1076.034], [1.344, -5.047, -5.083], [1.790, 0.810, 0.350],
                            [0.550, -0.430, -1.430], [0.000, -0.800, 1.830], [0.000, 1.570, 0.210]],
                           [[38.728, -119.318, 1072.496], [-4.649, -7.186, 1.582], [1.790, 0.810, 0.350],
                            [0.550, -0.430, -1.430], [0.000, -0.800, 1.830], [0.000, 1.570, 0.210]]]



            for n in range(len(outerPoints)):
                node = nodes.findNodeByIdentifier(n + 1)
                fieldcache.setNode(node)
                coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_VALUE, 1, outerPoints[n][0])
                if n == 34 - 1 or n == 19 - 1 or n == 38 - 1 or n == 43-1:
                    for v in range(len(outerPoints[n][1])):
                        coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D_DS1, v + 1,
                                                      outerPoints[n][1][v])
                        coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D_DS2, v + 1,
                                                      outerPoints[n][2][v])
                        coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D2_DS1DS2, v + 1,
                                                      outerPoints[n][3][v])
                        coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D_DS3, v + 1,
                                                      outerPoints[n][4][v])
                        coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D2_DS1DS3, v + 1,
                                                      outerPoints[n][5][v])
                else:
                    coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D_DS1, 1, outerPoints[n][1])
                    coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D_DS2, 1, outerPoints[n][2])
                    coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, outerPoints[n][3])
                    coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D_DS3, 1, outerPoints[n][4])
                    coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D2_DS1DS3, 1, outerPoints[n][5])

        if defineInnerCoordinates:
            cls._defineInnerCoordinates(region, coordinates, options, networkMesh)

        return [], networkMesh

    @classmethod
    def _defineInnerCoordinates(cls, region, coordinates, options, networkMesh):
        """
        Copy coordinates to inner coordinates via in-memory model file.
        Assign using the interactive function.
        :param region: Region to define field in.
        :param coordinates: Standard/outer coordinate field.
        :param options: Options used to generate scaffold.
        :param networkMesh: Network mesh object used to generate scaffold.
        """
        assert options["Define inner coordinates"]
        coordinates.setName("inner coordinates")  # temporarily rename
        sir = region.createStreaminformationRegion()
        srm = sir.createStreamresourceMemory()
        region.write(sir)
        result, buffer = srm.getBuffer()
        coordinates.setName("coordinates")  # restore name before reading inner coordinates back in
        sir = region.createStreaminformationRegion()
        sir.createStreamresourceMemoryBuffer(buffer)
        region.read(sir)
        functionOptions = {
            "To field": {"coordinates": False, "inner coordinates": True},
            "From field": {"coordinates": True, "inner coordinates": False},
            "Mode": {"Scale": True, "Offset": False},
            "D2 value": 0.5,
            "D3 value": 0.5}
        cls.assignCoordinates(region, options, networkMesh, functionOptions, editGroupName=None)

    @classmethod
    def editStructure(cls, region, options, networkMesh, functionOptions, editGroupName):
        """
        Edit structure safely, to prevent accidental changes.
        Copies functionOptions["Structure"] to options["Structure"] and regenerates with
        default geometric coordinates.
        :param region: Region containing model to clear and re-generate.
        :param options: The scaffold settings used to create the original model, pre-edits.
        :param networkMesh: The NetworkMesh construction object model was created from. Contents replaced.
        :param functionOptions: functionOptions["Structure"] contains new structure string.
        :param editGroupName: Name of Zinc group to put edited nodes in. Cleared.
        :return: boolean indicating if settings changed, boolean indicating if node parameters changed.
        """
        fieldmodule = region.getFieldmodule()
        with ChangeManager(fieldmodule):
            clearRegion(region)
            structure = options["Structure"] = functionOptions["Structure"]
            networkMesh.build(structure)
            networkMesh.create1DLayoutMesh(region)
            coordinates = find_or_create_field_coordinates(fieldmodule).castFiniteElement()
            coordinates.setManaged(True)  # since cleared by clearRegion
            defineInnerCoordinates = options["Define inner coordinates"]
            if defineInnerCoordinates:
                cls._defineInnerCoordinates(region, coordinates, options, networkMesh)

        return True, False  # settings changed, nodes not changed (since reset to original coordinates)

    class AssignCoordinatesMode(Enum):
        SCALE = 1,  # scale side derivative magnitude by value
        OFFSET = 2   # offset side derivative by absolute distance

    @classmethod
    def assignCoordinates(cls, region, options, networkMesh, functionOptions, editGroupName):
        """
        Assign coordinates or inner coordinates by scaling or offsetting from either original
        values or values from other field.
        If elements are selected, applied only to nodes used by the element and versions used in the enclosing segment.
        :param region: Region containing model to change parameters of.
        :param options: The scaffold settings used to create the original model, pre-edits.
        :param networkMesh: The NetworkMesh construction object model was created from. Unused.
        :param functionOptions: Which side directions to make normal.
        :param editGroupName: Name of Zinc group to put edited nodes in.
        :return: boolean indicating if settings changed, boolean indicating if node parameters changed.
        """
        fieldmodule = region.getFieldmodule()
        coordinates = fieldmodule.findFieldByName("coordinates").castFiniteElement()
        innerCoordinates = fieldmodule.findFieldByName("inner coordinates").castFiniteElement()
        if not innerCoordinates.isValid():
            if functionOptions["To field"]["inner coordinates"] or \
                    functionOptions["From field"]["inner coordinates"]:
                print("Assign coordinates:  No inner coordinates defined")
                return None, None
        mode = None
        if functionOptions["Mode"]["Scale"]:
            mode = cls.AssignCoordinatesMode.SCALE
        elif functionOptions["Mode"]["Offset"]:
            mode = cls.AssignCoordinatesMode.OFFSET
        else:
            print("Assign coordinates:  Invalid mode")
            return None, None
        toCoordinates = coordinates if functionOptions["To field"]["coordinates"] else innerCoordinates
        fromCoordinates = coordinates if functionOptions["From field"]["coordinates"] else innerCoordinates
        d2Value = functionOptions["D2 value"]
        d3Value = functionOptions["D3 value"]
        nodeset = fieldmodule.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        selectionGroup = scene_get_selection_group(region.getScene(), inherit_root_region=region.getRoot())
        selectionMeshGroup = None
        mesh1d = fieldmodule.findMeshByDimension(1)
        nodes = fieldmodule.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        if selectionGroup:
            selectionMeshGroup = selectionGroup.getMeshGroup(mesh1d)
            if not selectionMeshGroup.isValid():
                print("Assign coordinates:  Selection contains no elements. Clear it to assign globally.")
                return None, None
        valueLabels = [
            Node.VALUE_LABEL_VALUE, Node.VALUE_LABEL_D_DS1,
            Node.VALUE_LABEL_D_DS2, Node.VALUE_LABEL_D2_DS1DS2,
            Node.VALUE_LABEL_D_DS3, Node.VALUE_LABEL_D2_DS1DS3]

        with ChangeManager(fieldmodule):
            # get all node parameters (from selection if any)
            editNodeset = nodeset
            originalNodeParameters = None
            if selectionGroup:
                # make group of only nodes being edited
                tmpGroup = fieldmodule.createFieldGroup()
                tmpGroup.setSubelementHandlingMode(FieldGroup.SUBELEMENT_HANDLING_MODE_FULL)
                tmpMeshGroup = tmpGroup.createMeshGroup(mesh1d)
                tmpMeshGroup.addElementsConditional(selectionGroup)
                editNodeset = tmpGroup.getNodesetGroup(nodes)
                _, originalNodeParameters = get_nodeset_field_parameters(editNodeset, toCoordinates, valueLabels)
                del tmpMeshGroup
                del tmpGroup
            _, nodeParameters = get_nodeset_field_parameters(editNodeset, fromCoordinates, valueLabels)

            modifyVersions = None  # default is to modify all versions
            if selectionGroup:
                nodeIdentifierIndexes = {}
                modifyVersions = []
                for n in range(len(nodeParameters)):
                    nodeIdentifierIndexes[nodeParameters[n][0]] = n
                    versionsCount = len(nodeParameters[n][1][1])
                    modifyVersions.append([False] * versionsCount if selectionGroup else [True] * versionsCount)
                networkSegments = networkMesh.getNetworkSegments()
                for networkSegment in networkSegments:
                    nodeIdentifiers = networkSegment.getNodeIdentifiers()
                    nodeVersions = networkSegment.getNodeVersions()
                    elementIdentifiers = networkSegment.getElementIdentifiers()
                    for e in range(len(elementIdentifiers)):
                        elementIdentifier = elementIdentifiers[e]
                        element = selectionMeshGroup.findElementByIdentifier(elementIdentifier)
                        if element.isValid():
                            for n in [e, e + 1]:
                                nodeIndex = nodeIdentifierIndexes.get(nodeIdentifiers[n])
                                # print("Node identifier", nodeIdentifiers[n], "index", nodeIndex, "version", nodeVersions[n])
                                if nodeIndex is not None:
                                    modifyVersions[nodeIndex][nodeVersions[n] - 1] = True

            for n in range(len(nodeParameters)):
                modifyVersion = modifyVersions[n] if modifyVersions else None
                nNodeParameters = nodeParameters[n][1]
                oNodeParameters = originalNodeParameters[n][1] if modifyVersions else None
                versionsCount = len(nNodeParameters[1])
                for v in range(versionsCount):
                    if (not modifyVersions) or modifyVersion[v]:
                        for dd in range(2):
                            scale = d2Value if (dd == 0) else d3Value
                            if mode == cls.AssignCoordinatesMode.OFFSET:
                                mag = magnitude(nNodeParameters[2 + 2 * dd][v])
                                scale = (mag + scale) / mag if (abs(mag) > 0.0) else 1.0
                            for d in [2 + 2 * dd, 3 + 2 * dd]:
                                nNodeParameters[d][v] = mult(nNodeParameters[d][v], scale)
                    else:
                        # copy original derivative versions
                        for d in range(2, 6):
                            nNodeParameters[d][v] = oNodeParameters[d][v]

            set_nodeset_field_parameters(editNodeset, toCoordinates, valueLabels, nodeParameters, editGroupName)
            del editNodeset

        return False, True  # settings not changed, nodes changed

    @classmethod
    def makeSideDerivativesNormal(cls, region, options, networkMesh, functionOptions, editGroupName):
        """
        Make side directions normal to d1 and each other. Works for all versions.
        :param region: Region containing model to change parameters of.
        :param options: The scaffold settings used to create the original model, pre-edits.
        :param networkMesh: The NetworkMesh construction object model was created from. Unused.
        :param functionOptions: Which side directions to make normal.
        :param editGroupName: Name of Zinc group to put edited nodes in.
        :return: boolean indicating if settings changed, boolean indicating if node parameters changed.
        """
        fieldmodule = region.getFieldmodule()
        coordinates = fieldmodule.findFieldByName("coordinates").castFiniteElement()
        nodeset = fieldmodule.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        makeD2Normal = functionOptions['Make D2 normal']
        makeD3Normal = functionOptions['Make D3 normal']
        if not (makeD2Normal or makeD3Normal):
            return False, False
        make_nodeset_derivatives_orthogonal(nodeset, coordinates, makeD2Normal, makeD3Normal, editGroupName)
        return False, True  # settings not changed, nodes changed

    @classmethod
    def smoothSideCrossDerivatives(cls, region, options, networkMesh, functionOptions, editGroupName):
        """
        Smooth side cross derivatives giving rate of change of side directions d2, d3 w.r.t. d1.
        Note: only works for a single path with version 1.
        :param region: Region containing model to change parameters of.
        :param options: The scaffold settings used to create the original model, pre-edits.
        :param networkMesh: The NetworkMesh construction object model was created from.
        Used to determine connected paths for smoothing.
        :param functionOptions: Which side derivatives to smooth.
        :param editGroupName: Name of Zinc group to put edited nodes in.
        :return: boolean indicating if settings changed, boolean indicating if node parameters changed.
        """
        smoothD12 = functionOptions["Smooth D12"]
        smoothD13 = functionOptions["Smooth D13"]
        if not (smoothD12 or smoothD13):
            return False, False
        valueLabels = [Node.VALUE_LABEL_VALUE, Node.VALUE_LABEL_D_DS1]
        if smoothD12:
            valueLabels += [Node.VALUE_LABEL_D_DS2, Node.VALUE_LABEL_D2_DS1DS2]
        if smoothD13:
            valueLabels += [Node.VALUE_LABEL_D_DS3, Node.VALUE_LABEL_D2_DS1DS3]
        fieldmodule = region.getFieldmodule()
        parameters = get_nodeset_path_field_parameters(
            fieldmodule.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES),
            fieldmodule.findFieldByName('coordinates'),
            valueLabels)
        x = parameters[0]
        d1 = parameters[1]
        modifyParameters = []
        modifyValueLabels = []
        if smoothD12:
            d12 = smoothCubicHermiteCrossDerivativesLine(x, d1, parameters[2], parameters[3])
            modifyParameters.append(d12)
            modifyValueLabels.append(Node.VALUE_LABEL_D2_DS1DS2)
        if smoothD13:
            d13 = smoothCubicHermiteCrossDerivativesLine(x, d1, parameters[-2], parameters[-1])
            modifyParameters.append(d13)
            modifyValueLabels.append(Node.VALUE_LABEL_D2_DS1DS3)
        setPathParameters(region, modifyValueLabels, modifyParameters, editGroupName)
        return False, True  # settings not changed, nodes changed

    @classmethod
    def getInteractiveFunctions(cls):
        """
        Supply client with functions for smoothing path parameters.
        """
        return Scaffold_base.getInteractiveFunctions() + [
            ("Edit structure...",
                {"Structure": None},  # None = take value from options
                lambda region, options, networkMesh, functionOptions, editGroupName:
                    cls.editStructure(region, options, networkMesh, functionOptions, editGroupName)),
            ("Assign coordinates...", {
                "To field": {"coordinates": True, "inner coordinates": False},
                "From field": {"coordinates": True, "inner coordinates": False},
                "Mode": {"Scale": True, "Offset": False},
                "D2 value": 1.0,
                "D3 value": 1.0},
                lambda region, options, networkMesh, functionOptions, editGroupName:
                    cls.assignCoordinates(region, options, networkMesh, functionOptions, editGroupName)),
            ("Make side derivatives normal...",
                {"Make D2 normal": True,
                 "Make D3 normal": True},
                lambda region, options, networkMesh, functionOptions, editGroupName:
                    cls.makeSideDerivativesNormal(region, options, networkMesh, functionOptions, editGroupName)),
            ("Smooth side cross derivatives...",
                {"Smooth D12": True,
                 "Smooth D13": True},
                lambda region, options, networkMesh, functionOptions, editGroupName:
                    cls.smoothSideCrossDerivatives(region, options, networkMesh, functionOptions, editGroupName))
        ]
