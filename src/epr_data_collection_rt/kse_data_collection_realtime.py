import nidaqmx
import time
import pyvisa as visa
import pandas as pd
import nidaqmx.system as sys

import kse_experiment_utils as kse
import utilities as util

from os import path
from pymeasure.instruments.keithley import Keithley2000
from pymeasure.adapters import PrologixAdapter
from threading import Thread
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QWidget, QPushButton, QComboBox, QFileDialog, QMessageBox
from pglive.sources.data_connector import DataConnector
from pglive.sources.live_plot import LiveLinePlot
from pglive.sources.live_plot_widget import LivePlotWidget


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)


        ### INTERNAL VARIABLES NEEDED TO RUN THE APP ###################################################
        # resource manager, system settings, options for dropdowns
        self.rm = visa.ResourceManager()
        self.system = sys.System.local()
        self.my_instruments = util.get_connected_instruments(self.rm) #list of available instruments 
        self.ao_daq_channels = util.get_daq_ao_channels(self.system) #list of analog out channels available from virtual and physical daqs
        self.metal_types = ['rb85', 'rb87','cs133']
        self.energy_levels = ['high', 'low']
        # Collection parameters
        ## parameters that will remain hard coded
        self.trig_count = 1
        self.trig_count_cmd = 'TRIG:COUN '+ str(self.trig_count)
        self.trig_source = 'EXT'
        self.trig_source_cmd = 'TRIG:SOUR '+ self.trig_source
        # Note about the timeing: the high and low times are set such that in conjunction with the initializaion cycle
        # which now has to happen each time we get a point, the total time between points will be ~.8s. these an all be adjusted if needed
        self.high_V = 2.0
        self.low_V = 0.0
        self.high_time = 0.1 
        self.low_time = 0.7 
        ## parameters that could become user entered later
        self.csv_write_batch_num = 10
        self.error_threshold = 3
        self.gpib_channel_no = 1 #the channel number for the GPIB connection from the dmm. this can be set on the dmm to anything between 1 and 16
        #user entered fields required to start collection
        self.folder = ''#'Data\\kseExperiment' #defaults to saving here if nothing is specified. 
        self.keysight_addr = ''#'USB0::0x0957::0x1807::MY58430132::INSTR' #name/address for the keysight connected to the computer
        self.daq_path = ''#'Dev2/ao0' #the path to the daq
        self.dmm_addr = ''#'ASRL6::INSTR' #address of USB connected to computer
        self.alkali_metal = ''
        self.energy_level = ''
        #variables for storing collected data until it is saved to the correct location(s)
        self.start_time = None
        self.times = [] #the timestamps will go here
        self.frequencies = []
        self.dmm_vals = []
        self.time_intervals = [] #human readable time intervals go here

        ### GUI STUFF - EVERYTHING IN THIS SECTION WILL BE VISIBLE TO THE USER AS WIDGETS IN THE APP  ######################################
        self.setWindowTitle("K_se Data Collection")
        w=1200
        h=900
        self.resize(w, h)

        ##### SAVE FILE LOCATION
        self.choose_file_location_btn = QPushButton("Choose Output Location")
        self.choose_file_location_btn.clicked.connect(self.open_file_dialog)  
        self.file_loc_lbl = QLabel("Files will be saved to: ", self)
        self.file_loc_lbl.setFont(QFont('Arial', 11))

        ##### INSTRUMENT SETTINGS DROPDOWNS
        self.inst_settings_lbl = QLabel('Instrument Settings', self)
        self.inst_settings_lbl.setFont(QFont('Arial', 14))
        #freq counter select
        self.select_freq_counter_drpdn = QComboBox()
        self.select_freq_counter_drpdn.addItems(['Select Keysight Location'])
        self.select_freq_counter_drpdn.addItems(self.my_instruments)
        self.select_freq_counter_drpdn.activated.connect(self.select_fc)
        #dmm select
        self.select_dmm_drpdn = QComboBox()
        self.select_dmm_drpdn.addItems(['Select DMM Location'])
        self.select_dmm_drpdn.addItems(self.my_instruments)
        self.select_dmm_drpdn.activated.connect(self.select_dmm)
        #daq channels
        self.select_daq_drpdn = QComboBox()
        self.select_daq_drpdn.addItems(['Select DAQ Channel'])
        self.select_daq_drpdn.addItems(self.ao_daq_channels)
        self.select_daq_drpdn.activated.connect(self.select_daq)
        #labels for the dropdowns
        self.fc_lbl = QLabel('Frequency Counter: ', self)
        self.fc_lbl.setFont(QFont('Arial', 11))
        self.dmm_lbl = QLabel('Digital Multimeter: ', self)
        self.dmm_lbl.setFont(QFont('Arial', 11))
        self.daq_lbl = QLabel('DAQ Analog Output Channel: ', self)
        self.daq_lbl.setFont(QFont('Arial', 11))
              
        ### DATA PROCESSING SETTINGS
        self.proc_settings_lbl = QLabel('Data Processing Settings', self)
        self.proc_settings_lbl.setFont(QFont('Arial', 14))
        #select the appropriate alkali metal
        self.select_metal_drpdn = QComboBox()
        self.select_metal_drpdn.addItems(['Select metal'])
        self.select_metal_drpdn.addItems(self.metal_types)
        self.select_metal_drpdn.activated.connect(self.select_metal)
        self.metal_lbl = QLabel('Alkali Metal: ', self)
        self.metal_lbl.setFont(QFont('Arial', 11))
        #select the appropriate energy level
        self.select_energy_lvl_drpdn = QComboBox()
        self.select_energy_lvl_drpdn.addItems(['Select energy level'])
        self.select_energy_lvl_drpdn.addItems(self.energy_levels)
        self.select_energy_lvl_drpdn.activated.connect(self.select_energy_level)
        self.energy_lbl = QLabel('Energy: ', self)
        self.energy_lbl.setFont(QFont('Arial', 11))


        ### DATA COLLECTION BUTTONS AND USER FEEDBACK
        #create some labels so I can give feedback to the user as they take actions
        self.user_feedback_lbl_2 = QLabel('Select instrument locations and processing parameters. Then click "Start Data Collection" to begin. \nTo stop collection click "Stop Data Collection"', self)
        self.user_feedback_lbl_2.setFont(QFont('Arial', 12))
        #Data Collection Buttons
        #initialize collection/connect to everything
        self.initialize_data_collection_btn = QPushButton("Initialize Data Collection")
        self.initialize_data_collection_btn.clicked.connect(self.connect_to_instruments)
        #start data collection
        self.start_data_collection_btn = QPushButton("Start Data Collection")
        self.start_data_collection_btn.clicked.connect(self.start_collection)
        #stop data collection and close instrument connections
        self.stop_data_collection_btn = QPushButton("Stop Data Collection")
        self.stop_data_collection_btn.clicked.connect(self.stop_collection)
    

        ####DATA PLOTTING
        self.plot_widget = LivePlotWidget(title="Frequency (Hz) vs. Time (s )")
        self.plot_curve = LiveLinePlot()
        self.plot_widget.addItem(self.plot_curve)
        self.running = True
        self.data_connector = DataConnector(self.plot_curve, max_points=150)

        ### APP LAYOUT ###################################################################################
        gridlayout = QGridLayout()
        layout = QVBoxLayout()

        #layout the file selection section
        file_loc = QHBoxLayout()
        file_loc.addWidget(self.choose_file_location_btn)
        file_loc.addWidget(self.file_loc_lbl)
        file_loc_container = QWidget()
        file_loc_container.setLayout(file_loc)

        # Layout the instrument selection section
        #frequency counter
        fc_drp = QHBoxLayout()
        fc_drp.addWidget(self.fc_lbl)
        fc_drp.addWidget(self.select_freq_counter_drpdn)
        fc_drp_container = QWidget()
        fc_drp_container.setLayout(fc_drp)
        #dmm
        dmm_drp = QHBoxLayout()
        dmm_drp.addWidget(self.dmm_lbl)
        dmm_drp.addWidget(self.select_dmm_drpdn)
        dmm_drp_container = QWidget()
        dmm_drp_container.setLayout(dmm_drp)
        #daq
        daq_drp = QHBoxLayout()
        daq_drp.addWidget(self.daq_lbl)
        daq_drp.addWidget(self.select_daq_drpdn)
        daq_drp_container = QWidget()
        daq_drp_container.setLayout(daq_drp)
        #combining all the dropdowns
        dropdown = QVBoxLayout()
        dropdown.addWidget(self.inst_settings_lbl)
        dropdown.addWidget(fc_drp_container)
        dropdown.addWidget(dmm_drp_container)
        dropdown.addWidget(daq_drp_container)
        drpdn_container = QWidget()
        drpdn_container.setLayout(dropdown)

        #data processing parameter selection
        data_proc_metal = QHBoxLayout()
        data_proc_metal.addWidget(self.metal_lbl)        
        data_proc_metal.addWidget(self.select_metal_drpdn)
        data_proc_metal_container = QWidget()
        data_proc_metal_container.setLayout(data_proc_metal)
        data_proc_energy = QHBoxLayout()
        data_proc_energy.addWidget(self.energy_lbl)        
        data_proc_energy.addWidget(self.select_energy_lvl_drpdn)
        data_proc_energy_container = QWidget()
        data_proc_energy_container.setLayout(data_proc_energy)

        data_proc = QVBoxLayout()
        data_proc.addWidget(self.proc_settings_lbl)
        data_proc.addWidget(data_proc_metal_container)
        data_proc.addWidget(data_proc_energy_container)
        data_proc_container = QWidget()
        data_proc_container.setLayout(data_proc)
        
        #layout the collection buttons
        btns = QVBoxLayout()
        btns.addWidget(self.start_data_collection_btn)
        btns.addWidget(self.stop_data_collection_btn)
        btn_container = QWidget()
        btn_container.setLayout(btns)
    
        #arrange everything in a big grid
        gridlayout.addWidget(file_loc_container, 0, 0, 1, 2) #file location selection
        gridlayout.addWidget(drpdn_container, 1, 0, 1, 1, Qt.AlignTop) #dropdowns
        gridlayout.addWidget(data_proc_container, 1, 1, 1, 1, Qt.AlignTop) #processing settings
        gridlayout.addWidget(btn_container, 2, 0, 1, 2) #collection buttons
        gridlayout.addWidget(self.user_feedback_lbl_2, 3, 0, 1, 1) #user feedback
        grid_container = QWidget()
        grid_container.setLayout(gridlayout)

        #add the plot to all this
        layout.addWidget(grid_container) 
        layout.addWidget(self.plot_widget) #plot region
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        
        #unclear if I actually need this, but I think this shows all the available widgets?
        self.show()
        app.aboutToQuit.connect(self.close_event)

    #### FUNCTIONS! #############################################

    #### User Input and Setup ####################
    def open_file_dialog(self):
        self.folder = QFileDialog.getExistingDirectory(self, 'Select Folder')
        self.file_loc_lbl.setText("Files will be saved to: "+self.folder)

    def missing_info_warning_popup(self, missing_field):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("WARNING!")
        dlg.setText(missing_field + " has not been selected. Please make a selection before attempting to collect data.")
        button = dlg.exec()
        if button == QMessageBox.Ok:
            print("OK!")

    # may the coding gods forgive me for the crime I am about to commit against arrays
    # and also the crimes against reusability 
    # the next 5 functions do almost the same thing for different dropdowns T_T
    def select_fc(self, s):
        index = s-1
        if (index >= 0):
            self.keysight_addr = self.my_instruments[index]
        else:
            self.keysight_addr = ''

    def select_dmm(self, s):
        index = s-1
        if (index >= 0):
            self.dmm_addr = self.my_instruments[index]
        else: 
            self.dmm_addr = ''

    def select_daq(self, s):
        index = s-1
        if (index >=0):
            self.daq_path = self.ao_daq_channels[index]
        else: 
            self.daq_path = ''
    
    def select_metal(self, s):
        index = s-1
        if (index >= 0):
            self.alkali_metal = self.metal_types[index]
        else: 
            self.alkali_metal = ''

    def select_energy_level(self, s):
        index = s-1
        if(index >= 0):
            self.energy_level = self.energy_levels[index]
        else:
            self.energy_level = ''
    #### End of User Input and Setup ####################

    #### Data collection functions

    def start_collection(self):
         # Start data collection in new Thread and send data to data_connector
        Thread(target=self.get_frequency_data, args=(self.data_connector,)).start()

    
    def freq_initialization_pass(self):
        self.freq_counter.write('INIT')
        #do one trigger cycle to get rid of the empty data point that apparently gets collected for reasons?
        #I hate that this is a thing, but it appears to be a thing, so we're going to roll with it
        self.task.write(2.0)
        time.sleep(0.05)
        self.task.write(0.0)
        time.sleep(0.05)
        self.freq_counter.query('R?')#remove the empty data point from the data register, so our time stamps will match up with the frequencies collected
        #initialize the DMM
        self.dmm.write('INIT')


    def get_frequency_data(self, connector):
        self.connect_to_instruments()
        self.user_feedback_lbl_2.setText("Collecting data")
        self.error_counter = 0
        while(self.running):
            
            self.freq_initialization_pass()

            self.task.write(self.high_V) #high voltage value to send (probably stay below 5V in general)
            t1=time.time()
            self.times.append(t1)
            time.sleep(self.high_time) #how long do we want to stay at the hight voltage
            self.task.write(self.low_V) #usually this will be 0V
            time.sleep(self.low_time) #how long do we want to stay at the low voltage
            #set the start time  
            if (len(self.times)==1):
                self.start_time = self.times[0]
            #time interval is last value of times minus start time value
            x = t1-self.start_time

            try:
                #get the frequency data  
                y = float(self.freq_counter.query('FETC?'))
                #get dmm data
                y2 = float(self.dmm.ask('FETC?'))#self.dmm.ask('TRAC:DATA?')

                #check that it's not an error value
                #only add a new data point to the set of arrays if both the keysight and the dmm return valid values
                if((y < 100000000000) and (y2 < 100000000000)):
                    self.frequencies.append(y)
                    self.dmm_vals.append(y2)
                    self.time_intervals.append(x)
                    #send the data to the connector, but only if both keysight and dmm provide acceptable data
                    connector.cb_append_data_point(y, x)
                #increment the count so that I can batch update the csv instead of doing it each round
                #hopefully this is more efficient?
                #update when length of array is 10, clear storage arrays after update
                if (len(self.frequencies)==self.csv_write_batch_num):
                    self.update_csv(self.frequencies, self.dmm_vals, self.time_intervals)
                    self.frequencies=[]
                    self.dmm_vals=[] 
                    self.time_intervals=[]
                elif ((len(self.frequencies) != 0) and (self.running == False)):
                    self.update_csv(self.frequencies, self.dmm_vals, self.time_intervals)
                    self.frequencies=[]
                    self.dmm_vals=[] 
                    self.time_intervals=[]
                    #only reset the times array at the end!
                    self.times = []
                #reset the error counter if you get through the whole try block successfully
                self.error_counter = 0

            except Exception as error:  
                #if you can't read the data try again??? idk why it's erroring sometimes
                self.error_counter = self.error_counter+1
                self.user_feedback_lbl_2.setText("Error collecting data point: "+ str(error))

                #if I reach a certain threshold of errors in a row when trying to read data, close the connections. 
                #for now I will set the threshold at 1
                # I need to figure out how to distinguish which types of errors are happening because only some require a shutdown
                if(self.error_counter == self.error_threshold):
                    self.closing_tasks()

        #outside the while loop, if we get here then close all the connections
        self.closing_tasks()

    def connect_to_instruments(self):
        #first we need to check that we have all the necessary inputs from the user 
        #if any of these are missing warn the user, via pop up probably
        if(self.folder==''):
            self.missing_info_warning_popup('Data Collection File Location')
        elif(self.keysight_addr==''):
            self.missing_info_warning_popup('Keysight Address')
        elif(self.dmm_addr==''):
            self.missing_info_warning_popup('DMM Address')
        elif(self.daq_path==''):
            self.missing_info_warning_popup('DAQ Channel')
        elif(self.alkali_metal==''):
            self.missing_info_warning_popup('Alkali Metal')
        elif(self.energy_level==''):
            self.missing_info_warning_popup('Energy Level')
        else:
            self.error_counter = 0
            #reset the data connector?
            self.data_connector = DataConnector(self.plot_curve, max_points=60)
            #do all the document prep at the beginning so it doesn't slow down collection later
            #create a new csv file at the specified location
            self.filename = util.dtStringForFilename()+'.csv'
            self.fp = self.folder + '\\' + self.filename
            self.outfile = open(self.fp, mode='a')
            #create an empty data frame and save the headers to the file
            self.df_headers = pd.DataFrame({'Frequencies': [], 'Voltages': [], 'Time Interval':[]})
            self.df_headers.to_csv(self.fp, mode='a', index=False)
            
            # Keysight connection setup
            self.freq_counter = self.rm.open_resource(self.keysight_addr)
            self.freq_counter.write('*RST')
            self.freq_counter.encoding = 'latin_1'
            self.freq_counter.source_channel = 'CH1'

            # Keysight data collection set up
            ## reset everything and clear the event queues
            self.freq_counter.write('STAT:PRES')
            self.freq_counter.write('*CLS')
            ## set the type of measurement to frequency
            self.freq_counter.write('CONF:FREQ')
            self.freq_counter.write(self.trig_source_cmd)
            self.freq_counter.write('TRIG:SLOP POS')
            #self.freq_counter.write(self.trig_count_cmd)

            # DAQ Setup and task initialization
            self.task = nidaqmx.Task()
            self.task.ao_channels.add_ao_voltage_chan(self.daq_path)
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
            self.user_feedback_lbl_2.setText("Connected to frequency counter and dmm")
    
    def stop_collection(self):
        self.running = False
        self.user_feedback_lbl_2.setText("Ending data collection")
        time.sleep(1)#allow the program to finish writing any remaining data to the csv before processing it
        self.process_collected_data()
        self.user_feedback_lbl_2.setText("Data processing complete. ")    

    def update_csv(self, f, v, t):
        df = pd.DataFrame({
                'Frequency': f,
                'Voltage': v,
                'Time Interval': t
            })
        df.to_csv(self.fp, mode='a', index=False, header=False)

    ### End of data collection functions section
           
    ### Clean up functions #############
    #I've copied and pasted this block enough that it should have been it's own function ages ago       
    def closing_tasks(self):
        #outside the while loop, if we get here then close all the connections
        #close the DAQ taks
        self.task.close()
        #close the csv file
        self.outfile.close()
        #close the connections
        self.openres = self.rm.list_opened_resources()
        self.user_feedback_lbl_2.setText('Closing Connection with ', str(self.openres))
        self.freq_counter.close()
        self.adapter.close()
        self.rm.close()

    def close_event(self):
        if (self.running == True):
            self.running == False
        time.sleep(0.3)#allow data collection to finish current cycle
        try: 
            self.closing_tasks()
        except:
            print("already closed I guess")
    
    ### End of Clean up functions #############

    ### Data Processing ########################
    def process_collected_data(self):
        filepath_raw = self.folder + '\\' + self.filename
        fn_arry = (self.filename).split('.')
        fn = fn_arry[0]+'.'+fn_arry[1]+'_processed.csv'
        filepath_converted = self.folder + '\\' + fn
        processed_data = kse.processAllData_rt(filepath_raw, 'rb85', 'high')
        kse.createCSVProcessedData(filepath_converted, processed_data)
    


if __name__ == '__main__':
        
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()