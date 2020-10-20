# -*- coding: utf-8 -*-

"""
/***************************************************************************
 PostTelemac
                                 A QGIS plugin
 Post Traitment or Telemac
                              -------------------
        begin                : 2015-07-07
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Artelia
        email                : patrice.Verchere@arteliagroup.com
 ***************************************************************************/
 
 ***************************************************************************/
 get Image class
 Generate a Qimage from selafin file to be displayed in map canvas 
 with tht draw method of posttelemacpluginlayer
 
Versions :
0.0 : debut

 ***************************************************************************/
"""

from qgis.PyQt import QtGui, QtCore
import numpy as np
import qgis


class MeshLayerRubberband(QtCore.QObject):
    def __init__(self, meshlayer):
        QtCore.QObject.__init__(self)
        self.meshlayer = meshlayer

        self.rubberbandelem = None
        self.rubberbandfacenode = None
        self.rubberbandface = None

        self.pointcolor = QtGui.QColor(QtCore.Qt.red)
        self.elemcolor = QtGui.QColor(QtCore.Qt.blue)
        self.facecolor = QtGui.QColor(QtCore.Qt.darkGreen)

    def drawFromNum(self, num, type):
        if type == 0:
            geomtemp = self.meshlayer.hydrauparser.getElemXYFromNumElem(num)[0]
            elemqgisgeom = qgis.core.QgsGeometry.fromPolygon(
                [[self.meshlayer.xform.transform(qgis.core.QgsPointXY(coord[0], coord[1])) for coord in geomtemp]]
            )
            if not self.rubberbandelem:
                self.createRubberbandElem()
            self.rubberbandelem.reset(qgis.core.QgsWkbTypes.PolygonGeometry)
            self.rubberbandelem.addGeometry(elemqgisgeom, None)

        if type == 1:
            x, y = self.meshlayer.hydrauparser.getFaceNodeXYFromNumPoint(num)[0]
            qgspointfromcanvas = self.meshlayer.xform.transform(qgis.core.QgsPointXY(x, y))
            if not self.rubberbandfacenode:
                self.createRubberbandFaceNode()
            try:
                self.rubberbandfacenode.reset(qgis.core.QGis.Point)
            except:
                self.rubberbandfacenode.reset(qgis.core.QgsWkbTypes.PointGeometry)

            self.rubberbandfacenode.addPoint(qgspointfromcanvas)

        if type == 2:
            geomtemp = self.meshlayer.hydrauparser.getFaceXYFromNumFace(num)[0]
            faceqgisgeom = qgis.core.QgsGeometry.fromPolyline(
                [self.meshlayer.xform.transform(qgis.core.QgsPointXY(coord[0], coord[1])) for coord in geomtemp]
            )

            if not self.rubberbandface:
                self.createRubberbandFace()
            self.rubberbandface.reset(qgis.core.QgsWkbTypes.LineGeometry)
            self.rubberbandface.addGeometry(faceqgisgeom, None)

    def reset(self):
        if self.rubberbandelem != None:
            self.rubberbandelem.reset(qgis.core.QgsWkbTypes.PolygonGeometry)
        if self.rubberbandfacenode != None:
            self.rubberbandfacenode.reset(qgis.core.QgsWkbTypes.PointGeometry)
        if self.rubberbandface != None:
            self.rubberbandface.reset(qgis.core.QgsWkbTypes.LineGeometry)

    def createRubberbandFaceNode(self):
        self.rubberbandfacenode = qgis.gui.QgsRubberBand(self.meshlayer.canvas, qgis.core.QgsWkbTypes.PointGeometry)
        self.rubberbandfacenode.setWidth(2)
        self.rubberbandfacenode.setColor(self.pointcolor)

    def createRubberbandElem(self):
        self.rubberbandelem = qgis.gui.QgsRubberBand(self.meshlayer.canvas, qgis.core.QgsWkbTypes.PolygonGeometry)
        self.rubberbandelem.setWidth(2)
        color = QtGui.QColor(self.elemcolor)
        color.setAlpha(100)
        self.rubberbandelem.setColor(color)

    def createRubberbandFace(self):
        self.rubberbandface = qgis.gui.QgsRubberBand(self.meshlayer.canvas, qgis.core.QgsWkbTypes.LineGeometry)
        self.rubberbandface.setWidth(5)
        self.rubberbandface.setColor(self.facecolor)
