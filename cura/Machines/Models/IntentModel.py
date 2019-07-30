# Copyright (c) 2019 Ultimaker B.V.
# Cura is released under the terms of the LGPLv3 or higher.

from typing import Optional, List, Dict, Any

from PyQt5.QtCore import Qt, QObject, pyqtProperty, pyqtSignal

from UM.Qt.ListModel import ListModel
from UM.Settings.ContainerRegistry import ContainerRegistry
from UM.Settings.SettingFunction import SettingFunction

from cura.Settings.IntentManager import IntentManager
import cura.CuraApplication


class IntentModel(ListModel):
    NameRole = Qt.UserRole + 1
    QualityTypeRole = Qt.UserRole + 2
    LayerHeightRole = Qt.UserRole + 3
    AvailableRole = Qt.UserRole + 4

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        self.addRoleName(self.NameRole, "name")
        self.addRoleName(self.QualityTypeRole, "quality_type")
        self.addRoleName(self.LayerHeightRole, "layer_height")
        self.addRoleName(self.AvailableRole, "available")

        self._intent_category = "engineering"

        ContainerRegistry.getInstance().containerAdded.connect(self._onChanged)
        ContainerRegistry.getInstance().containerRemoved.connect(self._onChanged)
        self._layer_height_unit = ""  # This is cached
        self._update()

    intentCategoryChanged = pyqtSignal()

    def setIntentCategory(self, new_category: str) -> None:
        if self._intent_category != new_category:
            self._intent_category = new_category
            self.intentCategoryChanged.emit()
            self._update()

    @pyqtProperty(str, fset = setIntentCategory, notify = intentCategoryChanged)
    def intentCategory(self) -> str:
        return self._intent_category

    def _onChanged(self, container):
        if container.getMetaDataEntry("type") == "intent":
            self._update()

    def _update(self) -> None:
        new_items = []  # type: List[Dict[str, Any]]
        application = cura.CuraApplication.CuraApplication.getInstance()
        intent_manager = application.getIntentManager()
        global_stack = application.getGlobalContainerStack()
        if not global_stack:
            self.setItems(new_items)
            return
        quality_groups = intent_manager.getQualityGroups(global_stack)

        for quality_tuple, quality_group in quality_groups.items():
            new_items.append({"name": quality_group.name,
                              "quality_type": quality_tuple[1],
                              "layer_height": self._fetchLayerHeight(quality_group),
                              "available": True
                              })

        new_items = sorted(new_items, key=lambda x: x["layer_height"])
        self.setItems(new_items)

    #TODO: Copied this from QualityProfilesDropdownMenuModel for the moment. This code duplication should be fixed.
    def _fetchLayerHeight(self, quality_group) -> float:
        global_stack = cura.CuraApplication.CuraApplication.getInstance().getMachineManager().activeMachine
        if not self._layer_height_unit:
            unit = global_stack.definition.getProperty("layer_height", "unit")
            if not unit:
                unit = ""
            self._layer_height_unit = unit

        default_layer_height = global_stack.definition.getProperty("layer_height", "value")

        # Get layer_height from the quality profile for the GlobalStack
        if quality_group.node_for_global is None:
            return float(default_layer_height)
        container = quality_group.node_for_global.getContainer()

        layer_height = default_layer_height
        if container and container.hasProperty("layer_height", "value"):
            layer_height = container.getProperty("layer_height", "value")
        else:
            # Look for layer_height in the GlobalStack from material -> definition
            container = global_stack.definition
            if container and container.hasProperty("layer_height", "value"):
                layer_height = container.getProperty("layer_height", "value")

        if isinstance(layer_height, SettingFunction):
            layer_height = layer_height(global_stack)

        return float(layer_height)
