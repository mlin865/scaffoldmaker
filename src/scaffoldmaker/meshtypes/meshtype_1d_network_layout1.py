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
from scaffoldmaker.utils.networkmesh import NetworkMesh, pathValueLabels
from scaffoldmaker.utils.interpolation import smoothCurveSideCrossDerivatives
from scaffoldmaker.utils.zinc_utils import clearRegion, get_nodeset_field_parameters, \
    get_nodeset_path_ordered_field_parameters, make_nodeset_derivatives_orthogonal, \
    set_nodeset_field_parameters
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
        "Trifurcation": "1-2.1,2.2-3,2.3-4,2.4-5",
        "Trifurcation cross": "1-3.1,2-3.2,3.2-4,3.1-5",
        "colonHuman3": "1-2-3-4-5-6-7-8-9-10-11-12-13-14-15-16-17-18-19-20-21-22-23-24-25-26-27-28-29-30-31-32-33-34-35-36-37-38-39-40-41-42-43-44-45-46-47-48-49",
        "exfPath": "1-2-3-4-5-6-7-8-9-10-11-12-13-14-15-16-17-18-19-20-21-22-23-24-25-26-27-28-29-30-31-32-33-34-35-36-37-38-39-40-41-42-43-44-45-46-47-48-49"
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
            elementsCount = nodes.getSize()
            elementAngle = 2.0 * math.pi / elementsCount
            d1Mag = loopRadius * elementAngle
            for n in range(elementsCount):
                angle = elementAngle * n
                cosAngle = math.cos(angle)
                sinAngle = math.sin(angle)
                node = nodes.findNodeByIdentifier(n + 1)
                fieldcache.setNode(node)
                x = [loopRadius * cosAngle, loopRadius * sinAngle, 0.0]
                d1 = [-d1Mag * sinAngle, d1Mag * cosAngle, 0.0]
                d2 = [0.0, 0.0, tubeRadius]
                d3 = [tubeRadius * cosAngle, tubeRadius * sinAngle, 0.0]
                d13 = mult(d1, elementAngle * tubeRadius / d1Mag)
                coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_VALUE, 1, x)
                coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D_DS1, 1, d1)
                coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D_DS2, 1, d2)
                coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D_DS3, 1, d3)
                coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D2_DS1DS3, 1, d13)
        elif "colonHuman3" in parameterSetName:
            points = [[[-87.210,-111.060,890.540], [-4.750,0.410,12.390], [23.270,-3.130,7.880], [2.460,-0.390,-2.950], [3.090,24.460,0.450], [1.830,0.460,-4.310]],
                           [[-89.990,-110.570,902.650], [-2.050,0.530,12.720], [24.710,-3.280,4.130], [0.070,0.140,-2.810], [3.420,25.000,-0.640], [0.430,0.100,-3.970]],
                           [[-91.250,-110.010,915.920], [-0.550,0.530,13.390], [23.610,-2.820,1.080], [-1.460,0.550,-1.920], [2.850,23.610,-0.910], [-1.420,0.540,-2.130]],
                           [[-91.080,-109.520,929.390], [0.130,0.650,13.470], [21.830,-2.100,-0.100], [-0.530,0.220,-1.060], [2.080,21.810,-1.180], [-0.530,0.210,-1.170]],
                           [[-91.000,-108.720,942.850], [0.830,0.670,13.370], [22.560,-2.350,-1.280], [-0.880,0.270,-1.850], [2.290,22.560,-1.420], [-0.920,0.270,-2.030]],
                           [[-89.430,-108.180,956.080], [2.810,0.320,13.110], [20.050,-1.510,-4.270], [-1.960,0.620,-1.350], [1.380,20.440,-0.860], [-2.000,0.620,-1.490]],
                           [[-85.390,-108.090,968.920], [3.100,0.440,13.080], [18.600,-0.990,-4.380], [-0.760,0.320,0.660], [0.820,19.040,-0.910], [-0.730,0.310,0.710]],
                           [[-83.240,-107.300,982.140], [2.050,0.850,13.230], [18.550,-0.800,-2.820], [-0.240,0.090,0.570], [0.620,18.710,-1.440], [-0.210,0.080,0.630]],
                           [[-81.290,-106.400,995.370], [2.320,1.340,13.290], [18.150,-0.790,-3.100], [0.140,0.240,-0.110], [0.470,18.290,-2.130], [0.050,0.310,-0.570]],
                           [[-78.600,-104.620,1008.650], [2.140,-1.500,13.270], [18.840,-0.250,-3.070], [-0.910,1.850,-0.220], [0.840,18.750,3.430], [-0.950,1.980,-0.150]],
                           [[-77.170,-109.180,1020.820], [4.070,-9.070,9.680], [16.310,3.440,-3.630], [-2.150,4.060,0.800], [-0.010,12.030,12.600], [-1.970,3.890,1.430]],
                           [[-71.190,-121.030,1025.580], [7.480,-11.420,0.490], [14.200,9.260,-1.140], [-1.270,2.690,3.170], [0.000,1.980,17.640], [-1.270,2.720,3.230]],
                           [[-63.350,-130.560,1022.180], [7.990,-9.440,-3.400], [13.310,9.970,3.600], [-0.810,0.700,2.420], [0.000,-5.470,16.790], [-0.910,0.850,2.430]],
                           [[-55.270,-139.840,1018.800], [8.880,-8.590,-3.550], [12.320,10.870,4.490], [-1.070,0.870,0.810], [0.000,-6.180,16.540], [-1.090,0.870,0.810]],
                           [[-45.660,-147.660,1015.100], [9.900,-7.390,-3.360], [10.810,11.990,5.470], [-1.630,1.380,0.030], [-0.010,-6.690,16.290], [-1.620,1.360,0.020]],
                           [[-35.520,-154.600,1012.080], [11.080,-6.080,-1.980], [8.540,14.060,4.580], [-1.990,1.150,0.250], [-0.010,-5.000,17.000], [-1.970,1.130,0.240]],
                           [[-23.710,-159.680,1011.200], [11.970,-4.320,-1.790], [6.200,14.650,6.070], [-1.740,-0.440,2.510], [0.010,-6.170,16.490], [-1.790,-0.440,2.520]],
                           [[-11.720,-163.200,1008.530], [12.260,-2.580,-2.060], [4.480,13.030,10.390], [-2.160,-0.110,1.440], [-0.010,-10.220,14.200], [-2.140,-0.120,1.430]],
                           [[0.670,-164.820,1007.100], [12.710,-0.730,-0.480], [1.180,14.350,9.430], [-2.670,0.760,-0.810], [-0.010,-8.950,15.090], [-2.580,0.750,-0.810]],
                           [[13.556,-164.739,1007.051], [12.750,0.980,0.850], [-1.700,14.800,8.530], [-1.750,0.420,-1.040], [-0.320,-8.140,15.580], [-1.710,0.430,-1.040]],
                           [[26.116,-162.906,1008.217], [12.630,1.810,1.230], [-2.890,15.320,7.020], [-2.260,-0.160,-1.140], [-0.450,-6.810,16.270], [-2.230,-0.140,-1.140]],
                           [[38.730,-161.010,1010.040], [11.760,4.530,2.770], [-6.960,14.450,5.880], [-3.080,-0.420,-3.340], [-0.980,-6.490,16.380], [-3.120,-0.440,-3.350]],
                           [[50.563,-154.087,1013.645], [9.860,7.100,4.160], [-9.105,10.240,0.863], [-1.930,-0.520,-2.090], [-4.770,-2.540,17.360], [-1.970,-0.530,-2.090]],
                           [[58.745,-146.870,1017.469], [9.340,7.750,4.350], [-9.097,10.778,0.486], [-1.820,-1.100,1.290], [-3.670,-4.330,17.260], [-1.800,-1.060,1.300]],
                           [[67.501,-138.309,1022.249], [7.990,8.770,4.670], [-10.568,9.341,0.117], [-2.500,-1.970,-0.340], [-2.610,-6.250,17.940], [-2.590,-2.160,-0.410]],
                           [[74.433,-129.298,1027.145], [5.080,9.970,3.830], [-13.880,7.949,-1.165], [0.030,-2.060,0.330], [-2.126,-4.930,16.625], [-1.530,-1.170,0.490]],
                           [[77.560,-119.250,1030.430], [5.040,10.780,-0.510], [-14.630,6.980,2.780], [0.100,1.230,-1.770], [4.280,1.140,20.240], [0.400,1.970,-2.970]],
                           [[83.860,-109.530,1026.210], [6.930,6.510,-9.450], [-16.870,11.640,-4.350], [-2.810,1.300,-3.770], [7.220,14.780,13.520], [-1.240,0.300,-4.600]],
                           [[89.550,-108.420,1013.560], [3.910,0.860,-13.160], [-20.290,9.170,-5.430], [-1.850,-1.680,0.870], [8.380,20.860,4.280], [-2.140,-1.950,1.170]],
                           [[91.640,-107.830,1000.370], [1.780,0.550,-13.270], [-20.930,7.770,-2.480], [-0.800,-1.120,1.760], [7.590,21.030,2.070], [-0.860,-1.120,1.920]],
                           [[93.100,-107.330,987.040], [1.010,0.300,-13.420], [-22.050,6.680,-1.510], [-0.560,-0.650,1.350], [6.630,22.100,1.090], [-0.580,-0.660,1.490]],
                           [[93.660,-107.240,973.550], [-0.020,1.050,-13.410], [-22.120,6.280,0.520], [0.930,-2.250,1.330], [6.310,22.050,1.910], [0.920,-2.270,1.470]],
                           [[93.060,-105.250,960.320], [-0.770,2.250,-13.200], [-20.310,1.700,1.470], [0.920,-2.340,0.150], [1.920,20.030,3.650], [0.930,-2.360,0.170]],
                           [[92.120,-102.740,947.160], [-0.420,2.820,-13.160], [-20.350,1.100,0.880], [0.740,-0.110,-0.850], [1.250,19.860,4.690], [0.730,-0.090,-0.940]],
                           [[92.230,-99.620,934.040], [0.470,1.780,-13.240], [-18.820,1.460,-0.470], [1.010,0.010,-1.140], [1.390,18.640,2.850], [1.030,0.020,-1.270]],
                           [[93.040,-99.170,920.860], [1.210,-0.740,-13.330], [-18.310,1.150,-1.730], [0.280,-0.610,0.540], [1.230,18.350,-1.000], [0.280,-0.690,-0.020]],
                           [[94.650,-101.120,907.560], [-0.610,-1.620,-13.470], [-18.270,0.060,0.820], [-0.210,-1.550,3.280], [-0.050,18.160,-2.300], [-0.490,-1.710,2.070]],
                           [[91.840,-102.350,894.350], [-3.470,-1.640,-11.950], [-18.620,-2.390,5.740], [0.910,-2.200,3.650], [-3.000,19.300,-1.810], [-0.730,-2.580,3.870]],
                           [[87.880,-104.310,883.750], [-5.210,-2.130,-10.320], [-16.280,-4.940,9.250], [2.730,-2.870,2.500], [-6.690,20.720,-1.110], [0.460,-3.190,4.530]],
                           [[81.450,-106.590,873.900], [-6.990,-2.140,-9.270], [-12.430,-8.970,11.450], [0.330,-3.150,2.690], [-6.303,19.245,1.555], [2.230,-2.670,3.370]],
                           [[73.980,-108.570,865.270], [-8.310,-0.220,-8.520], [-12.268,-8.435,13.125], [-1.280,-1.760,1.510], [-6.633,18.953,4.087], [3.180,-1.460,2.050]],
                           [[65.060,-106.920,857.150], [-8.970,1.810,-7.690], [-14.794,-6.343,11.919], [1.280,0.430,-0.090], [-4.396,19.311,7.084], [2.480,0.160,0.520]],
                           [[56.070,-104.970,849.910], [-10.000,1.920,-6.880], [-14.078,-6.138,12.772], [2.490,5.000,1.790], [0.172,16.517,6.181], [2.280,4.690,1.100]],
                           [[45.110,-103.120,843.530], [-11.000,4.810,-5.260], [-9.460,-1.100,18.780], [2.560,4.660,2.880], [6.930,18.410,4.840], [2.420,4.350,0.870]],
                           [[34.860,-95.590,839.810], [-9.590,8.680,-2.670], [-6.610,-0.760,21.270], [0.940,-0.410,0.560], [12.620,13.250,3.920], [0.000,0.160,-0.540]],
                           [[26.140,-85.990,838.230], [-8.260,10.160,-2.000], [-7.290,-2.000,20.040], [-0.320,-0.120,-0.850], [14.710,10.710,6.320], [-1.050,-0.470,0.410]],
                           [[18.390,-75.310,835.820], [-8.420,10.080,-2.660], [-7.370,-0.990,19.530], [-0.560,0.610,0.800], [16.030,10.170,6.780], [-0.360,-0.280,1.590]],
                           [[9.350,-65.880,832.920], [-11.900,13.240,-4.280], [-8.470,-0.620,21.630], [-0.850,0.480,1.280], [17.760,11.500,7.330], [-1.390,-0.780,1.040]],
                           [[-5.120,-48.680,827.110], [-17.030,21.160,-7.340], [-8.980,0.200,21.430], [-0.080,1.010,-1.640], [17.760,11.500,7.330], [-1.390,-0.780,1.040]]]
            for n in range(len(points)):
                node = nodes.findNodeByIdentifier(n + 1)
                fieldcache.setNode(node)
                coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_VALUE, 1, points[n][0])
                coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D_DS1, 1, points[n][1])
                coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D_DS2, 1, points[n][2])
                coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, points[n][3])
                coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D_DS3, 1, points[n][4])
                coordinates.setNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D2_DS1DS3, 1, points[n][5])
                                    
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
                    d1Unit = normalize(cross(d2, d3))
                    d1 = mult(d1Unit, edgeArcLength)
                    cd1[nodeIndexes[ln]].append(d1)
                    cd2[nodeIndexes[ln]].append(d2)
                    cd13[nodeIndexes[ln]].append(mult(d1Unit, edgeAngle * tubeRadius))
            # fix the one node out of order:
            for d in [cd1[4], cd2[4], cd13[4]]:
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

        elif "exfPath" in parameterSetName:
            sir = region.createStreaminformationRegion()
            sir.createStreamresourceFile("C:\\Users\\mlin865\\3D whole body dataset\\transferringMarkersFromMaleToFemale\\humanColon3_network_female.exf")
            region.read(sir)

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
        if (functionOptions["To field"]["inner coordinates"] or functionOptions["From field"]["inner coordinates"]) \
                and not innerCoordinates.isValid():
            print("Assign coordinates:  inner coordinates field not defined")
            return False, False
        mode = None
        if functionOptions["Mode"]["Scale"]:
            mode = cls.AssignCoordinatesMode.SCALE
        elif functionOptions["Mode"]["Offset"]:
            mode = cls.AssignCoordinatesMode.OFFSET
        else:
            print("Assign coordinates:  Invalid mode")
            return False, False
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
                return False, False

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
                _, originalNodeParameters = get_nodeset_field_parameters(editNodeset, toCoordinates, pathValueLabels)
                del tmpMeshGroup
                del tmpGroup
            _, nodeParameters = get_nodeset_field_parameters(editNodeset, fromCoordinates, pathValueLabels)

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

            set_nodeset_field_parameters(editNodeset, toCoordinates, pathValueLabels, nodeParameters, editGroupName)
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
        innerCoordinates = fieldmodule.findFieldByName("inner coordinates").castFiniteElement()
        if functionOptions["Field"]["inner coordinates"] and not innerCoordinates.isValid():
            print("Make side derivatives normal:  inner coordinates field not defined")
            return False, False
        useCoordinates = coordinates if functionOptions["Field"]["coordinates"] else innerCoordinates
        makeD2Normal = functionOptions['Make D2 normal']
        makeD3Normal = functionOptions['Make D3 normal']
        if not (makeD2Normal or makeD3Normal):
            return False, False
        nodeset = fieldmodule.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        make_nodeset_derivatives_orthogonal(nodeset, useCoordinates, makeD2Normal, makeD3Normal, editGroupName)
        return False, True  # settings not changed, nodes changed

    @classmethod
    def smoothSideCrossDerivatives(cls, region, options, networkMesh, functionOptions, editGroupName):
        """
        Smooth side cross derivatives giving rate of change of side directions d2, d3 w.r.t. d1.
        If a single element in a segment is selected, the whole segment is smoothed, and if the segment
        connects to others with the same version, they are also smoothed with it.
        Also detects loops back to the start of a segment.
        :param region: Region containing model to change parameters of.
        :param options: The scaffold settings used to create the original model, pre-edits.
        :param networkMesh: The NetworkMesh construction object model was created from.
        Used to determine connected paths for smoothing.
        :param functionOptions: Which side derivatives to smooth.
        :param editGroupName: Name of Zinc group to put edited nodes in.
        :return: boolean indicating if settings changed, boolean indicating if node parameters changed.
        """
        fieldmodule = region.getFieldmodule()
        coordinates = fieldmodule.findFieldByName("coordinates").castFiniteElement()
        innerCoordinates = fieldmodule.findFieldByName("inner coordinates").castFiniteElement()
        if functionOptions["Field"]["inner coordinates"] and not innerCoordinates.isValid():
            print("Make side derivatives normal:  inner coordinates field not defined")
            return False, False
        useCoordinates = coordinates if functionOptions["Field"]["coordinates"] else innerCoordinates
        smoothD12 = functionOptions["Smooth D12"]
        smoothD13 = functionOptions["Smooth D13"]
        if not (smoothD12 or smoothD13):
            return False, False

        nodes = fieldmodule.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        selectionGroup = scene_get_selection_group(region.getScene(), inherit_root_region=region.getRoot())
        selectionMeshGroup = None
        mesh1d = fieldmodule.findMeshByDimension(1)
        if selectionGroup:
            selectionMeshGroup = selectionGroup.getMeshGroup(mesh1d)
            if not selectionMeshGroup.isValid():
                print("Smooth side cross derivatives:  Selection must contain elements to smooth segment chains "
                    "containing them, or be clear it to smooth all segment chains.")
                return False, False
        getValueLabels = [Node.VALUE_LABEL_VALUE, Node.VALUE_LABEL_D_DS1]
        setValueLabels = []
        if smoothD12:
            getValueLabels.append(Node.VALUE_LABEL_D_DS2)
            setValueLabels.append(Node.VALUE_LABEL_D2_DS1DS2)
        if smoothD13:
            getValueLabels.append(Node.VALUE_LABEL_D_DS3)
            setValueLabels.append(Node.VALUE_LABEL_D2_DS1DS3)

        # determine segment chains which must be smoothed together:
        # currently only links segments aligned in the same direction
        networkSegments = networkMesh.getNetworkSegments()
        segmentChains = []
        segmentChainsLoop = []  # True if same index segment chain is a loop
        processedSegments = set()
        for segment in networkSegments:
            if segment in processedSegments:
                continue
            segmentChain = [segment]
            processedSegments.add(segment)
            # add other non-processed segments attached and using the same derivative version
            startNetworkNode = segment.getNetworkNodes()[0]
            startNodeVersion = segment.getNodeVersions()[0]
            endNetworkNode = segment.getNetworkNodes()[-1]
            endNodeVersion = segment.getNodeVersions()[-1]
            while True:
                for outSegment in endNetworkNode.getOutSegments():
                    if ((outSegment.getNodeVersions()[0] == endNodeVersion) and
                            outSegment not in processedSegments):
                        segmentChain.append(outSegment)
                        processedSegments.add(outSegment)
                        endNetworkNode = outSegment.getNetworkNodes()[-1]
                        endNodeVersion = outSegment.getNodeVersions()[-1]
                        break
                else:
                    break
            while True:
                for inSegment in startNetworkNode.getInSegments():
                    if ((inSegment.getNodeVersions()[-1] == startNodeVersion) and
                            inSegment not in processedSegments):
                        segmentChain.insert(0, inSegment)
                        processedSegments.add(inSegment)
                        startNetworkNode = inSegment.getNetworkNodes()[0]
                        startNodeVersion = inSegment.getNodeVersions()[0]
                        break
                else:
                    break
            segmentChains.append(segmentChain)
            segmentChainsLoop.append((startNetworkNode == endNetworkNode) and (startNodeVersion == endNodeVersion))

        with ChangeManager(fieldmodule):

            editNodeset = nodes
            if selectionGroup:
                # include only chains containing a selected element
                chainIndex = 0
                while chainIndex < len(segmentChains):
                    segmentChain = segmentChains[chainIndex]
                    for segment in segmentChain:
                        if segment.hasLayoutElementsInMeshGroup(selectionMeshGroup):
                            break
                    else:
                        segmentChains.pop(chainIndex)
                        segmentChainsLoop.pop(chainIndex)
                        continue
                    chainIndex += 1
                # make group of only nodes being edited
                tmpGroup = fieldmodule.createFieldGroup()
                editNodeset = tmpGroup.createNodesetGroup(nodes)
                for segmentChain in segmentChains:
                    for segment in segmentChain:
                        for nodeIdentifier in segment.getNodeIdentifiers():
                            editNodeset.addNode(nodes.findNodeByIdentifier(nodeIdentifier))
                del tmpGroup

            _, nodeParameters = get_nodeset_field_parameters(editNodeset, useCoordinates, setValueLabels)
            nodeIdentifierIndexes = {}
            for n in range(len(nodeParameters)):
                nodeIdentifierIndexes[nodeParameters[n][0]] = n

            for chainIndex in range(len(segmentChains)):
                # get parameters for chain
                segmentChain = segmentChains[chainIndex]
                loop = segmentChainsLoop[chainIndex]
                segmentsCount = len(segmentChain)
                nx = []
                nd1 = []
                sideVectorsCount = 2 if smoothD12 and smoothD13 else 1
                nsv = [[] for s in range(sideVectorsCount)]
                nodeIdentifiers = []
                nodeVersions = []
                for segmentIndex in range(segmentsCount):
                    segment = segmentChain[segmentIndex]
                    segmentNodeIdentifiers = segment.getNodeIdentifiers()
                    segmentNodeVersions = segment.getNodeVersions()
                    segmentParameters = get_nodeset_path_ordered_field_parameters(
                        nodes, useCoordinates, getValueLabels, segmentNodeIdentifiers, segmentNodeVersions)
                    nodesCount = len(segmentNodeIdentifiers)
                    if loop or (segmentIndex < (segmentsCount - 1)):
                        nodesCount -= 1
                    nx += segmentParameters[0][:nodesCount]
                    nd1 += segmentParameters[1][:nodesCount]
                    for s in range(sideVectorsCount):
                        nsv[s] += segmentParameters[2 + s][:nodesCount]
                    nodeIdentifiers += segmentNodeIdentifiers[:nodesCount]
                    nodeVersions += segmentNodeVersions[:nodesCount]
                dnsv = smoothCurveSideCrossDerivatives(nx, nd1, nsv, loop=loop)
                for n in range(len(nodeIdentifiers)):
                    nodeIndex = nodeIdentifierIndexes.get(nodeIdentifiers[n])
                    nodeVersion = nodeVersions[n] - 1
                    assert nodeIndex is not None
                    for s in range(sideVectorsCount):
                        nodeParameters[nodeIndex][1][s][nodeVersion] = dnsv[s][n]

            set_nodeset_field_parameters(editNodeset, useCoordinates, setValueLabels, nodeParameters, editGroupName)
            del editNodeset

        return False, True  # settings not changed, nodes changed

    @classmethod
    def getInteractiveFunctions(cls):
        """
        Supply client with functions for smoothing path parameters.
        """
        # add choice of field to base functions
        modifiedBaseInteractiveFunctions = []
        for interactiveFunction in Scaffold_base.getInteractiveFunctions():
            dct = {"Field": {"coordinates": True, "inner coordinates": False}}
            dct.update(interactiveFunction[1])
            modifiedBaseInteractiveFunctions.append((
               interactiveFunction[0], dct,
               interactiveFunction[2]))
        return modifiedBaseInteractiveFunctions + [
            ("Edit structure...", {
                "Structure": None},  # None = take value from options
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
            ("Make side derivatives normal...", {
                "Field": {"coordinates": True, "inner coordinates": False},
                "Make D2 normal": True,
                "Make D3 normal": True},
                lambda region, options, networkMesh, functionOptions, editGroupName:
                    cls.makeSideDerivativesNormal(region, options, networkMesh, functionOptions, editGroupName)),
            ("Smooth side cross derivatives...", {
                "Field": {"coordinates": True, "inner coordinates": False},
                "Smooth D12": True,
                "Smooth D13": True},
                lambda region, options, networkMesh, functionOptions, editGroupName:
                    cls.smoothSideCrossDerivatives(region, options, networkMesh, functionOptions, editGroupName))
        ]
