from unittest.mock import MagicMock, patch

import pytest
from typing import Any, Dict, List

from cura.Settings.IntentManager import IntentManager
from cura.Settings.MachineManager import MachineManager
from cura.Machines.QualityGroup import QualityGroup
from cura.Machines.QualityManager import QualityManager
from UM.Settings.ContainerRegistry import ContainerRegistry

from tests.Settings.MockContainer import MockContainer


@pytest.fixture()
def global_stack():
    return MagicMock(name="Global Stack")


@pytest.fixture()
def container_registry(application, global_stack) -> ContainerRegistry:
    result = MagicMock(name = "ContainerRegistry")
    result.findContainerStacks = MagicMock(return_value = [global_stack])
    application.getContainerRegistry = MagicMock(return_value = result)
    return result


@pytest.fixture()
def machine_manager(application, extruder_manager, container_registry, global_stack) -> MachineManager:
    application.getExtruderManager = MagicMock(return_value = extruder_manager)
    application.getGlobalContainerStack = MagicMock(return_value = global_stack)
    with patch("UM.Settings.ContainerRegistry.ContainerRegistry.getInstance", MagicMock(return_value=container_registry)):
        manager = MachineManager(application)

    return manager


@pytest.fixture()
def quality_manager(application, container_registry, global_stack) -> QualityManager:
    application.getGlobalContainerStack = MagicMock(return_value = global_stack)
    with patch("cura.CuraApplication.CuraApplication.getInstance", MagicMock(return_value = application)):
        with patch("UM.Settings.ContainerRegistry.ContainerRegistry.getInstance", MagicMock(return_value = container_registry)):
            manager = QualityManager(application)
    return manager


@pytest.fixture()
def intent_manager(application, extruder_manager, machine_manager, quality_manager, container_registry, global_stack) -> IntentManager:
    application.getExtruderManager = MagicMock(return_value = extruder_manager)
    application.getGlobalContainerStack = MagicMock(return_value = global_stack)
    application.getMachineManager = MagicMock(return_value = machine_manager)
    application.getQualityManager = MagicMock(return_value = quality_manager)
    with patch("cura.CuraApplication.CuraApplication.getInstance", MagicMock(return_value = application)):
        with patch("UM.Settings.ContainerRegistry.ContainerRegistry.getInstance", MagicMock(return_value = container_registry)):
            manager = IntentManager()
    return manager


mocked_intent_metadata = [
    {"id": "um3_aa4_pla_smooth_normal", "GUID": "abcxyz", "definition": "ultimaker3", "variant": "AA 0.4",
     "material_id": "generic_pla", "intent_category": "smooth", "quality_type": "normal"},
    {"id": "um3_aa4_pla_strong_abnorm", "GUID": "defqrs", "definition": "ultimaker3", "variant": "AA 0.4",
     "material_id": "generic_pla", "intent_category": "strong", "quality_type": "abnorm"}]  # type:List[Dict[str, str]]

mocked_qualitygroup_metadata = {
    "normal": QualityGroup("um3_aa4_pla_normal", ("default", "normal")),
    "abnorm": QualityGroup("um3_aa4_pla_abnorm", ("default", "abnorm"))}  # type:Dict[str, QualityGroup]


def mockFindMetadata(**kwargs) -> List[Dict[str, Any]]:
    if "id" in kwargs:
        return [x for x in mocked_intent_metadata if x["id"] == kwargs["id"]]
    else:
        result = []
        for data in mocked_intent_metadata:
            should_add = True
            for key, value in kwargs.items():
                if key in data.keys():
                    should_add &= (data[key] == value)
            if should_add:
                result.append(data)
        return result


def mockFindContainers(**kwargs) -> List[MockContainer]:
    result = []
    metadatas = mockFindMetadata(**kwargs)
    for metadata in metadatas:
        result.append(MockContainer(metadata))
    return result


def doSetup(application, extruder_manager, quality_manager, container_registry, global_stack) -> None:
    container_registry.findContainersMetadata = MagicMock(side_effect = mockFindMetadata)
    container_registry.findContainers = MagicMock(side_effect = mockFindContainers)

    quality_manager.getDefaultIntentQualityGroups = MagicMock(return_value = mocked_qualitygroup_metadata)
    for _, qualitygroup in mocked_qualitygroup_metadata.items():
        qualitygroup.node_for_global = MagicMock(name = "Node for global")
    application.getQualityManager = MagicMock(return_value = quality_manager)

    global_stack.definition = MockContainer({"id": "ultimaker3"})
    application.getGlobalContainerStack = MagicMock(return_value = global_stack)

    extruder_stack_a = MockContainer({"id": "Extruder The First"})
    extruder_stack_a.variant = MockContainer({"name": "AA 0.4"})
    extruder_stack_a.material = MockContainer({"base_file": "generic_pla"})
    extruder_stack_b = MockContainer({"id": "Extruder II: Plastic Boogaloo"})
    extruder_stack_b.variant = MockContainer({"name": "AA 0.4"})
    extruder_stack_b.material = MockContainer({"base_file": "generic_pla"})

    application.getGlobalContainerStack().extruderList = [extruder_stack_a, extruder_stack_b]
    extruder_manager.getUsedExtruderStacks = MagicMock(return_value = [extruder_stack_a, extruder_stack_b])


def test_intentCategories(application, intent_manager, container_registry):
    # Mock .findContainersMetadata so we also test .intentMetadatas (the latter is mostly a wrapper around the former).
    container_registry.findContainersMetadata = MagicMock(return_value = mocked_intent_metadata)

    with patch("cura.CuraApplication.CuraApplication.getInstance", MagicMock(return_value = application)):
        with patch("UM.Settings.ContainerRegistry.ContainerRegistry.getInstance", MagicMock(return_value = container_registry)):
            categories = intent_manager.intentCategories("ultimaker3", "AA 0.4", "generic_pla")  # type:List[str]
            assert "default" in categories, "default should always be in categories"
            assert "strong" in categories, "strong should be in categories"
            assert "smooth" in categories, "smooth should be in categories"


def test_getCurrentAvailableIntents(application, extruder_manager, quality_manager, intent_manager, container_registry, global_stack):
    doSetup(application, extruder_manager, quality_manager, container_registry, global_stack)

    with patch("cura.CuraApplication.CuraApplication.getInstance", MagicMock(return_value = application)):
        with patch("UM.Settings.ContainerRegistry.ContainerRegistry.getInstance", MagicMock(return_value = container_registry)):
            intents = intent_manager.getCurrentAvailableIntents()
            assert ("default", "normal") in intents
            assert ("default", "abnorm") in intents
            assert len(intents) == 2  # Or 4? pending to-do in 'IntentManager'? TODO?


def test_currentAvailableIntentCategories(application, extruder_manager, quality_manager, intent_manager, container_registry, global_stack):
    doSetup(application, extruder_manager, quality_manager, container_registry, global_stack)

    with patch("cura.CuraApplication.CuraApplication.getInstance", MagicMock(return_value=application)):
        with patch("UM.Settings.ContainerRegistry.ContainerRegistry.getInstance", MagicMock(return_value=container_registry)):
            with patch("cura.Settings.ExtruderManager.ExtruderManager.getInstance", MagicMock(return_value=extruder_manager)):
                categories = intent_manager.currentAvailableIntentCategories()
                assert "default" in categories  # Currently inconsistent with 'currentAvailableIntents'!
                assert "smooth" in categories
                assert "strong" in categories
                assert len(categories) == 3


def test_selectIntent(application, extruder_manager, quality_manager, intent_manager, container_registry, global_stack):
    doSetup(application, extruder_manager, quality_manager, container_registry, global_stack)

    with patch("cura.CuraApplication.CuraApplication.getInstance", MagicMock(return_value=application)):
        with patch("UM.Settings.ContainerRegistry.ContainerRegistry.getInstance", MagicMock(return_value=container_registry)):
            with patch("cura.Settings.ExtruderManager.ExtruderManager.getInstance", MagicMock(return_value=extruder_manager)):
                intents = intent_manager.getCurrentAvailableIntents()
                for intent, quality in intents:
                    intent_manager.selectIntent(intent, quality)
                    extruder_stacks = extruder_manager.getUsedExtruderStacks()
                    assert len(extruder_stacks) == 2
                    assert extruder_stacks[0].intent.getMetaDataEntry("intent_category") == intent
                    assert extruder_stacks[1].intent.getMetaDataEntry("intent_category") == intent
