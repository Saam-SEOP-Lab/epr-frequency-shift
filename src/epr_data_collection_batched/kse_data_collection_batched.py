from PyQt5.QtCore import QSize, Qt, QRunnable, pyqtSlot, pyqtSignal, QThreadPool, QObject
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout, QGridLayout, QWidget, QPushButton, QScrollArea, QGroupBox
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg


import traceback, sys
import math
import nidaqmx
import time
import pyvisa as visa
import pandas as pd
import src.epr_data_collection_rt.utilities as util
from os import path
from pymeasure.instruments.keithley import Keithley2000
from pymeasure.adapters import PrologixAdapter

########################################## Helper functions go here ##############################################################################
#these should go on their own module probably idk
def getTrigCountCmd(num):
    trig_num_cmd = 'TRIG:COUN ' + str(num)
    return trig_num_cmd

def getTrigSourceCmd(sr):
    trig_src_cmd = 'TRIG:SOUR '+ sr
    return trig_src_cmd

def collectionTimeToNumCycles(col_time, trig_count, lowtime, hightime):
    time_per_point = lowtime + hightime
    time_per_cycle = time_per_point * trig_count
    num_cycles = col_time/time_per_cycle
    #round up, to the nearest int
    num_cycles = math.ceil(num_cycles)
    return int(num_cycles)
####################################################################################################################################################

#class for signals sent from treadable process
class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

#make some workers to do threading because unfortunately we must
class Worker(QRunnable):
    #worker thread
    @pyqtSlot()
    def __init__(self, function, *args, **kwargs):
        super(Worker, self).__init__()
        self.function = function # I think this allows me to reuse this code for whatever process I need to run
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        #self.kwargs['process_callback'] = self.signals.progress

    def run(self):
        try:
            result = self.function(*self.args, **self.kwargs)
        except: 
            traceback.print_exc()
            exc_type, value = sys.exc_info()[:2]
            self.signals.error.emit((exc_type, value, traceback.format_exc()))
        else:  
            self.signals.result.emit(result)
        finally: 
            self.signals.finished.emit()



class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.setWindowTitle("K_se Data Collection")
        w=900
        h=900
        self.resize(w, h)

        #stuff I need to display
        #BUTTONS
        self.initialize_data_collection_btn = QPushButton("Initialize Data Collection")
        self.start_data_collection_btn = QPushButton("Start Data Collection")
        self.stop_data_collection_btn = QPushButton("Stop Data Collection")
        #GRAPH
        self.x
        self.y

        #self.frame = pg.GraphicsLayoutWidget()
        #self.data_disp = self.frame.addPlot()

        self.data_disp = pg.PlotWidget()

        
        self.data_disp.setLabel("left", "frequency (Hz)")
        self.data_disp.setLabel("bottom", "time (s)")
        #self.data_disp.enableAutoRange()
        #SCROLL BOX FOR THE GRAPH
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.data_disp)
        self.scroll.setWidgetResizable(True)
        #self.frame.setFixedWidth(1000)
        self.data_disp.setMouseEnabled(x=False, y=False)

        

        #connect the widgets to actions
        self.initialize_data_collection_btn.clicked.connect(self.connect_to_instruments)
        self.start_data_collection_btn.clicked.connect(self.collection_thread)
        self.stop_data_collection_btn.clicked.connect(self.stop_collection)

        #parameters I need to be able to access go here
        #collect data flag
        self.collection_active = False
        self.collection_cycle_active = None
        #Collection parameters set here:
        self.trig_count = 10
        self.trig_count_cmd = getTrigCountCmd(self.trig_count)
        self.trig_source = 'EXT'
        self.trig_source_cmd = getTrigSourceCmd(self.trig_source)
        self.high_V = 2.0
        self.low_V = 0.0
        self.high_time = 0.1
        self.low_time = 0.4
        self.how_long_collect = 20
        self.how_many_cycles = collectionTimeToNumCycles(self.how_long_collect, self.trig_count, self.low_time, self.high_time)
        self.folder = 'Data\\kseExperiment\\'
        self.keysight_addr = 'USB0::0x0957::0x1807::MY58430132::INSTR' #name/address for the keysight connected to the computer
        self.daq_path = 'Dev2/ao0' #the path to the daq
        self.dmm_addr = 'ASRL6::INSTR' #address of USB connected to computer
        self.gpib_channel_no = 1 #the channel number for the GPIB connection from the dmm. this can be set on the dmm to anything between 1 and 16

        self.start_time = None

        #get everything on the screen
        layout = QGridLayout()
        btns = QHBoxLayout()
        btns.addWidget(self.initialize_data_collection_btn)
        btns.addWidget(self.start_data_collection_btn)
        btns.addWidget(self.stop_data_collection_btn)
        btn_container = QWidget()
        btn_container.setLayout(btns)
        layout.addWidget(btn_container, 0, 0)
        layout.addWidget(self.scroll, 1, 0)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        #display
        self.show()
        #self.connect_to_instruments()

        #make the threadpool
        self.threadpool = QThreadPool()

    #functions
    def plot_data(self):
        x=self.time_intervals
        y=self.frequencies.to_list()
        for i in range(0, len(y)):
            y[i]=float(y[i])
        #print(x)
        #print(y)
        self.data_disp.plot(x,y)
        self.data_disp.update()
        #self.data_disp.autoRange()

    def collection_thread(self):
        worker = Worker(self.collect_data)
        #add some sort of way to check on this process later?

        #start my thread
        self.threadpool.start(worker)    

    def collect_data(self):

        self.cycle_num=1
        while (True):  #self.cycle_num <= self.how_many_cycles
            self.collection_cycle_active = True

            self.freq_counter.write('INIT')
            #do one trigger cycle to get rid of the empty data point that apparently gets collected for reasons?
            #I hate that this is a thing, but it appears to be a thing, so we're going to roll with it
            self.task.write(2.0)
            time.sleep(0.1)
            self.task.write(0.0)
            time.sleep(0.1)
            self.freq_counter.query('R?')#remove the empty data point from the data register, so our time stamps will match up with the frequencies collected
            
            # set up the data trace so I can get more than one mesurement when we reach the end of the collection cycle
            # I have to do this here so all the data points stay in sync because of the weird empty value the keysight likes to for it's first trigger cycle
            cmd_trace = 'TRAC:POIN ' + str(self.trig_count)
            self.dmm.write(cmd_trace)
            self.dmm.write('TRAC:FEED SENS1;FEED:CONT NEXT')
            self.dmm.write('INIT')

            print('Starting Data Collection Cycle '+str(self.cycle_num))
            self.times = [] #the timestamps will go here
            self.frequencies = []
            self.dmm_vals = []
            self.time_intervals = []
            
            #times = daqUtils.genAnalogTriggerCycle(task, trig_count, high_V, low_V, high_time, low_time)
            i=0
            while (i<self.trig_count):
                self.task.write(self.high_V) #high voltage value to send (probably stay below 5V in general)
                self.times.append(time.time())
                time.sleep(self.high_time) #how long do we want to stay at the hight voltage
                self.task.write(self.low_V) #usually this will be 0V
                time.sleep(self.low_time) #how long do we want to stay at the low voltage
                if (i==0 and self.cycle_num ==1):
                    self.start_time = self.times[0]
                self.time_intervals.append((self.times[i]-self.start_time))
                i = i+1

            print('Ending Collection Cycle '+str(self.cycle_num))

            try:
                self.frequencies = self.freq_counter.query('FETC?')
            except: 
                print('I regret to inform you that something done f*cked up with the Keysight and there is no data.')
                print('Ending data collection.')
                self.task.close()
                self.freq_counter.close()
                self.adapter.close()
                self.rm.close()

            try: 
                self.dmm_vals = self.dmm.ask('TRAC:DATA?')
            except:  
                print('I regret to inform you that something done f*cked up with the Keysight and there is no data.')
                print('Ending data collection.')
                self.task.close()
                self.freq_counter.close()
                self.adapter.close()
                self.rm.close()   

            #now I need to make the data into some sort of format that we can easily put in a text file
            self.frequencies = util.stringToPandasSeries(self.frequencies, ',')
            self.dmm_vals = util.stringToPandasSeries(self.dmm_vals, ',')
            self.hrdates, self.hrtimes = util.formatTimestampsForCSV(self.times)
            
            self.df = pd.DataFrame({
                'Frequency': self.frequencies,
                'Voltage': self.dmm_vals,
                'Time': self.hrtimes, 
                'Timestamps': self.times
            })
            self.df.to_csv(self.fp, mode='a', index=False, header=False)
            self.cycle_num = self.cycle_num+1
            self.plot_data()
            self.collection_cycle_active = False

    
    def connect_to_instruments(self):
        # in case there is data from the last run in the plot, clear the plot before connecting
        self.data_disp.clear()

        #do all the document prep at the beginning so it doesn't slow down collection later
        #create a new csv file at the specified location
        self.filename = util.dtStringForFilename()+'.csv'
        self.fp = self.folder + self.filename
        self.file = open(self.fp, 'a')
        #create an empty data frame and save the headers to the file
        self.df_headers = pd.DataFrame({'Frequencies': [], 'Voltages': [], 'Times':[], 'Timestamps':[]})
        self.df_headers.to_csv(self.fp, mode='a', index=False)
        print('Output file created')

        # open the resource manager so we can connect to the keysight and the keithley
        self.rm = visa.ResourceManager()

        # Keysight connection setup
        self.freq_counter = self.rm.open_resource(self.keysight_addr)
        self.freq_counter.encoding = 'latin_1'
        self.freq_counter.source_channel = 'CH1'

        # Keysight data collection set up
        ## reset everything and clear the event queues
        self.freq_counter.write('*RST')
        self.freq_counter.write('STAT:PRES')
        self.freq_counter.write('*CLS')
        ## set the type of measurement to frequency
        self.freq_counter.write('CONF:FREQ')
        self.freq_counter.write(self.trig_source_cmd)
        self.freq_counter.write('TRIG:SLOP POS')
        self.freq_counter.write(self.trig_count_cmd)

        # DAQ Setup and task initialization
        self.task = nidaqmx.Task()
        self.task.ao_channels.add_ao_voltage_chan(self.daq_path)
        print('Starting Collection')
        self.task.start()
        self.task.write(0.0)#make sure we are starting at 0V

        #Keithley dmm connection set up
        self.adapter = PrologixAdapter(self.dmm_addr, self.gpib_channel_no) #create prologix adapter and connect to GPIB w/ address 1
        self.dmm = Keithley2000(self.adapter) #create the instrument using the adapter

        # Keithley data collection set up
        ## reset everything and clear the event queues
        self.dmm.reset()
        ## need to set trigger type to external
        self.dmm.write(self.trig_source_cmd)
        ## set trigger count to the desired number of datapoints per collection cycle
        self.dmm.write(self.trig_count_cmd)
        ## set sample count to 1 (this is one sample per trigger)
        self.dmm.write('SAMP:COUN 1')

    
    def stop_collection(self):
        self.collection_active = False                
        #close the DAQ taks
        self.task.close()
        #close the csv file
        self.file.close()
        #close the connections
        self.openres = self.rm.list_opened_resources()
        print('Closing Connection with ', self.openres)
        self.freq_counter.close()
        self.adapter.close()
        self.rm.close()



app = QApplication([])
window = MainWindow()
window.show()

app.exec()