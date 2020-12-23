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

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QObject, QThread, pyqtSignal

from qgis.core import QgsApplication, QgsProject
from qgis.utils import iface

from .meshlayer_abstract_tool import *
from ..meshlayerparsers.libtelemac.selafin_io_pp import ppSELAFIN

import sys
import numpy as np
import math

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "AleaTool.ui"))


class AleaTool(AbstractMeshLayerTool, FORM_CLASS):

    NAME = "ALEATOOL"
    SOFTWARE = ["TELEMAC"]

    def __init__(self, meshlayer, dialog):
        AbstractMeshLayerTool.__init__(self, meshlayer, dialog)
        self.pushButton_alea_compute.clicked.connect(self.calculAlea)

    def initTool(self):
        self.setupUi(self)
        self.iconpath = os.path.join(os.path.dirname(__file__), "..", "icons", "tools", "alea.jpg")

    def onActivation(self):
        maxiter = self.meshlayer.hydrauparser.itertimecount
        self.spinBox_alea_start.setMaximum(maxiter)
        self.spinBox_alea_end.setMaximum(maxiter)
        self.spinBox_alea_end.setValue(maxiter)
        
        self.methodeCalculChanged(self.comboBox_alea_calcul.currentIndex())
        self.critereChanged(self.comboBox_alea_Vmontee.currentIndex())

        try:
            self.comboBox_alea_calcul.currentIndexChanged.disconnect()
        except:
            pass
        try:
            self.comboBox_alea_Vmontee.currentIndexChanged.disconnect()
        except:
            pass
        self.comboBox_alea_calcul.currentIndexChanged.connect(self.methodeCalculChanged)
        self.comboBox_alea_Vmontee.currentIndexChanged.connect(self.critereChanged)

    def onDesactivation(self):
        try:
            self.comboBox_alea_calcul.currentIndexChanged.disconnect()
        except:
            pass
        try:
            self.comboBox_alea_Vmontee.currentIndexChanged.disconnect()
        except:
            pass

    def calculAlea(self):
        if (
            self.meshlayer.hydrauparser.parametreh == None
            or self.meshlayer.hydrauparser.parametrevx == None
            or self.meshlayer.hydrauparser.parametrevy == None
        ):
            self.propertiesdialog.errorMessage(
                "Le fichier n'a pas les variables nécessaires (HAUTEUR ou VITESSE X ou VITESSE Y)"
            )
            return

        self.initclass = initRunAlea()
        self.initclass.status.connect(self.propertiesdialog.logMessage)
        self.initclass.finished1.connect(self.chargerSelafin)
        self.initclass.start(self.meshlayer, self)
        
        self.propertiesdialog.normalMessage("Méthode de calcul choisie : {}".format(self.comboBox_alea_calcul.currentText()))
        self.propertiesdialog.normalMessage("Le calcul de l'aléa a débuté... - Progression onglet Log")

    def methodeCalculChanged(self, index):
        self.stackedWidget.setCurrentIndex(index)
        if index == 0:
            self.Haleamin = self.doubleSpinBox_aleaclassique_Haleamin
        elif index == 2:
            self.Haleamin = self.doubleSpinBox_venues_Haleamin

    def critereChanged(self, index):
        self.doubleSpinBox_alea_H1.setEnabled(index)

    def chargerSelafin(self, path):
        if path and self.checkBox_alea_loadSLF.isChecked():
            if iface is not None:
                slf = QgsApplication.instance().pluginLayerRegistry().pluginLayerType("selafin_viewer").createLayer()
                slf.setRealCrs(self.meshlayer.crs())
                slf.load_selafin(path, "TELEMAC")
                QgsProject.instance().addMapLayer(slf)


class runAlea(QObject):
    def __init__(self, selafinlayer, tool):
        QObject.__init__(self)
        self.selafinlayer = selafinlayer
        self.tool = tool
        self.methodeCalcul = self.tool.comboBox_alea_calcul.currentIndex()
        self.critere1 = self.tool.doubleSpinBox_alea_H1.value() if self.tool.doubleSpinBox_alea_H1.isEnabled() else -1
        self.critere2 = self.tool.doubleSpinBox_alea_H2.value()
        self.critereHAlea = self.tool.Haleamin.value()
        self.intensite = True
        self.direction = True
        self.submersion = self.tool.doubleSpinBox_alea_H2.value()
        self.duree = self.tool.doubleSpinBox_alea_H2.value()
        self.name_res = self.selafinlayer.hydraufilepath
        self.name_res_out = self.selafinlayer.hydraufilepath.rsplit(".", maxsplit=1)[0] + "_Alea_Max.res"

    def run(self):
        """
        Fonction permettant de recuperer la valeur max d'un resultat (avec en plus
        l'ecriture de l'intensite et de la direction)
        Parametre d'entree:
        - name_res (str) : nom du fichier resultat telemac
        - name_res_out (str) : nom du fichier a creer (au format Serafin)
        - intensite (bool) : si vrai alors on recalcule l'intensite max
        - direction (bool) : si vrai alors on recalcule la direction des intensites max
        Parametre de sortie:
        - aucun
        fonctions appelees:
        - aucunes

        """

        ## Creation de la variable au format Serafin
        resIn = ppSELAFIN(self.name_res)
        resOut = ppSELAFIN(self.name_res_out)

        ## Lecture de l'entete du fichier d'entree
        resIn.readHeader()

        ## Recuperation de tous les temps
        resIn.readTimes()

        ## On copie toutes les variables de l'entete du fichier d'entree dans
        ## les variables du fichier de sortie
        title = resIn.getTitle()
        times = resIn.getTimes()
        variables = resIn.getVarNames()
        units = resIn.getVarUnits()
        float_type, float_size = resIn.getPrecision()

        # number of variables
        NVAR = len(variables)

        # gets some mesh properties from the *.slf file
        IPARAM = resIn.getIPARAM()
        NELEM, NPOIN, NDP, IKLE, IPOBO, x, y = resIn.getMesh()

        resIn.close()

        ## On ajoute les deux nouvelles variables, pour cela il faut modifier la variable
        ## nbvar et nomvar (le nom de la variable ne doit pas depasser 72 caracteres

        for param in self.selafinlayer.hydrauparser.parametres:
            if param[4]:  # for virtual parameter
                variables.append(str(param[1]))
                units.append("")

        variables.append("VIT DE MONTEE")
        units.append("CM/H")
        variables.append("ALEA")
        units.append("")
        if self.intensite:
            variables.append("intensite")
            units.append("M/S")
        if self.direction:
            variables.append("direction")
            units.append("")
        if self.submersion > -1:
            variables.append("submersion")
            units.append("S")
        if self.duree > -1:
            variables.append("duree")
            units.append("S")

        ## Ecriture de l'entete dans le fichier de sortie
        resOut.setPrecision(float_type, float_size)
        resOut.setTitle(title)
        resOut.setVarNames(variables)
        resOut.setVarUnits(units)
        resOut.setIPARAM(IPARAM)
        resOut.setMesh(NELEM, NPOIN, NDP, IKLE, IPOBO, x, y)
        resOut.writeHeader()

        ## Boucle sur tous les temps et récuperation des variables
        itermin = self.tool.spinBox_alea_start.value()
        iterfin = self.tool.spinBox_alea_end.value()

        initialisation = True
        for timeslf in self.selafinlayer.hydrauparser.getTimes()[itermin:iterfin]:
            num_time = np.where(self.selafinlayer.hydrauparser.getTimes() == timeslf)[0][0]

            if (num_time - itermin) % 10 == 0:
                self.status.emit("Calcul de l'aléa - temps " + str(timeslf))

            if initialisation:  ## Ce else permet de d'initialiser notre variable max avec le premier pas de temps
                var_max = self.selafinlayer.hydrauparser.getValues(num_time)

                var_alea = np.array([0.0] * self.selafinlayer.hydrauparser.facesnodescount)
                var_alea_max = np.array([0.0] * self.selafinlayer.hydrauparser.facesnodescount)

                var_Vmontee = np.array([0.0] * self.selafinlayer.hydrauparser.facesnodescount)

                var_Vm1 = np.array([np.nan] * self.selafinlayer.hydrauparser.facesnodescount)
                if self.critere1 > -1:
                    pos_Vm1 = np.where(var_max[self.selafinlayer.hydrauparser.parametreh] >= self.critere1)[0]
                    var_Vm1[pos_Vm1] = timeslf

                var_Vm2 = np.array([np.nan] * self.selafinlayer.hydrauparser.facesnodescount)
                pos_Vm2 = np.where(var_max[self.selafinlayer.hydrauparser.parametreh] >= self.critere2)[0]
                var_Vm2[pos_Vm2] = timeslf

                if self.submersion > -1:
                    var_sub = np.array([np.nan] * self.selafinlayer.hydrauparser.facesnodescount)
                    pos_sub = np.where(var_max[self.selafinlayer.hydrauparser.parametreh] >= self.submersion)[0]
                    var_sub[pos_sub] = timeslf

                if self.duree > -1:
                    var_dur = np.array([0.0] * self.selafinlayer.hydrauparser.facesnodescount)
                    previoustime = timeslf

                initialisation = False
            else:
                var = self.selafinlayer.hydrauparser.getValues(num_time)

                for num_var, val_var in enumerate(var):
                    if (
                        self.submersion > -1 or self.duree > -1
                    ) and num_var == self.selafinlayer.hydrauparser.parametreh:
                        if self.critere1 > -1:
                            pos_Vm1 = np.where(var[num_var] >= self.critere1)[0]
                            pos_Vm1_prec = np.where(np.isnan(var_Vm1))[0]  # on cherche les valeurs encore a nan
                            goodNum_Vm1 = np.intersect1d(pos_Vm1, pos_Vm1_prec)  # on intersecte les deux
                            var_Vm1[goodNum_Vm1] = timeslf
                        else:
                            pos_T_Hmax = np.where(var[num_var] > var_max[num_var])[0]
                            var_Vm1[pos_T_Hmax] = timeslf

                        pos_Vm2 = np.where(var[num_var] >= self.critere2)[0]
                        pos_Vm2_prec = np.where(np.isnan(var_Vm2))[0]  # on cherche les valeurs encore a nan
                        goodNum_Vm2 = np.intersect1d(pos_Vm2, pos_Vm2_prec)  # on intersecte les deux
                        var_Vm2[goodNum_Vm2] = timeslf

                        if self.duree > -1:
                            pos_dur = np.where(var[num_var] >= self.duree)[0]
                            var_dur[pos_dur] += timeslf - previoustime
                            previoustime = timeslf

                        if self.submersion > -1:
                            pos_sub = np.where(var[num_var] >= self.submersion)[0]
                            possubpreced = np.where(np.isnan(var_sub))[0]  # on cherche les valeurs encore a nan
                            goodNum = np.intersect1d(pos_sub, possubpreced)  # on intersecte les deux
                            var_sub[goodNum] = timeslf

                    pos_max = np.where(var[num_var] > var_max[num_var])[0]
                    var_max[num_var][pos_max] = val_var[pos_max]

                ## Maintenant on s'occuppe du cas particulier des vitesses
                vit = np.power(
                    np.power(var[self.selafinlayer.hydrauparser.parametrevx], 2)
                    + np.power(var[self.selafinlayer.hydrauparser.parametrevy], 2),
                    0.5,
                )
                vit_max = np.power(
                    np.power(var_max[self.selafinlayer.hydrauparser.parametrevx], 2)
                    + np.power(var_max[self.selafinlayer.hydrauparser.parametrevy], 2),
                    0.5,
                )

                pos_vmax = np.where(vit > vit_max)[0]
                var_max[self.selafinlayer.hydrauparser.parametrevx][pos_vmax] = var[
                    self.selafinlayer.hydrauparser.parametrevx
                ][pos_vmax]
                var_max[self.selafinlayer.hydrauparser.parametrevy][pos_vmax] = var[
                    self.selafinlayer.hydrauparser.parametrevy
                ][pos_vmax]

                ## Aléa
                if self.methodeCalcul == 0:  ## Méthode classique
                    var_alea_max = self.calculAleaClassique(
                        var_alea,
                        var_alea_max,
                        self.critereHAlea,
                        var_max[self.selafinlayer.hydrauparser.parametreh],
                        vit,
                    )
                elif self.methodeCalcul == 1:  ## Méthode PPRI 2019
                    continue  ## Pas implémentée pour le moment
                elif self.methodeCalcul == 2:  ## Calcul des venues d'eau dangereuse pour EDD
                    var_alea_max = self.calculVenuesEauDangereuses(
                        var_alea,
                        var_alea_max,
                        self.critereHAlea,
                        var_max[self.selafinlayer.hydrauparser.parametreh],
                        vit,
                    )

        if self.critere1 > -1:
            var_Vmontee = (self.critere1 - self.critere2) / (var_Vm1 - var_Vm2) * 360000
            # Conversion m/s en cm/min
        else:
            var_Vmontee = (
                (var_max[self.selafinlayer.hydrauparser.parametreh] - self.critere2) / (var_Vm1 - var_Vm2) * 360000
            )
            # Conversion m/s en cm/min

        np.place(
            var_Vmontee,
            np.logical_or(np.logical_or(np.isnan(var_Vmontee), np.isinf(var_Vmontee)), np.less_equal(var_Vmontee, 0)),
            0.0,
        )

        var_max = np.vstack((var_max, var_Vmontee))
        var_max = np.vstack((var_max, var_alea_max))

        ## Une fois sortie de la boucle le max a ete calculer
        ## On recalcule les directions et les intensites sur le dernier pas de temps

        if self.intensite or self.direction:
            u = var_max[self.selafinlayer.hydrauparser.parametrevx]
            v = var_max[self.selafinlayer.hydrauparser.parametrevy]
            if self.intensite:
                val_intensite = np.power(np.power(u, 2) + np.power(v, 2), 0.5)
                var_max = np.vstack((var_max, val_intensite))

            if self.direction:
                np.seterr(divide="ignore", invalid="ignore")
                val_direction = (
                    np.arctan2(u, v) * 360.0 / (2.0 * math.pi)
                    + np.minimum(np.arctan2(u, v), 0.0) / np.arctan2(u, v) * 360.0
                )
                np.seterr(divide="warn", invalid="warn")
                ## Dans la creation des directions il peut y avoir des divisions par 0
                ## Ceci entraine la creation de nan (not a number)
                ## On va alors remplacer tous ces nan par 0.
                np.place(val_direction, np.isnan(val_direction), 0.0)
                var_max = np.vstack((var_max, val_direction))

        if self.submersion > -1 and self.selafinlayer.hydrauparser.parametreh != None:
            var_sub = np.nan_to_num(var_sub)
            var_max = np.vstack((var_max, var_sub))
        if self.duree > -1 and self.selafinlayer.hydrauparser.parametreh != None:
            var_max = np.vstack((var_max, var_dur))

        ## Ecriture des valeurs max dans le fichier de sortie (on met un temps à 0 dans le fichier)
        resOut.writeVariables(0.0, var_max)

        resOut.close()

        self.finished.emit(self.name_res_out)

    def calculAleaClassique(self, var_alea, var_alea_max, critereHAlea, h, v):
        posFaible = np.where(
            np.logical_and(
                np.logical_and(
                    np.greater(h, critereHAlea),
                    np.greater(v, critereHAlea),
                ),
                np.logical_and(np.less(h, 0.5), np.less(v, 0.5)),
            )
        )[0]
        posModere = np.where(
            np.logical_and(
                np.logical_and(
                    np.greater(h, critereHAlea),
                    np.greater(v, critereHAlea),
                ),
                np.logical_or(
                    np.logical_and(
                        np.less(h, 1),
                        np.logical_and(np.greater_equal(v, 0.5), np.less(v, 1)),
                    ),
                    np.logical_and(
                        np.less(v, 0.5),
                        np.logical_and(
                            np.greater_equal(h, 0.5),
                            np.less(h, 1),
                        ),
                    ),
                ),
            )
        )[0]
        posFort = np.where(
            np.logical_or(
                np.greater_equal(h, 1),
                np.greater_equal(v, 1),
            )
        )[0]

        var_alea[posFaible] = 1
        var_alea[posModere] = 2
        var_alea[posFort] = 3

        pos_aleaMax = np.where(var_alea > var_alea_max)[0]
        var_alea_max[pos_aleaMax] = var_alea[pos_aleaMax]

        return var_alea_max

    def calculVenuesEauDangereuses(self, var_alea, var_alea_max, critereHAlea, h, v):
        posNonDanger = np.where(
            np.logical_and(
                np.logical_and(
                    np.greater(h, critereHAlea),
                    np.greater(v, critereHAlea),
                ),
                np.logical_and(np.less(h, 0.5), np.less(v, 0.5)),
            )
        )[0]
        posMDanger = np.where(
            np.logical_and(
                np.logical_and(
                    np.greater(h, critereHAlea),
                    np.greater(v, critereHAlea),
                ),
                np.logical_and(
                    np.logical_and(
                        np.greater_equal(h, 0.5),
                        np.less(h, 1),
                    ),
                    np.less(v, 0.5),
                ),
            )
        )[0]
        posDanger = np.where(
            np.logical_or(
                np.logical_and(
                    np.less(h, 2),
                    np.greater_equal(h, 1),
                ),
                np.logical_and(
                    np.less(v, 2),
                    np.greater_equal(v, 0.5),
                ),
            ),
        )[0]
        posPartDanger = np.where(
            np.logical_or(
                np.greater_equal(h, 2),
                np.greater_equal(v, 2),
            )
        )[0]

        var_alea[posNonDanger] = 1
        var_alea[posMDanger] = 2
        var_alea[posDanger] = 3
        var_alea[posPartDanger] = 4

        pos_aleaMax = np.where(var_alea > var_alea_max)[0]
        var_alea_max[pos_aleaMax] = var_alea[pos_aleaMax]

        return var_alea_max

    status = pyqtSignal(str)
    finished = pyqtSignal(str)


class initRunAlea(QObject):
    def __init__(self):
        QObject.__init__(self)
        self.thread = QThread()
        self.worker = None

    def start(self, selafinlayer, tool):
        # Launch worker
        self.worker = runAlea(selafinlayer, tool)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.status.connect(self.writeOutput)
        self.worker.finished.connect(self.workerFinished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self.thread.quit)
        self.thread.start()

    def writeOutput(self, str1):
        self.status.emit(str(str1))

    def workerFinished(self, str1):
        self.finished1.emit(str1)

    status = pyqtSignal(str)
    finished1 = pyqtSignal(str)
