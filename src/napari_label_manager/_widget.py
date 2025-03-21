import numpy as np
import seaborn as sns
from napari import Viewer
from napari.layers import Labels
from napari.utils.colormaps import CyclicLabelColormap, DirectLabelColormap, label_colormap
from napari_toolkit.containers import (
    setup_scrollarea,
    setup_vgroupbox
)
from napari_toolkit.containers.boxlayout import hstack,vstack
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
    setup_radiobutton,
    setup_spinbox, setup_lineedit,setup_pushbutton
)
from qtpy.QtWidgets import (
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class LabelManager(QWidget):
    def __init__(self, viewer: Viewer):
        super().__init__()
        self._viewer = viewer
        self.colormap_options = [
            "default",
            "random",
            # Categorical
            "deep",
            "muted",
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
            "rocket",
            "mako",
            "flare",
            "crest",
            # Diverging
            "icefire",
            "vlag",
            "coolwarm",
            "seismic",
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
        self.set_picker_cmap()

        self.connect_picker()

    def build_gui(self):
        main_layout = QVBoxLayout(self)
        _container, _layout = setup_vgroupbox(main_layout, "")
        # Layer Selection
        label = setup_label(None, "Label Layer:")
        label.setFixedWidth(120)
        self.layerselect = setup_layerselect(
            None, self._viewer, Labels, function=self.on_layer_changed
        )
        hstack(_layout, [label, self.layerselect])
        # rbtn = setup_radiobutton(main_layout, "Apply for all Layers")

        # Number of Classes
        label = setup_label(None, "Number Classes:")
        label.setFixedWidth(120)
        self.spinbox_numc = setup_spinbox(None, 2, 256, default=6, function=self.on_numc_changed)
        _ = hstack(_layout, [label, self.spinbox_numc])

        # To all layers
        label = setup_label(None, "")
        label.setFixedWidth(120)
        self.all_layers=setup_checkbox(None, "Apply to All Layers",checked=False,function=self.set_layer_cmap)
        _ = hstack(_layout, [label, self.all_layers])

        # --- Colormap --- #
        _container, _layout = setup_vgroupbox(main_layout, "Colormap:")
        self.combobox_cm = setup_combobox(None, self.colormap_options,placeholder="Select", function=self.on_cm_selected)
        self.lineedit_cm=setup_lineedit(None,"",placeholder="Colormap Name",function=self.on_cm_edit)
        self.combobox_cm.setCurrentIndex(-1)

        btn = setup_iconbutton(
                None, "", "new_labels", self._viewer.theme, function=self.on_cm_update
            )
        btn.setFixedWidth(26)
        hstack(_layout, [self.combobox_cm,self.lineedit_cm,btn])
        self.reverse_ckbx=setup_checkbox(_layout,"Reverse Colormap",False,function=self.on_cm_update)

        # --- Appearance --- #
        _container, _layout = setup_vgroupbox(main_layout, "Settings:")

        # Colormap Type
        _tmp = setup_label(None, "CM Type:")
        _tmp.setFixedWidth(75)
        self.cyclic = setup_radiobutton(None, "Cyclic", checked=True, function=self.convert_cm)
        self.direct = setup_radiobutton(None, "Direct", function=self.convert_cm)
        _ = hstack(_layout, [_tmp, self.cyclic, self.direct])

        # Reverse
        _tmp = setup_label(None, "")
        _tmp.setFixedWidth(75)
        self.reverse_btn = setup_pushbutton(_layout, "Reverse", function=self.reverse_cm)
        _ = hstack(_layout, [_tmp, self.reverse_btn])

        # Oppacity
        label_opp = setup_label(None, "Oppacity:")
        label_opp.setFixedWidth(75)
        self.label_opp_slider = setup_editdoubleslider(
            None, digits=2, default=1.0, include_buttons=False, function=self.set_picker_opp
        )
        self.label_opp_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        _ = hstack(_layout, [label_opp, self.label_opp_slider])

        # --- Classes --- #
        self.scroll_area = setup_scrollarea(main_layout)
        self.scroll_area.setWidgetResizable(True)

    def build_cmap(self, cm_name, numc):

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

    def build_picker(self):

        _container, _layout = setup_vgroupbox(None, "Classes:")
        self.colorpickers = []

        numc = get_value(self.spinbox_numc)
        for i in range(numc):
            label = setup_label(None, f"{i}")
            label.setFixedWidth(20)
            cp = setup_editcolorpicker(None)
            if i == 0:
                cp.setEnabled(False)
                cp.set_color([0, 0, 0, 0])
            self.colorpickers.append(cp)
            hstack(_layout, [label, cp])
        self.scroll_area.setWidget(_container)

    def connect_picker(self):
        for i, p in enumerate(self.colorpickers):
            if i != 0:
                p.changed.connect(lambda x=i: self.on_picker_changed(x))

    def set_picker_cmap(self):
        for i, p in enumerate(self.colorpickers):
            if i != 0:
                col = self.cmap.map(i)
                col = [int(col[0] * 255), int(col[1] * 255), int(col[2] * 255), col[3]]
                p.set_color(col)
                p.setEnabled(True)
                if i >= len(self.cmap) and isinstance(self.cmap, CyclicLabelColormap):
                    p.setEnabled(False)

    def set_layer_cmap(self):
        if get_value(self.all_layers):
            layers = [_layer for _layer in self._viewer.layers if isinstance(_layer,Labels)]
        else:
            layer_name, _ = get_value(self.layerselect)
            if layer_name == "":
                return
            layers=[self._viewer.layers[layer_name]]

        for layer in layers:

            layer.events.colormap.disconnect(self.on_layer_changed)
            layer.colormap = self.cmap
            layer.events.colormap.connect(self.on_layer_changed)

            layer.refresh()

    def set_picker_opp(self):
        val = get_value(self.label_opp_slider)

        for i, p in enumerate(self.colorpickers):
            if i != 0:
                p.set_oppacity(val)

    # Event driven functions
    def on_layer_changed(self):
        layer_name, _ = get_value(self.layerselect)
        if layer_name != "":
            layer = self._viewer.layers[layer_name]
            self.cmap = layer.colormap
            layer.events.colormap.disconnect(self.on_layer_changed)
            self.set_picker_cmap()
            layer.events.colormap.connect(self.on_layer_changed)

            self.cyclic.setChecked(isinstance(layer.colormap, CyclicLabelColormap))
            self.direct.setChecked(isinstance(layer.colormap, DirectLabelColormap))

    def on_cm_update(self):
        self.on_cm_selected()
        self.on_cm_edit()


    def on_cm_edit(self):
        cm_name=get_value(self.lineedit_cm)
        if cm_name != "":
            try:
                print(cm_name)
                self.combobox_cm.setCurrentIndex(-1)
                self.on_cm_changed(cm_name)
            except ValueError:
                return

    def on_cm_selected(self):
        cm_name, idx = get_value(self.combobox_cm)
        if idx != -1:  # None
            set_value(self.lineedit_cm,"")
            self.on_cm_changed(cm_name)

    def on_cm_changed(self,cm_name):

        numc = get_value(self.spinbox_numc)
        self.build_cmap(cm_name, numc)

        layer, _ = get_value(self.layerselect)
        if layer != "":
            self.set_layer_cmap()
        # else:
        self.set_picker_cmap()

    def on_numc_changed(self):
        self.build_picker()
        self.set_picker_cmap()
        self.connect_picker()

    def on_picker_changed(self, idx):
        layer_name, _ = get_value(self.layerselect)

        if layer_name == "":
            return

        layer = self._viewer.layers[layer_name]

        color = get_value(self.colorpickers[idx])
        color = [color[0] / 255, color[1] / 255, color[2] / 255, color[3]]

        if isinstance(layer.colormap, CyclicLabelColormap):
            colors = layer.colormap.colors
            controls = layer.colormap.controls
            if 0 <= idx < len(colors):
                colors[idx] = color

            self.cmap = CyclicLabelColormap(
                colors=np.array(colors),
                controls=np.array(controls),
            )
        elif isinstance(layer.colormap, DirectLabelColormap):
            color_dict = layer.colormap.color_dict.copy()
            color_dict[idx] = color
            self.cmap = DirectLabelColormap(color_dict=color_dict)

        else:
            print(f"Colormap Class {type(layer.colormap)} is not supported")
            return

        self.set_layer_cmap()

    def convert_cm(self):
        if (isinstance(self.cmap, CyclicLabelColormap) and get_value(self.cyclic)) or (isinstance(self.cmap, DirectLabelColormap) and not get_value(self.cyclic)):
            pass
        elif get_value(self.cyclic):
            color_dict = self.cmap.color_dict
            filtered_items = {k: v for k, v in color_dict.items() if isinstance(k, int)}
            if 0 not in list(filtered_items.keys()):
                filtered_items[0]=[0,0,0,0]
            filtered_items=dict(sorted(filtered_items.items()))
            self.cmap = CyclicLabelColormap(colors=list(filtered_items.values()))


        else:
            color_dict={i: color for i, color in enumerate(self.cmap.colors)}
            color_dict[None] = [0,0,0,0]
            color_dict[0] = [0,0,0,0]
            self.cmap = DirectLabelColormap(color_dict=color_dict)

        self.set_layer_cmap()
        self.set_picker_cmap()


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

            filtered_items = {k: v for k, v in color_dict.items() if
                              isinstance(k, int) and k > 0}
            keys, values = zip(*filtered_items.items()) if filtered_items else ([], [])
            color_dict.update(zip(keys, reversed(values)))

            self.cmap = DirectLabelColormap(color_dict=color_dict)

        self.set_layer_cmap()
        self.set_picker_cmap()