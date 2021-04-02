"""
An application lives on each node
"""
from __future__ import absolute_import
from __future__ import division

# =========================== imports =========================================

from builtins import range
from builtins import object
from abc import abstractmethod
import random
import os
import copy
import numpy as np
import sys
import collections 
# Mote sub-modules

# Simulator-wide modules
import SimEngine
#from SimEngine import Connectivity
#from ..Connectivity import ConnectivityMatrixBase as connectivity

from . import MoteDefines as d
from .. import SimSettings
from . import radio as r
from . import RoutingPerm as rou
from ..Connectivity import *
# =========================== defines =========================================

# =========================== helpers =========================================

# =========================== body ============================================

def App(mote):
    """factory method for application
    """
    settings = SimEngine.SimSettings.SimSettings()

    # use mote.id to determine whether it is the root or not instead of using
    # mote.dagRoot because mote.dagRoot is not initialized when application is
    # instantiated
   
    if mote.id == 0:
        return AppRoot(mote)
    else:
        return globals()[settings.app](mote)
    

    
class AppBase(object):
    """Base class for Applications.
    """
    #global li 

    def __init__(self, mote, sim_engine=None):

        # store params
        self.mote       = mote
        self.Packet_number = 0
       
        # singletons (quicker access, instead of recreating every time)
        self.engine     = SimEngine.SimEngine.SimEngine()
        self.settings   = SimEngine.SimSettings.SimSettings()
        self.log        = SimEngine.SimLog.SimLog().log
        #global connectivity   
        # local variables
        global li
        self.appcounter      = 0
        self.k               = 0
        self.liste           = []
        self.p               = random.randint(1, 9)
        self.max             = 34
        self.cale = 0
        
        
        self.settings = SimSettings.SimSettings()
        #self.engine   = sim_engine

        #self.liste=connectivity.motelist()

       
    def listeMote(self):
        # local variables 
        self.x = [mote.id for mote in self.engine.motes]
        li = self.x
        return li 
   
    #======================== public ==========================================

    @abstractmethod
    def startSendingData(self):
        """Starts the application process.

        Typically, this methods schedules an event to send a packet to the root.
        """
        raise NotImplementedError()  # abstractmethod
       


    @abstractmethod
    def  motelist(self):
        pass  
    
    def partitionnement(self):
	pass

    def envoieDesPaquets(self):
        pass

    def recvPacket(self, packet):
        """Receive a packet destined to this application
        """
        # log and mote stats
        self.log(
            SimEngine.SimLog.LOG_APP_RX,
            {
                u'_mote_id': self.mote.id,
                u'packet'  : packet
            }
        )

    #======================== private ==========================================

    def _generate_packet(
            self,
            dstIp,
            packet_type,
            packet_length,
        ):

        # create data packet
        dataPacket = {
            u'type':              packet_type,
            u'net': {
                u'srcIp':         self.mote.get_ipv6_global_addr(),
                u'dstIp':         dstIp,
                u'packet_length': packet_length
            },
            u'app': {
                u'appcounter':    self.appcounter,
                u'timestamp':     self.engine.getAsn()
            }

        }

        # update appcounter
        self.appcounter += 1

        return dataPacket

    def _send_packet(self, dstIp, packet_length):

        # abort if I'm not ready to send DATA yet
        if self.mote.clear_to_send_EBs_DATA()==False:
            return

        # create
        packet = self._generate_packet(
            dstIp          = dstIp,
            packet_type    = d.PKT_TYPE_DATA,
            packet_length  = packet_length
        )

        # log
        self.log(
            SimEngine.SimLog.LOG_APP_TX,
            {
                u'_mote_id':       self.mote.id,
                u'packet':         packet,
            }
        )

        # send
        self.mote.sixlowpan.sendPacket(packet)

class AppRoot(AppBase):
    """Handle application packets from motes
    """
    
    # the payload length of application ACK
    APP_PK_LENGTH = 10
    global li 

    def __init__(self, mote):
        super(AppRoot, self).__init__(mote)


    #======================== public ==========================================

    def startSendingData(self):
        # nothing to schedule
        pass

    def recvPacket(self, packet):
        assert self.mote.dagRoot
        #self.mote.dagRoot
        

        # log and update mote stats
        self.log(
            SimEngine.SimLog.LOG_APP_RX,
            {
                u'_mote_id': self.mote.id,
                u'packet'  : packet
            }
        )

    def motelist(self):
        pass 

    def NombreTotalDePacket(self):
        pass
    
    def envoieDesPaquets(self):
        #tracer = open("Dossier/tracer.csv","a")
        #resumer = open("Dossier/resumer.csv","a")
        print("Envoie des paquets DodagID")
        #tracer.write("nodeId,status,recEnergy,transEnergy,nbTrans,nbRec\n\n")
        #resumer.write("nodeId,status,recEnergy,transEnergy,nbTrans,nbRec\n\n")

        #tracer.close()
        #resumer.close()
    #======================== private ==========================================

    def _send_ack(self, destination, packet_length=None):

        if packet_length is None:
            packet_length = self.APP_PK_LENGTH

        self._send_packet(
            dstIp          = destination,
            packet_length  = packet_length
        )

    def resume(self):
       pass

    def receive(self):
       pass
class AppPeriodic(AppBase):

    """Send a packet periodically

    Intervals are distributed uniformly between (pkPeriod-pkPeriodVar)
    and (pkPeriod+pkPeriodVar).

    The first timing to send a packet is randomly chosen between [next
    asn, (next asn + pkPeriod)].
    """

    def __init__(self, mote, **kwargs):
        super(AppPeriodic, self).__init__(mote)
        self.sending_first_packet = True

    #======================== public ==========================================

    def startSendingData(self):
        if self.sending_first_packet:
            self._schedule_transmission()

    #======================== public ==========================================

    def _schedule_transmission(self):
        assert self.settings.app_pkPeriod >= 0
        if self.settings.app_pkPeriod == 0:
            return

        if self.sending_first_packet:
            # compute initial time within the range of [next asn, next asn+pkPeriod]
            delay = self.settings.tsch_slotDuration + (self.settings.app_pkPeriod * random.random())
            self.sending_first_packet = False
        else:
            # compute random delay
            assert self.settings.app_pkPeriodVar < 1
            delay = self.settings.app_pkPeriod * (1 + random.uniform(-self.settings.app_pkPeriodVar, self.settings.app_pkPeriodVar))

        # schedule
        self.engine.scheduleIn(
            delay           = delay,
            cb              = self._send_a_single_packet,
            uniqueTag       = (
                u'AppPeriodic',
                u'scheduled_by_{0}'.format(self.mote.id)
            ),
            intraSlotOrder  = d.INTRASLOTORDER_ADMINTASKS,
        )

    def _send_a_single_packet(self):
        if self.mote.rpl.dodagId == None:
            # it seems we left the dodag; stop the transmission
            self.sending_first_packet = True
            return

        self._send_packet(
            dstIp          = self.mote.rpl.dodagId,
            packet_length  = self.settings.app_pkLength
        )
        # schedule the next transmission
        self._schedule_transmission()
    

class AppRoupe(AppBase):

    Identifiant = 0
    Packet_number = 0

    Energie_Transmission = 3
    Energie_Reception = 2
    Energie_Idle = 1
 
    transmit = 0 
    nbTrans = 0 
    nbRecu = 0
    recu   = 0
    nbPacketSend = 0
    nbPakect = 0
    nbPakectRec = 0
    nbTours = 0

    global trans 
    trans = 0 
    #print(trans)
 
    global liste 
    liste = []

    global liste_memoire
    liste_memoire = []

    global dataObjet
    dataObjet = []
    
    global Liste_Energy
    Liste_Energy = []

    global data
    data = collections.defaultdict(list)

    global liste_Agent
    liste_Agent = []

    global TableDiffusion 
    #TableDiffusion = collections.defaultdict(list)
    TableDiffusion = []

    global group
    group = collections.defaultdict(list)

    global partition
    partition = collections.defaultdict(list)

    global dataDonne
    dataDonne = collections.defaultdict(list)

    global ResumE
    ResumE = collections.defaultdict(list)
    
    global adresse
    adresse = ""
    
    global donne
    
    global calculValeur
    calculValeur = []

    global adresseOfEachObjet
    adresseOfEachObjet = collections.defaultdict(list)
    

    def __init__(self, mote, **kwargs):
        super(AppRoupe, self).__init__(mote)
        self.engine  = SimEngine.SimEngine.SimEngine()
        self.sending_first_packet = True
        self.Packet_number = 0
     
    def listeMote(self):
        # local variables 
        self.x = [mote.id for mote in engine.motes]
        li = self.x
        return li 


    def listeMemoire(self):
        # local variables 
        for mote in engine.motes:
            self.mem = self.mem + self.Packet_number
        return self.mem
  
        
       
    #======================== public ==========================================

    def startSendingData(self):
        if self.sending_first_packet:
            self._schedule_transmission()

    #======================== public ==========================================

    def _schedule_transmission(self):
        i = 0
        global Packet_number    
        Packet_number = 0

        while Packet_number < self.p :
            assert self.settings.app_pkPeriod >= 0
            if self.settings.app_pkPeriod == 0:
                return

            if self.sending_first_packet:
                # compute initial time within the range of [next asn, next asn+pkPeriod]
                delay = self.settings.tsch_slotDuration + (self.settings.app_pkPeriod * random.random())
                self.sending_first_packet = False
            else:
                # compute random delay
                assert self.settings.app_pkPeriodVar < 1
                delay = self.settings.app_pkPeriod * (1 + random.uniform(-self.settings.app_pkPeriodVar, self.settings.app_pkPeriodVar))

            # schedule
            self.engine.scheduleIn(
                delay           = delay,
                cb              = self._send_a_single_packet,
                uniqueTag       = (
                    u'AppRoupe',
                    u'scheduled_by_{0}'.format(self.mote.id)
                ),
                intraSlotOrder  = d.INTRASLOTORDER_ADMINTASKS,
            )
            i=i+1
            Packet_number = i
            
            
    def _send_a_single_packet(self):
        #trace = open("Dossier/FichierDeTrace.txt","a")
        #tracer = open("Dossier/tracer.csv","a")
        
        i=0
        inc=0
        nbre = 0
        b = False 
        #trace.write("table ::: \t:"+ str(dataDonne) +" -\n")

        NombreObjet = len(self.engine.motes) - 1


        #while nbre < NombreObjet:
        if self.mote.id !=0:
            while nbre < NombreObjet:       #On parcour le nombre d'objet
                k=nbre+1

                if self.mote.id == k:
                    donne = dataDonne[nbre] #dataDonne contient les adresses ip a diffuse
                    self.nbPacketSend = len(donne)
                    taille = len(donne)

                    while inc < taille:
                        #trace.write("\n SEND PACKET \t \n" )
                        Liste_Energy[nbre] = int(Liste_Energy[nbre]) - self.Energie_Transmission
                        self.transmit = self.transmit + self.Energie_Transmission

                        self.nbTours = self.nbTours + 1  

                        self.nbPakect = self.nbPakect + 1
                        self._send_packet(
                            dstIp          = donne[inc],
                            packet_length  = self.settings.app_pkLength
                        )
                         
                        #trace.write("single packet sent by: " + str(self.mote.get_ipv6_link_local_addr())+" To "+str(donne[inc])) 
                        inc=inc+1
                    
                    #tracer.write("nodeId,status,recEnergy,transEnergy,nbTrans,nbRec\n\n")
                    #tracer.write(""+str(self.mote.id)+",trans," + str(Liste_Energy[nbre]) + "," + str(Liste_Energy[nbre]) +"," + str(taille)+","+"0" + "\n") #a traiter
                    b = True
                    #tracer.write(""+str(self.mote.id)+",trans," +  str(self.recu) + "," + str(self.transmit) +"," + str(self.nbPakect)+","+ str(self.nbPakectRec) + "\n")
                    #trace.write("Liste d'energie :" + str(Liste_Energy)  +"\t \n \n")
                
                #Ajout des informations d'energie dans le dictionnaire
                if self.mote.id == nbre:
                    if b == True:
                        ResumE[nbre].extend([str(self.recu), str(self.transmit), str(self.nbPakect), str(self.nbPakectRec),str(self.nbTours)])
                nbre = nbre +1    

        
        #trace.write("\n" )
        #trace.write("\n" )
        #trace.close()
        #tracer.close()

        Identifiant = self.mote.id
        #tracer.close()
    

    def somme_mem(self):
        mem = 0
        somme = 0
        while mem < len(liste_memoire) :
            somme = somme + int(liste_memoire[mem])
            mem = mem + 1
        return somme

    def div_naive(self):
        reste = self.somme_mem() 
        while reste > self.settings.phy_numChans:
            prim = reste
            first = prim // self.settings.phy_numChans
            reste = prim % self.settings.phy_numChans
        return first

    def restriction(self):
       result = self.somme_mem() // int(self.max)
       return result

    def maximum(liste_memoire):
        count = 0
        i = 0
        taille = len(liste_memoire)
        while i <= taille:
            if liste_memoire[i+1] > liste_memoire[i]:
                count = liste_memoire[i+1] 
        return count
       

    #Essai de partitionnemnent
    def partitionnement(self):      
        v = 0
        NombreObjet = len(self.engine.motes) - 1
        if self.mote.id == NombreObjet:
            self.max = self.max + 1
            Configuration = open("Dossier/Configuration"+str(NombreObjet)+".csv","a")
            Configuration.write(""+"Numero objet,"+ "" + "Configuration"  +"\n")
            #print(NombreObjet)
            while v < NombreObjet:
                memoire  = int(liste_memoire[v])
                Configuration.write(""+str(v)+ "," + str(memoire) +"\n")
                v = v + 1

            Configuration.write("La somme de memoire :," + "" + str(self.somme_mem()) +"\n")
            Configuration.write("La plus grande memoire  est de :," + "" +  str(self.max) +"\n")
            Configuration.write("La restriction S/V est de :," + "" +   str( self.restriction()) +"\n")
            Configuration.write("Le nombre de canaux :," + "" +   str(self.settings.phy_numChans) +"\n")

            Configuration.write("----------------------------end---------------------------- \n")

            Configuration.close()

        print('')
        print('liste:', liste_memoire)
        print('')
        print('Somme de memoire : ', self.somme_mem())
        print('La plus grande memoire  est de :', str(self.max))
        print('Le nombre de canal est de : ',self.settings.phy_numChans)
        print('La restriction est de :', self.restriction())
        print('il sagit' ,self.div_naive())
        
        if self.settings.phy_numChans <= self.restriction():
            print("Ne respecte pas la condition k > S/V")
        else:
            print("Partionnement")
            print("Ici k > S/V")
            b = 1
            i = 0
            j = 0
            k = 0
            
            print (self.restriction())
            NombreObjet = len(self.engine.motes) - 1 
            calcul = self.div_naive ()           #On determine le Nombre de groupe
            listeMemo = liste_memoire
            nombreElement = len(liste) - 1 

            if self.mote.id == NombreObjet:
                print("GROUP GROUP GROUP")
                print(calcul)

                while b <= calcul:
                    if b == 1:
                        print("entrer :"+str(listeMemo))
                    
                    if listeMemo.index(max(listeMemo)) not in liste_Agent:
                        liste_Agent.append(listeMemo.index(max(listeMemo)))
                        partition[b].append(listeMemo.index(max(listeMemo)))
                    
                        indice = int(listeMemo.index(max(listeMemo)))
                        #calculValeur[b] = max(listeMemo)
                        calculValeur.append(max(listeMemo))

                        #print("indice : " + str(indice))
                        vari = "0"
                        listeMemo[indice] = vari

                    #del(listeMemo[listeMemo.index(max(listeMemo))])
                    #print("Liste des index :"+str(indexListe))
                    #print(partition)
                    print(calculValeur)

                    if b == calcul:
                        print("Sortie :"+str(listeMemo))

                    b=b+1


                while j < len(listeMemo):
                    if listeMemo[j]!= "0":
                        k = 0
                        groupepetit = 0
                        pluspetit = calculValeur[0]

                        #Nous recherchons le groupe ayant le plus petit nombre de memoire
                        while k < calcul:
                            if int(calculValeur[k]) <= int(pluspetit):
                                groupepetit = k
                                pluspetit = calculValeur[k]
                                print("Indice du plus petit groupe "+str(groupepetit))
                            k = k + 1

                        somme =  int(calculValeur[groupepetit]) + int(listeMemo[j])
                        print(somme)
    
                        calculValeur[groupepetit] = int(somme)

                        groupepetit = groupepetit + 1
                        partition[groupepetit].append(j)
                        print(calculValeur)

                    j = j + 1

                print(partition)
            
            l = 0 
            m = 1
            agent_Adres = [] 
            
            tailleliste = len(liste) #tailleliste contient la taille de la LISTE liste contenant l'adresse et la memoire de chaque objet

            #A ce niveau on recupere l'adresse de tous les objets afin de recuperer l'adresse 
            #des agents et difuser les paquets a ces agents 
            while l < tailleliste:  
                agent_Adres.append(str(liste[l])) 
                l=l+2

            print(agent_Adres)
            while m <= len(partition):
                print("Groupe " +str(m))
                values = partition[m]
                print(values)
                p=0
                
                while p < len(values):
                    print(agent_Adres[values[p]-1])
                    #self.nbTours = self.nbTours + 1
                    adresseOfEachObjet[m].append(agent_Adres[values[p]-1])
                    p = p + 1
                m = m + 1
       
    
    def motelist(self):
        #trace = open("Dossier/FichierDeTrace.txt","a")
        i = 1
        j = 0
        k = 0
        l = 0
        n = 0
        r = 0
        s = 0
        
        #liste.extend([str(self.mote.get_ipv6_link_local_addr()), self.p])
        liste.extend([str(self.mote.get_ipv6_link_local_addr()), 1])
        NombreObjet = len(self.engine.motes) - 1     

        liste_Adresse = []        #represente la liste des adresses 
        
        listTab = liste           #listeTab contient l'adresse et la memoire de chaque objet
        print(listTab) 
        taille = len(listTab)
        nombre = taille / 2 


        if nombre == NombreObjet:  #On verifie si le nbre d'objet est egale nombre d'objet de notre liste

            #A ce niveau on remplir une liste constituer de memoire de chaque objet
            while i < taille:  
                liste_memoire.append(str(listTab[i])) 
                i=i+2
            #trace.write("Liste des memoires " + str(liste_memoire)  +"\t \n")
    

            #A ce niveau on remplir une liste constituer d'adresses de chaque objet
            while j < taille:  
                liste_Adresse.append(str(listTab[j])) 
                j=j+2
            #trace.write("Liste des Adresses :" + str(liste_Adresse)  +"\t \n \n")

            #A ce niveau on remplir une liste constituer d'energie de chaque objet
            while l < taille: 
                Energie_Initial = random.randint(50, 100) 
                Liste_Energy.append(str(Energie_Initial)) 
                l=l+2
            #trace.write("Liste d'energie :" + str(Liste_Energy)  +"\t \n \n")

            #A ce niveau on remplir une liste constitue d'adresse ou chaque objet possede ses
            #adresse ip en fonction de sa memoire  
            while r < NombreObjet:
                memory = int(liste_memoire[r])   
                s = 0
                while s < memory:
                    dataObjet.append(liste_Adresse[r])
                    s = s + 1       
                r = r + 1

            #A ce niveau un dictionnaire global est utilise 
        
            #A ce niveau on remplir notre dictionnaire 
            #data
            while k < NombreObjet:
                memoire = int(liste_memoire[k])

                nombreObjetListe = nombre - 1
                l = 0
                while l < memoire:
                    m = random.randint(0, nombreObjetListe)
                    if m < len(dataObjet):
                        data[k].append(str(dataObjet[m]))
                        dataObjet.pop(m)
                        l = l + 1       

                k = k + 1

            #Liste des paquets affiches dans le fichier de trace
            #trace.write("\n Liste des objets  : " + str(data)  +"\t \n \n")

        #trace.close()

    def NombreTotalDePacket(self):
        #Attribue le nombre de paquets
        NombreDePaquets = 100
        NombreObjet = len(self.engine.motes) - 1
        taille = len(liste_memoire)
        i = 1 
        
        AtribueMemoire = 0
        NombreDePaquets = NombreDePaquets - NombreObjet

        if NombreObjet < NombreDePaquets:
            while i < taille: 
                
                if NombreDePaquets != 0:
                    AtribueMemoire = random.randint(1, NombreDePaquets)
                    #AtribueMemoire = int(AtribueMemoire**(1.0/2))
                    AtribueMemoire = int(AtribueMemoire/NombreObjet)
                  
                    print('memoire a atribue :', AtribueMemoire)
                    val = liste_memoire[i]
                    val = int(val) + int(AtribueMemoire)
                    liste_memoire[i] = str(val)
                    print('')
                    print('Traitement en cour')
                    print('')

                    #liste_memoire.append(str(AtribueMemoire)) 
                    print(' Nombre de Paquet restant : ', NombreDePaquets)
                    print('')
                    NombreDePaquets = NombreDePaquets - AtribueMemoire

                    AtribueMemoire = 0

                i=i+1
           
            #Attribue le max dans le tableau
            
            
            val = liste_memoire[0]                
            calcul = int(val) + int(self.max)
            liste_memoire[0] = str(calcul)
            NombreDePaquets = int(NombreDePaquets) - int(self.max)

            j=0
            while NombreDePaquets > 0 :
                valeur = random.randint(2, NombreObjet - 1)
                retire = 1
                val = liste_memoire[valeur]                
                calcul = int(val) + int(retire)
                liste_memoire[valeur] = str(calcul)

                NombreDePaquets = int(NombreDePaquets) - int(retire) 
            #    print('Memoire de chaque objet pendant :', liste_memoire)

        print('')
        print('Memoire de chaque objet fin :', liste_memoire)
        print('')
            

    def envoieDesPaquets(self):
        #trace = open("Dossier/FichierDeTrace.txt","a")

        donnee = data
        taille = len(donnee)

        if self.settings.phy_numChans > self.restriction():
            print("Respecte la condition k > S/V")
            if self.mote.id != 0:
                i=0
                j=0
                l=0
                
                while i < taille:
                    k= i + 1 
                    #A ce niveau, on verifie si l'objet correspont a son entrer 
                    # dans le dictionnaire
                    if self.mote.id == k:
                        donne = donnee[i] 
                        while j < len(donne):
                            #Verification de l'adresse ip
                            if self.mote.get_ipv6_link_local_addr() != donne[j]:
                                #Envoie des paquets 

                                dataDonne[i].append(str(donne[j]))
                            
                                # compute random delay
                                assert self.settings.app_pkPeriodVar < 1
                                delay = self.settings.app_pkPeriod * (1 + random.uniform(-self.settings.app_pkPeriodVar, self.settings.app_pkPeriodVar))
                                #self.nbTours = self.nbTours + 1
                                
                                self.engine.scheduleIn(
                                    delay           = delay,
                                    cb              = self._send_a_single_packet,
                                    uniqueTag       = (
                                        u'AppRoupe',
                                        u'scheduled_by_{0}'.format(self.mote.id)
                                    ),
                                    intraSlotOrder  = d.INTRASLOTORDER_ADMINTASKS,
                                )
                                
                            j= j + 1
                        #trace.write("Objet \t:"+ str(self.mote.id) +" -\n")
                    i = i + 1    

        
    def receive(self):
        #trace = open("Dossier/FichierDeTrace.txt","a")
        #tracer = open("Dossier/tracer.csv","a")
        i=0
        j=0
        k=0
        b = False
        NombreObjet = len(self.engine.motes) 
        
        
        #trace.write("receive packet \n")
        donne = dataDonne[i] 
        taille = len(donne)
        #tracer.write("trans packet" + str(ResumE) +"\n")
        if self.settings.phy_numChans > self.restriction():
            
            while i < NombreObjet:
                k=i+1
                
                while j < taille:
                    Liste_Energy[j] = int(Liste_Energy[j]) - self.Energie_Reception
                    self.recu = self.recu + self.Energie_Reception
                    self.nbPakectRec = self.nbPakectRec + 1
                      
                    b = True
                    #trace.write(" envoyer par :" + str(k) + "\t recu par :" + str(donne[j]) + "\t \n \n") 
                    j=j+1
        
                if self.mote.id == i:
                    if b == True:
                        ResumE[i].extend([str(self.recu), str(self.transmit), str(self.nbPakect), str(self.nbPakectRec),str(self.nbTours)])
                i=i+1
                self.nbTours = self.nbTours + 1
                print("receivePa")
            
        # On obtient le tableau de tour de diffusion pour chaque objet
        i = 0
        NombreObjet = len(self.engine.motes) - 1
        while i <= NombreObjet:
            if i == self.mote.id:
                #TableDiffusion[i].append(self.nbTours)  
                TableDiffusion.insert(i, self.nbTours)
            #else:
            #    TableDiffusion.extend(0)
            i = i + 1

        print(TableDiffusion)
       
        z = 0 
        #print(TableDiffusion)
        #Pour recuperer le tour de diffusion pour chaque noeud
        TourDeDiffusion = open("Dossier/TourDeDiffusion"+str(NombreObjet)+".csv","a")
        TourDeDiffusion.write(""+"Numero objet,"+ "" + "Tour de Diffusion"  +"\n")
    
        while z < len(TableDiffusion):
            
            val = TableDiffusion[z]
        
            TourDeDiffusion.write(""+str(z)+ "," + str(val) +"\n")  

            z = z + 1
        TourDeDiffusion.write("----------------------------end---------------------------- \n")

        #print(TableDiffusion.keys()) 

            




    def resume(self):
        NombreObjet = len(self.engine.motes) -1
        resumer = open("Dossier/resumer"+str(NombreObjet)+".csv","a")

        i=0
        v=1

        rec=0
        trans=0
        nbPa=0
        nbPaRe=0
        TourDeDIff=0

        NombreObjet = len(self.engine.motes) - 1
        NumeroObject = v 

        resumer.write(""+"Numero objet"+",global," + "energie depense recep" + "," + "energie depense trans" + "," + "Tour de Diffusion" +"\n")
        #resumer.write(""+"Numero objet"+",global," + "energie depense recep" + "," + "energie depense trans" +"," + "nbrePacket Trans" +","+ "nbrePacket Recu" + "," + "Tour de Diffusion" + "\n")
        while v <= NombreObjet:

            resu = ResumE[v]
            taille = len(resu) -1
            k=0
            
            if resu != []:
               
                while k < 5:
                    if k == 0:
                        nbPaRe  = int(resu[taille])                     
                    elif k == 1:        
                        nbPa = int(resu[taille])
                    elif k == 2:
                        trans = int(resu[taille])
                    elif k == 3:
                        rec = int(resu[taille])
                    elif k == 4:
                        TourDeDIff = int(resu[taille])
                    k=k+1
                    taille = taille - 1
            nbPa = int(nbPa / 2)
            resumer.write(""+str(v)+",global," + str(rec) + "," + str(trans) + "," + str(TourDeDIff) +"\n")
            #resumer.write(""+str(v)+",global," + str(rec) + "," + str(trans) +"," + str(nbPa) +","+ str(nbPaRe) +  "\n")

            v = v + 1
            if v == NombreObjet:
                resumer.write("----------------------------end---------------------------- \n")
 
        resumer.close()




class AppBurst(AppBase):
    """Generate burst traffic to the root at the specified time (only once)
    """

    #======================== public ==========================================
    def __init__(self, mote, **kwargs):
        super(AppBurst, self).__init__(mote, **kwargs)
        self.done = False

    def startSendingData(self):
        if not self.done:
            # schedule app_burstNumPackets packets in app_burstTimestamp
            self.engine.scheduleIn(
                delay           = self.settings.app_burstTimestamp,
                cb              = self._send_burst_packets,
                uniqueTag       = (
                    u'AppBurst',
                    u'scheduled_by_{0}'.format(self.mote.id)
                ),
                intraSlotOrder  = d.INTRASLOTORDER_ADMINTASKS,
            )
            self.done = True

    #======================== private ==========================================

    def _send_burst_packets(self):
        if self.mote.roupe.dodagId == None:
            # we're not part of the network now
            return

        for _ in range(0, self.settings.app_burstNumPackets):
            self._send_packet(
                dstIp         = self.mote.roupe.dodagId,
                packet_length = self.settings.app_pkLength
            )
