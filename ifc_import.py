# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2022 Yorik van Havre <yorik@uncreated.net>              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU General Public License (GPL)            *
# *   as published by the Free Software Foundation; either version 3 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU General Public License for more details.                          *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

import importlib
import os
import time

import FreeCAD
import ifc_tools
import ifc_psets
import ifc_materials
import ifc_layers

if FreeCAD.GuiUp:
    import FreeCADGui


params = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/NativeIFC")


def open(filename):
    """Opens an IFC file"""

    name = os.path.splitext(os.path.basename(filename))[0]
    FreeCAD.IsOpeningIFC = True
    doc = FreeCAD.newDocument()
    doc.Label = name
    FreeCAD.setActiveDocument(doc.Name)
    insert(filename, doc.Name)
    del FreeCAD.IsOpeningIFC
    return doc


def insert(
    filename,
    docname,
    strategy=None,
    shapemode=None,
    switchwb=None,
    silent=False,
    singledoc=None,
):
    """Inserts an IFC document in a FreeCAD document"""

    importlib.reload(ifc_tools)  # useful as long as we are in early dev times
    strategy, shapemode, switchwb = get_options(strategy, shapemode, switchwb, silent)
    if strategy is None:
        print("Aborted.")
        return
    stime = time.time()
    document = FreeCAD.getDocument(docname)
    if singledoc is None:
        singledoc = params.GetBool("SingleDoc", False)
    if singledoc:
        prj_obj = ifc_tools.convert_document(document, filename, shapemode, strategy)
    else:
        prj_obj = ifc_tools.create_document_object(
            document, filename, shapemode, strategy
        )
    if params.GetBool("LoadOrphans", False):
        ifc_tools.load_orphans(prj_obj)
    if not silent and params.GetBool("LoadMaterials", False):
        ifc_materials.load_materials(prj_obj)
    if params.GetBool("LoadLayers", False):
        ifc_layers.load_layers(prj_obj)
    if params.GetBool("LoadPsets", False):
        ifc_psets.load_psets(prj_obj)
    document.recompute()
    # print a reference to the IFC file on the console
    if FreeCAD.GuiUp:
        if isinstance(prj_obj, FreeCAD.DocumentObject):
            pstr = "FreeCAD.getDocument('{}').{}.Proxy.ifcfile"
            pstr = pstr.format(prj_obj.Document.Name, prj_obj.Name)
        else:
            pstr = "FreeCAD.getDocument('{}').Proxy.ifcfile"
            pstr = pstr.format(prj_obj.Name)
        pstr = "ifcfile = " + pstr
        pstr += " # warning: make sure you know what you are doing when using this!"
        FreeCADGui.doCommand(pstr)
    endtime = "%02d:%02d" % (divmod(round(time.time() - stime, 1), 60))
    fsize = round(os.path.getsize(filename) / 1048576, 2)
    print("Imported", os.path.basename(filename), "(", fsize, "Mb ) in", endtime)
    if FreeCAD.GuiUp and switchwb:
        from StartPage import StartPage

        StartPage.postStart()
    return document


def get_options(
    strategy=None, shapemode=None, switchwb=None, silent=False, orphans=None
):
    """Shows a dialog to get import options

    shapemode: 0 = full shape
               1 = coin only
               2 = no representation
    strategy:  0 = only root object
               1 = only bbuilding structure,
               2 = all children
    """

    orphans = params.GetBool("LoadOrphans", False)
    psets = params.GetBool("LoadPsets", False)
    materials = params.GetBool("LoadMaterials", False)
    layers = params.GetBool("LoadLayers", False)
    singledoc = params.GetBool("SingleDoc", False)
    if strategy is None:
        strategy = params.GetInt("ImportStrategy", 0)
    if shapemode is None:
        shapemode = params.GetInt("ShapeMode", 0)
    if switchwb is None:
        switchwb = params.GetBool("SwitchWB", True)
    if silent:
        return strategy, shapemode, switchwb
    ask = params.GetBool("AskAgain", True)
    if ask and FreeCAD.GuiUp:
        import FreeCADGui
        from PySide import QtGui

        dlg = FreeCADGui.PySideUic.loadUi(
            os.path.join(os.path.dirname(__file__), "ui", "dialogImport.ui")
        )
        dlg.checkSwitchWB.hide()  # TODO see what to do with this...
        dlg.comboStrategy.setCurrentIndex(strategy)
        dlg.comboShapeMode.setCurrentIndex(shapemode)
        dlg.checkSwitchWB.setChecked(switchwb)
        dlg.checkAskAgain.setChecked(ask)
        dlg.checkLoadOrphans.setChecked(orphans)
        dlg.checkLoadPsets.setChecked(psets)
        dlg.checkLoadMaterials.setChecked(materials)
        dlg.checkLoadLayers.setChecked(layers)
        dlg.comboSingleDoc.setCurrentIndex(1 - int(singledoc))
        result = dlg.exec_()
        if not result:
            return None, None, None
        strategy = dlg.comboStrategy.currentIndex()
        shapemode = dlg.comboShapeMode.currentIndex()
        switchwb = dlg.checkSwitchWB.isChecked()
        ask = dlg.checkAskAgain.isChecked()
        orphans = dlg.checkLoadOrphans.isChecked()
        psets = dlg.checkLoadPsets.isChecked()
        materials = dlg.checkLoadMaterials.isChecked()
        layers = dlg.checkLoadLayers.isChecked()
        singledoc = dlg.comboSingleDoc.currentIndex()
        params.SetInt("ImportStrategy", strategy)
        params.SetInt("ShapeMode", shapemode)
        params.SetBool("SwitchWB", switchwb)
        params.SetBool("AskAgain", ask)
        params.SetBool("LoadOrphans", orphans)
        params.SetBool("LoadPsets", psets)
        params.SetBool("LoadMaterials", materials)
        params.SetBool("LoadLayers", layers)
        params.SetBool("SingleDoc", bool(1 - singledoc))
    return strategy, shapemode, switchwb


def get_project_type(silent=False):
    """Gets the type of project to make"""

    ask = params.GetBool("ProjectAskAgain", True)
    ptype = params.GetBool("ProjectFull", False)
    if silent:
        return ptype
    if ask and FreeCAD.GuiUp:
        import FreeCADGui
        from PySide import QtGui

        dlg = FreeCADGui.PySideUic.loadUi(
            os.path.join(os.path.dirname(__file__), "ui", "dialogCreateProject.ui")
        )
        result = dlg.exec_()
        ask = not (dlg.checkBox.isChecked())
        ptype = bool(result)
        params.SetBool("ProjectAskAgain", ask)
        params.SetBool("ProjectFull", ptype)
    return ptype
