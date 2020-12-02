"""
Generates a 3-D stomach based on Kumar's CMGUI stomach scaffold
"""

from scaffoldmaker.annotation.annotationgroup import AnnotationGroup, getAnnotationGroupForTerm, findOrCreateAnnotationGroupForTerm
from scaffoldmaker.annotation.stomach_terms import get_stomach_term
from scaffoldmaker.meshtypes.scaffold_base import Scaffold_base
from scaffoldmaker.scaffoldpackage import ScaffoldPackage
from scaffoldmaker.utils import interpolation as interp
from scaffoldmaker.utils import tubemesh
from scaffoldmaker.utils.tubemesh import CylindricalSegmentTubeMeshInnerPoints
from scaffoldmaker.utils import vector
from scaffoldmaker.utils.zinc_utils import exnodeStringFromNodeValues
from opencmiss.zinc.context import Context
from opencmiss.zinc.element import Element
from opencmiss.zinc.field import Field
from opencmiss.zinc.node import Node
from opencmiss.utils.zinc.field import findOrCreateFieldCoordinates, get_group_list
from opencmiss.utils.zinc.finiteelement import get_element_node_identifiers
from scaffoldmaker.utils.eft_utils import scaleEftNodeValueLabels, setEftScaleFactorIds
from scaffoldmaker.utils.eftfactory_tricubichermite import eftfactory_tricubichermite
from scaffoldmaker.utils.zinc_utils import mesh_destroy_elements_and_nodes_by_identifiers

class MeshType_3d_stomach1(Scaffold_base):
    '''
    Generates a 3-D stomach mesh from Kumar's CMGUI files by removing duplicate nodes,
    remaking annotation groups and implementing linear mapping on boundary between dorsal
    and ventral stomach.
    '''

    @staticmethod
    def getName():
        return '3D Stomach 1'

    @staticmethod
    def getParameterSetNames():
        return [
            'Default',
            'Rat 1']

    @classmethod
    def getDefaultOptions(cls, parameterSetName='Default'):
        return {
            'Refine': False,
            'Refine number of elements around': 2,
            'Refine number of elements along': 2,
            'Refine number of elements through wall': 1
        }

    @staticmethod
    def getOrderedOptionNames():
        return [
            'Refine',
            'Refine number of elements around',
            'Refine number of elements along',
            'Refine number of elements through wall' ]

    @classmethod
    def checkOptions(cls, options):
        for key in [
            'Refine number of elements around',
            'Refine number of elements along',
            'Refine number of elements through wall']:
            if options[key] < 1:
                options[key] = 1

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

        fieldModule = region.getFieldmodule()
        coordinates = findOrCreateFieldCoordinates(fieldModule)

        sir = region.createStreaminformationRegion()
        # sir.createStreamresourceFile('C:\\Users\\mlin865\\Stomach\\FromKumar_19112020\\reformatted\\mabelle\\dorsal_longitudinal_renumbered0.exnode')
        # sir.createStreamresourceFile('C:\\Users\\mlin865\\Stomach\\FromKumar_19112020\\reformatted\\mabelle\\dorsal_longitudinal_renumbered.exelem')
        sir.createStreamresourceFile('C:\\Users\\mlin865\\Stomach\\FromKumar_19112020\\reformatted\\mabelle\\stomach_all.exf')

        region.read(sir)

        allGroups = get_group_list(fieldModule)
        # fieldModule = region.getFieldmodule()
        nodeset = fieldModule.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        mesh = fieldModule.findMeshByDimension(3)

        # ensure no faces or rogue 2D elements, and delete orphaned nodes from latter
        mesh2d = fieldModule.findMeshByDimension(2)
        mesh2d.destroyAllElements()
        nodeset.destroyAllNodes()

        # coordinates = fieldModule.findFieldByName('coordinates').castFiniteElement()
        fieldcache = fieldModule.createFieldcache()

        nodeIdList = []
        xList = []
        d1List = []
        d2List = []

        nodeIter = nodeset.createNodeiterator()
        node = nodeIter.next()

        # print('coordinates.isValid() =', coordinates.isValid())
        # print('fieldcache.isValid() = ', fieldcache.isValid())

        fieldcache.setNode(node)
        while node.isValid():
            identifier = node.getIdentifier()
            fieldcacheCheck = fieldcache.setNode(node)
            # print('fieldcacheCheck = ', fieldcacheCheck)
            # result, x = coordinates.evaluateReal(fieldcache, 3) # doesnt generate the derivatives
            result, x = coordinates.getNodeParameters(fieldcache, -1, Node.VALUE_LABEL_VALUE, 1, 3)
            resultd1, d1 = coordinates.getNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D_DS1, 1, 3)
            resultd2, d2 = coordinates.getNodeParameters(fieldcache, -1, Node.VALUE_LABEL_D_DS2, 1, 3)
            # print('Node', identifier, result, x)
            # print('Node', identifier, resultd1, d1)
            # print('Node', identifier, resultd2, d2)
            # do stuff with node
            node = nodeIter.next()
            nodeIdList.append(identifier)
            xList.append(x)
            d1List.append(d1)
            d2List.append(d2)

        # Find nodes in same position with same derivatives and nodes in same position but opposite derivatives
        duplicateDorsalLayerNodesMap = []
        duplicateVentralLayerNodesMap = []
        duplicateMirrorNodesMap = []
        # remapNodesD1OnlyMap = []
        remapNodesD2OnlyMap = []
        remapNodesD1D2Map = []

        # Check through dorsal layers first
        for i in range(len(xList)):
            nodesToDelete = []
            if nodeIdList[i] > 11000:
                break
            else:
                for j in range(i + 1, len(xList)):
                    if nodeIdList[j] > 11000:
                        break
                    else:
                        if xList[i] == xList[j] and d1List[i] == d1List[j] and d2List[i] == d2List[j]:
                            # print(nodeIdList[i], nodeIdList[j])
                            duplicateDorsalLayerNodesMap.append([nodeIdList[j], nodeIdList[i]])
                            nodesToDelete.append(j)

                if nodesToDelete:
                    for n in range(len(nodesToDelete)-1, -1, -1):
                        j = nodesToDelete[n]
                        del xList[j]
                        del d1List[j]
                        del d2List[j]
                        del nodeIdList[j]

        # Check through ventral layers
        for i in range(len(xList)):
            nodesToDelete = []
            if i == len(xList): # force terminate and iterator does not know that len of list has changed with deletion
                break
            if nodeIdList[i] == 15104: # 15104 close to 16010 but not exactly the same spot
                duplicateVentralLayerNodesMap.append([16010, 15104])
            if nodeIdList[i] > 11000:
                for j in range(i + 1, len(xList)):
                    if nodeIdList[j] > 11000:
                        if xList[i] == xList[j] and d1List[i] == d1List[j] and d2List[i] == d2List[j]:
                            # print(nodeIdList[i], nodeIdList[j])
                            duplicateVentralLayerNodesMap.append([nodeIdList[j], nodeIdList[i]])
                            nodesToDelete.append(j)

                if nodesToDelete:
                    for n in range(len(nodesToDelete) - 1, -1, -1):
                        j = nodesToDelete[n]
                        del xList[j]
                        del d1List[j]
                        del d2List[j]
                        del nodeIdList[j]

        # print('len of duplicate dorsal List = ', len(duplicateDorsalLayerNodesMap))
        # print('len of duplicate ventral List = ', len(duplicateVentralLayerNodesMap))
        duplicateNodesMap = duplicateDorsalLayerNodesMap + duplicateVentralLayerNodesMap

        # Identify nodes that need remapping:
        for i in range(len(nodeIdList)):
            nodesToDelete = []
            if i == len(nodeIdList):
                break
            if nodeIdList[i] < 11000:
                for j in range(i + 1, len(nodeIdList)):
                    if nodeIdList[j] > 11000:
                        xDiff = [abs(xList[i][c] - xList[j][c]) for c in range(3)]
                        if xDiff[0] <= 1e-2 and xDiff[1] <= 1e-2 and xDiff[2] <= 1e-2:
                            # print(nodeIdList[i], nodeIdList[j])
                            duplicateMirrorNodesMap.append([nodeIdList[j], nodeIdList[i]])
                            nodesToDelete.append(j)
                            # need to update renumbered duplicate list to the mirror node we retain
                            for n in range(len(duplicateNodesMap)):
                                if duplicateNodesMap[n][1] == nodeIdList[j]:
                                    duplicateNodesMap[n][1] = nodeIdList[i]
                            # if d1List[i] != d1List[j] and d2List[i] == d2List[j]:
                            #     print('remap d1 only')
                            #     #print(nodeIdList[i], nodeIdList[j])
                            #     remapNodesD1OnlyMap.append([nodeIdList[j], nodeIdList[i]])
                            if d1List[i] == d1List[j] and d2List[i] != d2List[j]:
                                # print('remap d2 only')
                                # print(nodeIdList[i], nodeIdList[j])
                                remapNodesD2OnlyMap.append([nodeIdList[j], nodeIdList[i]])
                            elif d1List[i] != d1List[j] and d2List[i] != d2List[j]:
                                # print('remap d1 & d2')
                                # print(nodeIdList[i], nodeIdList[j])
                                remapNodesD1D2Map.append([nodeIdList[j], nodeIdList[i]])

                if nodesToDelete:
                    for n in range(len(nodesToDelete) - 1, -1, -1):
                        j = nodesToDelete[n]
                        del xList[j]
                        del d1List[j]
                        del d2List[j]
                        del nodeIdList[j]

        # print('D1 remap')
        # for n in range(len(remapNodesD1Map)):
        #     print(remapNodesD1Map[n][1], remapNodesD1Map[n][0])
        #
        # print('D2 remap')
        # for n in range(len(remapNodesD2Map)):
        #     print(remapNodesD2Map[n][1], remapNodesD2Map[n][0])

        duplicateNodesMap += duplicateMirrorNodesMap

        elementtemplate = mesh.createElementtemplate()
        elementIter = mesh.createElementiterator()
        element = elementIter.next()
        stomachGroup = AnnotationGroup(region, get_stomach_term("stomach"))

        while element.isValid():
            # do stuff with element
            eft = element.getElementfieldtemplate(coordinates, -1)
            nodeIdentifiers = get_element_node_identifiers(element, eft)
            elementId = element.getIdentifier()
            # result, scalefactors = element.getScaleFactors(eft, 64)
            # print(len(scalefactors))
            # for s in scalefactors:
            #     if s != 1.0:
            #         print('non unit scale factor', s)

            # Replace duplicate nodes
            newNodeIdentifiers = []
            # remapD1 = []
            remapD2 = []
            remapD1D2 = []
            for n in range(len(nodeIdentifiers)):
                nodeID = nodeIdentifiers[n]
                newNodeIdentifiers.append(nodeID)
                for i in range(len(duplicateNodesMap)):
                    if nodeID == duplicateNodesMap[i][0]:
                        # print(nodeID, duplicateNodesMap[i])
                        newNodeIdentifiers[-1] = duplicateNodesMap[i][1]
                        for m in range(len(remapNodesD2OnlyMap)):
                            if nodeID == remapNodesD2OnlyMap[m][0]:
                                remapD2.append(n + 1)
                                break
                        for m in range(len(remapNodesD1D2Map)):
                            if nodeID == remapNodesD1D2Map[m][0]:
                                remapD1D2.append(n + 1)
                                break
                        break
            # print('new nodeIdentifiers:', newNodeIdentifiers)

            # scaleFactorsCount = eft.getNumberOfLocalScaleFactors()
            functionsCount = eft.getNumberOfFunctions()
            for fn in range(1, functionsCount + 1):
                result = eft.setTermScaling(fn, 1, [])
            eft.setNumberOfLocalScaleFactors(0)

            if remapD2 or remapD1D2:
                setEftScaleFactorIds(eft, [1], [])
                if remapD2:
                    if remapD2 == [8]:
                        remapD2 = [4, 8]
                    # print(element.getIdentifier(), 'D2', remapD2)
                    scaleEftNodeValueLabels(eft, remapD2,
                                            [Node.VALUE_LABEL_D_DS2, Node.VALUE_LABEL_D2_DS1DS2,
                                             Node.VALUE_LABEL_D2_DS2DS3, Node.VALUE_LABEL_D3_DS1DS2DS3], [1])
                elif remapD1D2:
                    if remapD1D2 == [6, 8]:
                        remapD1D2 = [2, 4, 6, 8]
                    if remapD1D2 == [5]:
                        remapD1D2 = [1, 5]
                        print(element.getIdentifier(), 'D1D2', remapD1D2)
                    scaleEftNodeValueLabels(eft, remapD1D2,
                                            [Node.VALUE_LABEL_D_DS1, Node.VALUE_LABEL_D_DS2, Node.VALUE_LABEL_D2_DS1DS3,
                                             Node.VALUE_LABEL_D2_DS2DS3], [1])

            result1 = elementtemplate.defineField(coordinates, -1, eft)
            result2 = element.merge(elementtemplate)
            element.setNodesByIdentifier(eft, newNodeIdentifiers)
            if eft.getNumberOfLocalScaleFactors() == 1:
                element.setScaleFactors(eft, [-1.0])
            stomachGroup.getMeshGroup(mesh).addElement(element)
            # print('element', element.getIdentifier(), result1, result2)
            element = elementIter.next()

        mesh_destroy_elements_and_nodes_by_identifiers(mesh, [2064, 4064, 5064, 12064, 14064, 15064])

        nodeset.destroyAllNodes()

        longitudinalGroup = AnnotationGroup(region, get_stomach_term("Longitudinal muscle layer of stomach"))
        is_dorsal_longitudinal = fieldModule.findFieldByName('dorsal_longitudinal')
        is_ventral_longitudinal = fieldModule.findFieldByName('ventral_longitudinal')
        is_longitudinal = fieldModule.createFieldOr(is_dorsal_longitudinal, is_ventral_longitudinal)
        longitudinalGroup.getMeshGroup(mesh).addElementsConditional(is_longitudinal)
        # print('longitudinalGroup size',longitudinalGroup.getMeshGroup(mesh).getSize(), is_longitudinal.isValid())

        circularGroup = AnnotationGroup(region, get_stomach_term("stomach smooth muscle circular layer"))
        is_dorsal_circular = fieldModule.findFieldByName('dorsal_circular')
        is_ventral_circular = fieldModule.findFieldByName('ventral_circular')
        is_circular = fieldModule.createFieldOr(is_dorsal_circular, is_ventral_circular)
        circularGroup.getMeshGroup(mesh).addElementsConditional(is_circular)

        submucosaGroup = AnnotationGroup(region, get_stomach_term("submucosa of stomach"))
        is_dorsal_submucosa = fieldModule.findFieldByName('dorsal_submucosal')
        is_ventral_submucosa = fieldModule.findFieldByName('ventral_submucosal')
        is_submucosa = fieldModule.createFieldOr(is_dorsal_submucosa, is_ventral_submucosa)
        submucosaGroup.getMeshGroup(mesh).addElementsConditional(is_submucosa)

        mucosaGroup = AnnotationGroup(region, get_stomach_term("mucosa of stomach"))
        is_dorsal_mucosa = fieldModule.findFieldByName('dorsal_mucosal')
        is_ventral_mucosa = fieldModule.findFieldByName('ventral_mucosal')
        is_mucosa = fieldModule.createFieldOr(is_dorsal_mucosa, is_ventral_mucosa)
        mucosaGroup.getMeshGroup(mesh).addElementsConditional(is_mucosa)

        # # Replace with wedge elements on dorsal forestomach
        tricubichermite = eftfactory_tricubichermite(mesh, None)
        eftDorsal = tricubichermite.createEftWedgeDorsal([4, 8])
        elementIdentifiers = [2064, 4064, 5064]
        newNodeIdList = [[2073, 2082, 2074, 2167, 2176, 2168], [2167, 2176, 2168, 4167, 4176, 4168],
                         [4167, 4176, 4168, 5167, 5176, 5168]]
        elementtemplateDorsal = mesh.createElementtemplate()
        elementtemplateDorsal.setElementShapeType(Element.SHAPE_TYPE_CUBE)
        elementtemplateDorsal.defineField(coordinates, -1, eftDorsal)
        for i in range(3):
            elementIdentifier = elementIdentifiers[i]
            newNodeIdentifiers = newNodeIdList[i]
            element = mesh.createElement(elementIdentifier, elementtemplateDorsal)
            element.setNodesByIdentifier(eftDorsal, newNodeIdentifiers)
            stomachGroup.getMeshGroup(mesh).addElement(element)
            if i == 0:
                longitudinalGroup.getMeshGroup(mesh).addElement(element)
            elif i == 1:
                circularGroup.getMeshGroup(mesh).addElement(element)
            elif i == 2:
                submucosaGroup.getMeshGroup(mesh).addElement(element)

        # # Replacing with wedge element on ventral forestomach
        eftVentral = tricubichermite.createEftWedgeVentral([4, 8])
        elementIdentifiers = [12064, 14064, 15064]
        newNodeIdList = [[12074, 2082, 2073, 12168, 2176, 2167], [12168, 2176, 2167, 14168, 4176, 4167],
                       [14168, 4176, 4167, 15168, 5176, 5167]]
        elementtemplateVentral = mesh.createElementtemplate()
        elementtemplateVentral.setElementShapeType(Element.SHAPE_TYPE_CUBE)
        elementtemplateVentral.defineField(coordinates, -1, eftVentral)
        for i in range(3):
            elementIdentifier = elementIdentifiers[i]
            newNodeIdentifiers = newNodeIdList[i]
            element = mesh.createElement(elementIdentifier, elementtemplateVentral)
            element.setNodesByIdentifier(eftVentral, newNodeIdentifiers)
            element.setScaleFactors(eftVentral, [-1.0])
            stomachGroup.getMeshGroup(mesh).addElement(element)
            if i == 0:
                longitudinalGroup.getMeshGroup(mesh).addElement(element)
            elif i == 1:
                circularGroup.getMeshGroup(mesh).addElement(element)
            elif i == 2:
                submucosaGroup.getMeshGroup(mesh).addElement(element)


        annotationGroups = [stomachGroup, longitudinalGroup, circularGroup, submucosaGroup, mucosaGroup]

        for group in allGroups:
            group.setManaged(False)
        del allGroups

        # region.writeFile('C:\\Users\\mlin865\\mapclient_workflow\\stomach_all_out.exf')

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

    @classmethod
    def defineFaceAnnotations(cls, region, options, annotationGroups):
        '''
        Add face annotation groups from the highest dimension mesh.
        Must have defined faces and added subelements for highest dimension groups.
        :param region: Zinc region containing model.
        :param options: Dict containing options. See getDefaultOptions().
        :param annotationGroups: List of annotation groups for top-level elements.
        New face annotation groups are appended to this list.
        '''

        # Create 2d surface mesh groups
        fm = region.getFieldmodule()
        longitudinalGroup = getAnnotationGroupForTerm(annotationGroups, get_stomach_term("Longitudinal muscle layer of stomach"))

        mesh2d = fm.findMeshByDimension(2)

        is_exterior = fm.createFieldIsExterior()
        is_exterior_face_xi3_0 = fm.createFieldAnd(is_exterior, fm.createFieldIsOnFace(Element.FACE_TYPE_XI3_0))
        # is_exterior_face_xi3_1 = fm.createFieldAnd(is_exterior, fm.createFieldIsOnFace(Element.FACE_TYPE_XI3_1))
        is_face_xi3_1 = fm.createFieldIsOnFace(Element.FACE_TYPE_XI3_1)

        is_longitudinal = longitudinalGroup.getFieldElementGroup(mesh2d)
        is_serosa = fm.createFieldAnd(is_longitudinal, is_exterior_face_xi3_0)
        is_myenteric = fm.createFieldAnd(is_longitudinal, is_face_xi3_1) #is_exterior_face_xi3_1)

        serosaGroup = findOrCreateAnnotationGroupForTerm(annotationGroups, region, get_stomach_term("serosa of stomach"))
        serosaGroup.getMeshGroup(mesh2d).addElementsConditional(is_serosa)

        myentericGroup = findOrCreateAnnotationGroupForTerm(annotationGroups, region, get_stomach_term("myenteric nerve plexus"))
        myentericGroup.getMeshGroup(mesh2d).addElementsConditional(is_myenteric)
