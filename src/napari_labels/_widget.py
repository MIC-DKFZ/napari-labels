import json
from pathlib import Path

import numpy as np
import seaborn as sns
from napari import Viewer
from napari.layers import Labels
from napari.utils.colormaps import CyclicLabelColormap, DirectLabelColormap, label_colormap
from napari_toolkit.containers import setup_scrollarea, setup_vcollapsiblegroupbox, setup_vgroupbox
from napari_toolkit.containers.boxlayout import hstack
from napari_toolkit.utils import set_value
from napari_toolkit.utils.widget_getter import get_value
from napari_toolkit.widgets import (
    setup_checkbox,
    setup_combobox,
    setup_editcolorpicker,
    setup_editdoubleslider,
    setup_iconbutton,
    setup_label,
    setup_layerselect,
    setup_lineedit,
    setup_pushbutton,
    setup_radiobutton,
    setup_spinbox,
)
from qtpy.QtWidgets import (
    QFileDialog,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class LabelsControlWidget(QWidget):

    def __init__(self, viewer: Viewer):
        super().__init__()
        self._viewer = viewer
        self.file_ending = ".nclr"
        self.colormap_options = [
            "default",
            "random",
            # Categorical
            "deep",
            "tab10",
            "tab20",
            "Set1",
            # Sequential
            "gray",
            "viridis",
            "plasma",
            "inferno",
            "magma",
            "cividis",
            # "rocket",
            # "mako",
            "flare",
            "crest",
            "cubehelix",
            # Diverging
            "icefire",
            "coolwarm",
            "seismic",
            "Spectral",
            # Cyclic
            "hsv",
            "twilight",
        ]

        self.build_gui()

        self.build_picker()

        layer_name, _ = get_value(self.layerselect)
        if layer_name != "":
            layer = self._viewer.layers[layer_name]
            self.cmap = layer.colormap
            layer.events.colormap.connect(self.on_layer_changed)
        else:
            self.build_cmap("default", get_value(self.spinbox_numc))

        self.connect_picker()
        self.update_picker()

    # GUI
    def build_gui(self):
        main_layout = QVBoxLayout(self)
        _container, _layout = setup_vgroupbox(main_layout, "")

        # --- 1. INIT --- #
        # --- 1.1 Layer Selection --- #
        label = setup_label(None, "Label Layer:")
        label.setFixedWidth(120)
        self.layerselect = setup_layerselect(
            None, self._viewer, Labels, function=self.on_layer_changed
        )
        hstack(_layout, [label, self.layerselect])

        # --- 1.2 Number of Classes --- #
        label = setup_label(None, "Number Classes:")
        label.setFixedWidth(120)
        self.spinbox_numc = setup_spinbox(None, 2, 256, default=6, function=self.on_numc_changed)
        _ = hstack(_layout, [label, self.spinbox_numc])

        # --- 1.3 Apply to All Layers --- #
        label = setup_label(None, "")
        label.setFixedWidth(120)
        self.all_layers = setup_checkbox(
            None, "Apply to All Layers", checked=False, function=self.update_layercm
        )
        _ = hstack(_layout, [label, self.all_layers])

        # --- 2. COLORMAP --- #
        _container, _layout = setup_vcollapsiblegroupbox(main_layout, "Colormap:", True)
        self.combobox_cm = setup_combobox(
            None, self.colormap_options, placeholder="Select", function=self.on_cm_selected
        )
        self.lineedit_cm = setup_lineedit(
            None, "", placeholder="Colormap Name", function=self.on_cm_edited
        )
        self.combobox_cm.setCurrentIndex(-1)

        btn = setup_iconbutton(
            None, "", "new_labels", self._viewer.theme, function=self.on_refresh_cm
        )
        btn.setFixedWidth(26)
        hstack(_layout, [self.combobox_cm, self.lineedit_cm, btn])
        self.reverse_ckbx = setup_checkbox(
            _layout, "Reverse Colormap", False
        )  # ,function=self.on_cm_update)

        # --- 3. SETTINGS --- #
        _container, _layout = setup_vcollapsiblegroupbox(main_layout, "Settings:", True)

        # --- 3.1 Colormap Type --- #
        _tmp = setup_label(None, "CM Type:")
        _tmp.setFixedWidth(75)
        self.cyclic = setup_radiobutton(
            None, "Cyclic", checked=True, function=self.on_cm_type_changed
        )
        self.direct = setup_radiobutton(None, "Direct")
        _ = hstack(_layout, [_tmp, self.cyclic, self.direct])

        # --- 3.2 Reverse --- #
        _tmp = setup_label(None, "")
        _tmp.setFixedWidth(75)
        self.reverse_btn = setup_pushbutton(_layout, "Reverse", function=self.on_cm_reversed)
        _ = hstack(_layout, [_tmp, self.reverse_btn])

        # --- 3.3 Oppacity --- #
        label_opp = setup_label(None, "Oppacity:")
        label_opp.setFixedWidth(75)
        self.label_opp_slider = setup_editdoubleslider(
            None, digits=2, default=1.0, include_buttons=False, function=self.on_oppacity_changed
        )
        self.label_opp_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        _ = hstack(_layout, [label_opp, self.label_opp_slider])

        # --- 1.4. IO --- #
        _container, _layout = setup_vgroupbox(main_layout, "")
        self.load_btn = setup_pushbutton(None, "Load", function=self.load)
        self.save_btn = setup_pushbutton(None, "Save", function=self.save)
        _ = hstack(_layout, [self.load_btn, self.save_btn])

        # --- 4. CLASS COLORS --- #
        self.scroll_area = setup_scrollarea(main_layout)
        self.scroll_area.setWidgetResizable(True)

    def build_picker(self):
        _container, _layout = setup_vgroupbox(None, "Classes:")
        self.colorpickers = []

        numc = get_value(self.spinbox_numc)
        for i in range(numc):
            label = setup_label(None, f"{i}")
            label.setFixedWidth(24)
            cp = setup_editcolorpicker(None)
            if i == 0:
                cp.setEnabled(False)
                cp.set_color([0, 0, 0, 0])
            self.colorpickers.append(cp)
            hstack(_layout, [label, cp])
        self.scroll_area.setWidget(_container)

    # GETTER/SETTER
    def update_layercm(self):
        if get_value(self.all_layers):
            self._viewer.layers.events.inserted.connect(self.update_layercm)
            layers = [_layer for _layer in self._viewer.layers if isinstance(_layer, Labels)]
        else:
            layer_name, _ = get_value(self.layerselect)
            if layer_name == "":
                return
            layers = [self._viewer.layers[layer_name]]

        for layer in layers:
            self.disconnect_layer(layer)
            layer.colormap = self.cmap
            self.connect_layer(layer)

            layer.refresh()

    def update_picker(self):
        self.disconnect_picker()

        for i, p in enumerate(self.colorpickers):
            if i != 0:
                col = self.cmap.map(i)
                col = [int(col[0] * 255), int(col[1] * 255), int(col[2] * 255), col[3]]
                p.set_color(col)
                p.setEnabled(True)
                if i >= len(self.cmap) and isinstance(self.cmap, CyclicLabelColormap):
                    p.setEnabled(False)

        self.connect_picker()

    def get_cm_from_layer(self):
        layer_name, _ = get_value(self.layerselect)
        if layer_name == "":
            return
        self.cmap = self._viewer.layers[layer_name].colormap

    def get_cm_from_picker(self):
        colors = []
        for p in self.colorpickers:
            color = get_value(p)
            color = [color[0] / 255, color[1] / 255, color[2] / 255, color[3]]
            colors.append(color)
        if isinstance(self.cmap, CyclicLabelColormap):
            org_colors = self.cmap.colors

            for i in range(len(colors)):
                org_colors[i] = colors[i]

            self.cmap = CyclicLabelColormap(colors=np.array(org_colors))
        elif isinstance(self.cmap, DirectLabelColormap):
            color_dict = self.cmap.color_dict
            for i in range(len(colors)):
                color_dict[i] = colors[i]
            self.cmap = DirectLabelColormap(color_dict=color_dict)

    # EVENTS
    def on_layer_changed(self):
        self.get_cm_from_layer()
        self.update_picker()

    def on_picker_changed(self):
        self.get_cm_from_picker()
        self.update_layercm()

    def on_numc_changed(self):
        self.build_picker()
        self.connect_picker()
        self.update_picker()

    def on_refresh_cm(self):
        self.on_cm_selected()
        self.on_cm_edited()

    def on_cm_selected(self):
        cm_name, idx = get_value(self.combobox_cm)
        if idx != -1:
            numc = get_value(self.spinbox_numc)
            set_value(self.lineedit_cm, "")

            self.build_cm(cm_name, numc)

            self.update_layercm()
            self.update_picker()

    def on_cm_edited(self):
        cm_name = get_value(self.lineedit_cm)
        if cm_name != "":
            numc = get_value(self.spinbox_numc)
            self.combobox_cm.setCurrentIndex(-1)

            self.build_cm(cm_name, numc)

            self.update_layercm()
            self.update_picker()

    def on_cm_type_changed(self):
        self.convert_cm()
        self.update_layercm()
        self.update_picker()

    def on_cm_reversed(self):
        self.reverse_cm()
        self.update_layercm()
        self.update_picker()

    def on_oppacity_changed(self):
        self.oppacity_cm()
        self.update_layercm()
        self.update_picker()

    # FUNCTIONALITY
    def build_cm(self, cm_name, numc):

        if cm_name == "default":  # Default
            colors = label_colormap(num_colors=49, seed=0.5, background_value=0).colors[:, :3]
            colors = colors[1:numc]
        elif cm_name == "random":  # Random
            colors = label_colormap(
                num_colors=numc - 2, seed=np.random.random(), background_value=0
            ).colors[:, :3]
        else:  # Seaborn Colormaps
            colors = sns.color_palette(cm_name, numc - 1)

        colors = np.array(colors)

        if get_value(self.reverse_ckbx):
            colors = colors[::-1]

        if get_value(self.cyclic):
            colors = np.array([[1, 1, 1]] + list(colors))
            self.cmap = CyclicLabelColormap(
                colors=colors,
            )
        else:
            color_dict = {None: [0, 0, 0, 0]}
            for i in range(len(colors)):
                color_dict[i + 1] = colors[i]
            self.cmap = DirectLabelColormap(color_dict=color_dict)

    def convert_cm(self):
        if (isinstance(self.cmap, CyclicLabelColormap) and get_value(self.cyclic)) or (
            isinstance(self.cmap, DirectLabelColormap) and not get_value(self.cyclic)
        ):
            pass
        elif get_value(self.cyclic):
            color_dict = self.cmap.color_dict
            filtered_items = {k: v for k, v in color_dict.items() if isinstance(k, int)}
            if 0 not in list(filtered_items.keys()):
                filtered_items[0] = [0, 0, 0, 0]
            filtered_items = dict(sorted(filtered_items.items()))
            self.cmap = CyclicLabelColormap(colors=list(filtered_items.values()))

        else:
            color_dict = dict(enumerate(self.cmap.colors))
            color_dict[None] = [0, 0, 0, 0]
            color_dict[0] = [0, 0, 0, 0]
            self.cmap = DirectLabelColormap(color_dict=color_dict)

    def reverse_cm(self):

        if isinstance(self.cmap, CyclicLabelColormap):
            colors = self.cmap.colors
            controls = self.cmap.controls

            colors[1:] = colors[1:][::-1]

            self.cmap = CyclicLabelColormap(
                colors=np.array(colors),
                controls=np.array(controls),
            )
        elif isinstance(self.cmap, DirectLabelColormap):
            color_dict = self.cmap.color_dict

            filtered_items = {k: v for k, v in color_dict.items() if isinstance(k, int) and k > 0}
            keys, values = zip(*filtered_items.items()) if filtered_items else ([], [])
            color_dict.update(zip(keys, reversed(values)))

            self.cmap = DirectLabelColormap(color_dict=color_dict)

    def oppacity_cm(self):
        oppacity = get_value(self.label_opp_slider)
        if isinstance(self.cmap, CyclicLabelColormap):
            colors = self.cmap.colors
            controls = self.cmap.controls

            colors[1:, 3] = oppacity

            self.cmap = CyclicLabelColormap(
                colors=np.array(colors),
                controls=np.array(controls),
            )
        elif isinstance(self.cmap, DirectLabelColormap):
            color_dict = self.cmap.color_dict
            for k, v in color_dict.items():
                if k is not None and k != 0:
                    v[3] = oppacity

            self.cmap = DirectLabelColormap(color_dict=color_dict)

    def connect_layer(self, layer):
        layer.events.colormap.connect(self.on_layer_changed)

    def disconnect_layer(self, layer):
        layer.events.colormap.disconnect(self.on_layer_changed)

    def connect_picker(self):
        for i, p in enumerate(self.colorpickers):
            if i != 0:
                p.changed.connect(self.on_picker_changed)

    def disconnect_picker(self):
        for i, p in enumerate(self.colorpickers):
            if i != 0:
                p.changed.disconnect(self.on_picker_changed)

    # IO
    def save(self):

        _dialog = QFileDialog(self)
        _dialog.setDirectory(str(Path.cwd()))
        config_path, _ = _dialog.getSaveFileName(
            self,
            "Select File",
            f"color_map{self.file_ending}",
            filter=f"*{self.file_ending}",
            options=QFileDialog.DontUseNativeDialog,
        )
        if config_path is not None and config_path.endswith(self.file_ending):
            config_path = Path(config_path)
            # config_path = Path("config.col")
            numc = get_value(self.spinbox_numc)
            if isinstance(self.cmap, CyclicLabelColormap):
                colors = self.cmap.colors[1:]
                cm_type = "CyclicLabelColormap"
            elif isinstance(self.cmap, DirectLabelColormap):
                color_dict = {
                    k: v for k, v in self.cmap.color_dict.items() if isinstance(k, int) and k > 0
                }
                color_dict = dict(sorted(color_dict.items()))
                colors = list(color_dict.values())
                cm_type = "DirectLabelColormap"

            colors = np.array(colors).tolist()

            config = {"cm_type": cm_type, "numc": numc, "colors": colors}

            with Path(config_path).open("w") as f:
                json.dump(config, f, indent=4)
        else:
            print("No Valid File Selected")

    def load(self):
        _dialog = QFileDialog(self)
        _dialog.setDirectory(str(Path.cwd()))
        config_path, _ = _dialog.getOpenFileName(
            self,
            "Select File",
            filter=f"*{self.file_ending}",
            options=QFileDialog.DontUseNativeDialog,
        )
        if config_path is not None and config_path.endswith(self.file_ending):
            with Path(config_path).open("r") as f:
                config = json.load(f)

            numc = config["numc"]
            set_value(self.spinbox_numc, numc)

            if config["cm_type"] == "CyclicLabelColormap":
                self.cmap = CyclicLabelColormap(
                    colors=np.array([[0, 0, 0, 0]] + config["colors"]),
                )

            elif config["cm_type"] == "DirectLabelColormap":
                color_dict = dict(enumerate(config["colors"]))
                color_dict[None] = [0, 0, 0, 0]
                color_dict[0] = [0, 0, 0, 0]

                self.cmap = DirectLabelColormap(color_dict=color_dict)

            set_value(self.cyclic, isinstance(self.cmap, CyclicLabelColormap))
            set_value(self.direct, isinstance(self.cmap, DirectLabelColormap))

            self.update_layercm()
            self.update_picker()
        else:
            print("No Valid File Selected")
