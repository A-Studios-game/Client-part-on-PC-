#versione client finale per comandare l'alphabot attraverso il muse 2
#va avanti se si è concentrati
#se si è concentrati e si gira la testa il robot gira nella direzione in cui il soggetto ha girato la testa
#se non si è concentrati l'alphabot sta fermo

import logging
import socket
import threading as thr
import time
#import ModuloClient
#librerie per implementazione muse
from muselsl import stream, list_muses
from pylsl import StreamInlet, resolve_byprop
import utils
#libreria che aggiunge supporto a grandi matrici e array multidimensionali
import numpy as np

registered = False
nickname = ""
SERVER=('192.168.1.123', 3450) #192.168.0.123 indirizzo IP alphabot
BUFFER_LENGTH = 5

# Length of the epochs used to compute the FFT (in seconds)
EPOCH_LENGTH = 1

# Amount of overlap between two consecutive epochs (in seconds)
OVERLAP_LENGTH = 0.8

# Amount to 'shift' the start of each next consecutive epoch
SHIFT_LENGTH = EPOCH_LENGTH - OVERLAP_LENGTH

# Index of the channel(s) (electrodes) to be used
# 0 = left ear, 1 = left forehead, 2 = right forehead, 3 = right ear
INDEX_CHANNEL = [0]


    



def museDxSx(inlet_Gyro, fs_Gyro): #funzione per capire se il soggetto indossante il muse 2 gira la testa e da che parte
    """ 3.1 ACQUIRE DATA """
        # Obtain EEG data from the LSL stream
    gyro_data, timestamp = inlet_Gyro.pull_chunk(
    timeout=1, max_samples=int(SHIFT_LENGTH * fs_Gyro))
        #print(eeg_data[-1])
    #Theta = 0.5*(gyro_data[-1][2] + gyro_data[-2][2]) * 1/fs_Gyro #velocita in questo istante, media degli ultimi 2 valori, per giroscopio
    #Theta = asse x, girare la testa verso dx e sx
    Gamma = 0.5*(gyro_data[-1][0] + gyro_data[-2][0]) * 1/fs_Gyro

    #print(f"valore GAMMA: {Gamma}")
    #Gamma inclinazione testa dx e sx
    if(Gamma > 0.3): #va a sinistra, left
        comando = 'L'
        #print("Gyroscopoe: ", comando)
    elif(Gamma < -0.3): #va a destra, right
        comando = 'R'
        #print("Gyroscopoe: ", comando)
    else:
        comando = 'F' #rimane dritto, forward
        #print("Gyroscopoe: ", comando)'''


    

                    
        #print(Theta)
        #print(timestamp)
    return comando #il comando che entrerà nell'alphabot

            
def museConcentrazione(inlet_EEG, fs_EEG): #restituisce il comando in entrata all'alphabot per la concentrazione
    eeg_buffer = np.zeros((int(fs_EEG * BUFFER_LENGTH), 1))
    filter_state = None  # for use with the notch filter
    EEG_data, timestamp = inlet_EEG.pull_chunk(
        timeout=1, max_samples=int(SHIFT_LENGTH * fs_EEG))
    ch_data = np.array(EEG_data)[:, INDEX_CHANNEL]
    eeg_buffer, filter_state = utils.update_buffer(eeg_buffer, ch_data, notch=True, filter_state=filter_state)

    """ 3.2 COMPUTE BAND POWERS """
    data_epoch = utils.get_last_data(eeg_buffer, EPOCH_LENGTH * fs_EEG)
    band_powers = utils.compute_band_powers(data_epoch, fs_EEG) #band_powers(raggi alpha, beta, theta, delta) cioè tutti gli EEG
        #print (band_powers)
    band_beta = utils.compute_beta(data_epoch, fs_EEG) #compute_beta funzione per il calcolo dei raggi beta(concentrazione)
        
        #secondo metodo          
        #print(EEG_data[-1])
        #Beta = 0.5*(EEG_data[-1][2] + EEG_data[-2][2]) * 1/fs_EEG #velocita in questo istante
        #print(Beta)
        #time.sleep(1)
    """if(Beta > 8):
        print('concentrato')
    else:
        print('non concentrato')"""
    return band_beta #comando (W / ESCI) per l'alphabot, se concentrato W quindi va avanti, altrimenti ESCI, sta fermo


class Receiver(thr.Thread):
    def __init__(self, s): #Costruttore Thread, self è come il this, s è il socket
        thr.Thread.__init__(self)  #costruttore 
        self.running = True   #fino a quando esiste
        self.s = s 

    def stop_run(self): #in caso di stop
        self.running = False

    def run(self): #Al suo interno vengono eseguite tutte le azioni 
        global registered

        while self.running:
            data = self.s.recv(4096).decode()   #ricezione
            
            if data == "OK":    #Se riceve OK, la connessione è avvenuta
                registered = True
                logging.info(f"\nConnessione avvenuta, registrato. Entrando nella chat mode...")
            
            else: #altrimenti 
                logging.info(f"\n{data}")

def main():
    global registered
    global nickname
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #creo un socket TCP / IPv4, primo che manda, creo la base che fa tutto
    print("in attesa di connessione\n")
    s.connect(SERVER)       #connessione al server
    print("connesso\n")
    #exit()
    stream("00:55:da:b5:49:3e", ppg_enabled=True, acc_enabled=True, gyro_enabled=True) #"00:55:da:b5:49:3e" = MAC ADDRESS MUSE 2
        #print(stream("00:55:da:b5:49:3e"))
        #00:55:da:b5:49:3e
    streams_Gyro = resolve_byprop('type', 'Gyroscope', timeout=2) #fa partire il giroscopio, riceve movimenti della testa su asse orizzontale (x)
        #creare un'altra stream per EEG
    streams_EEG = resolve_byprop('type', 'EEG', timeout=2) #fa partire i segnali EEG, che servono per trovare la concentrazione, riceve W (concentrato) o ESCI (non)
        #print(streams_Gyro)
        #print(streams_EEG)
        #secondo inlet per EEG
    inlet_Gyro = StreamInlet(streams_Gyro[0], max_chunklen=12)
    info_Gyro = inlet_Gyro.info()
        #print(info.desc())

    inlet_EEG = StreamInlet(streams_EEG[0], max_chunklen=12)
    info_EEG  = inlet_EEG.info()  
        
    fs_Gyro = int(info_Gyro.nominal_srate()) #frequenza del giroscopio
        #fs2 per EEG
    fs_EEG = int(info_EEG.nominal_srate()) #frequenza segnali EEG
        #print(fs)
    ricev = Receiver(s) #riceve i messaggi, per far modo che il server quando rimanda il messaggio ai client arriva a tutti
    ricev.start() #AVVIO THREAD

    comando = 'ESCI'
    while True:


        #time.sleep(0.1) 

        concentrazione = museConcentrazione(inlet_EEG, fs_EEG) #funzione che calcola il livello di concentrazione
        
        #print("comando concentrazione: ", concentrazione)
        
        #time.sleep(0.5)
        
        #lettura_file = open("file.txt", "r").read()
        comando = museDxSx(inlet_Gyro, fs_Gyro) #controllo di dove e se il soggetto gira la testa
        #stampaggio a schermo dei valori
        print("comando concentrazione: ", concentrazione)
        print(f"comando direzione: {comando}")

        #se il soggetto rimane concentrato e non muove la testa il robot proseguirà il percorso
        if(comando=='F'):
            if(concentrazione=='W'):
                s.sendall(comando.encode())
            #altrimenti si fermerà
            else: s.sendall(concentrazione.encode())
        #per muovere il robot a destra e sinistra non è necessario rimanere concentrati
        else:s.sendall(comando.encode()) #manda il messaggio al server
        #print(input())

        #time.sleep(5)   

        if 'exit' in comando:   #In caso si dovesse interrompere la connessione
            ricev.stop_run()    #interrompe la connessione
            logging.info("Disconnessione...")
            break

    ricev.join() #CONCLUSIONE THREAD
    s.close() #chiusura connessione

if __name__ == "__main__":
    main()