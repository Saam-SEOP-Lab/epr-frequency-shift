import numpy as np
import pandas as pd
import csv

###TO DO
# check how the magnetic field affects the gyromagnetic ratios
# look at the spreadsheet for this and see if we need to add that calculation into this program
# figure out of the change is large enough that we need to account for that here
# linear correction term for freq and quadratic in field

########## IMPORTANT CONTSANTS ############################################################################################################

rb87_gyromagnetic_ratio_HE = -687948.167 #Hz/Gauss
rb85_gyromagnetic_ratio_HE = -447338.733 #Hz/Gauss
cs133_gyromagnetic_ratio_HE = -344814.813 #Hz/Gauss

rb87_gyromagnetic_ratio_LE = -711218.443 #Hz/Gauss
rb85_gyromagnetic_ratio_LE = -486146.856 #Hz/Gauss
cs133_gyromagnetic_ratio_LE = -354909.377 #Hz/Gauss


conv_fact_V = 0.1 #Volts
conv_fact_G = 0.01 #Gauss
B_field_gain = 1/100

########################################################################################################################################


def getTimeIntervals(times):
    """
    Converts an array of timestamps into an array of time intervals, setting the first point at t=0.

    Parameters
    ----------
    times : [float]
        An array of timestamps represented as floats.
    
    Returns
    -------
    delta_t : [float]
        An array of time intervals starting at t=0s.   
    """
    i = 0
    delta_t = []
    for t in times:
        delta_t.append(times[i] - times[0])
        i = i+1
    return delta_t

def getMagetometerConversionFactor(volts, gauss, gain):
    """
    Gets the magnetometer conversion factor from the specified voltage readings, magnetic field, and gain values. 

    Parameters
    ----------
    volts : float
        The part of the convesion factor in Volts.
    gauss : float
        The part of the conversion factor in Gauss.
    gain : float
        The gain of the magnetic field.
    
    Returns
    -------
    mag_conversion_factor : float
        The conversion factor calculated by gauss*gain/volts   
    """
    mag_conversion_factor = (gauss/volts)*gain
    return mag_conversion_factor

def getVoltstoHzConversion(metal, energy):
    """
    Gets conversion factor for converting voltage from  the DMM to a frequency value.  

    Parameters
    ----------
    metal : str
        The akali metal used in the cell. Allowed choices are: "rb87", "rb85", or "cs133"
    energy : str
        the type of energy transition. Allowed choices are: "high" or "low"
    
    Returns
    -------
    overall_conversion_factor : float
        The overall conversion factor for the specific metal, enegry, and magnetic field being used.   
    """
    m_conv_f = getMagetometerConversionFactor(conv_fact_V, conv_fact_G, B_field_gain)
    overall_conversion_factor = 0
    if (energy == "low"):
        if (metal=="rb87"):
            overall_conversion_factor = m_conv_f*rb87_gyromagnetic_ratio_LE
        elif (metal=="rb85"):
            overall_conversion_factor = m_conv_f*rb85_gyromagnetic_ratio_LE
        elif (metal=="cs133"):
            overall_conversion_factor = m_conv_f*cs133_gyromagnetic_ratio_LE
    elif(energy == "high"):
        if (metal=="rb87"):
            overall_conversion_factor = m_conv_f*rb87_gyromagnetic_ratio_HE
        elif (metal=="rb85"):
            overall_conversion_factor = m_conv_f*rb85_gyromagnetic_ratio_HE
        elif (metal=="cs133"):
            overall_conversion_factor = m_conv_f*cs133_gyromagnetic_ratio_HE

    return overall_conversion_factor  

def getDMMChangeInVoltage(voltages):
    """
    Converts the array of voltages collected from the DMM into an array of voltage differences, with the first reading taken to be 0.    

    Parameters
    ----------
    voltages : [str]
        A string array of voltage readings from the DMM. 
    
    Returns
    -------
    delta_Vs : [float]
        A float array of voltage differences, taking the first reading to be 0.    
    """
    l = len(voltages)
    delta_Vs = []
    initial_V = float(voltages[0])
    for i in range(0,l):
        delta_Vs[i] = float(voltages[i])-initial_V
    return delta_Vs

def convertDMMData(volts, metal, energy):
    """
    Converts the array of voltages collected from the DMM into an array of frequencies changes.   

    Parameters
    ----------
    voltages : [str]
        A string array of voltage readings from the DMM. 
    
    Returns
    -------
    dmm_freqs : [float]
        A float array of frequency changes, taking the first reading to be 0.    
    """
    dmm_freqs = []
    convf = getVoltstoHzConversion(metal, energy)
    initial_V = float(volts[0])
    for v in volts:
        delta_V = float(v)-initial_V #convert raw voltage to change in voltage
        dmm_freqs.append(delta_V*convf) #convert change in voltage to frequency value and add to array
    return dmm_freqs

def getRawDataFromCSV(fp, row_freq, row_dmm, row_time):
    """
    Reads raw data stored in a csv and return an array of frequencies, an array of dmm readings, and an array of time intervals.    

    Parameters
    ----------
    fp : str
        The file path to the raw data file as a string. 
    row_freq : str
        The name of the frequency column as string.
    row_dmm : str
        The name of the dmm column as string.
    row_time : try
        The name of the time interval column as string.
    
    Returns
    -------
    freq_counter : [str]
        A string array of frequency readings.    
    dmm  : [str]
        A string array of dmm readings.
    timestamps : [str]
        A string array of times.
    """
    outfile = open(fp, 'r')
    data = csv.reader(outfile, delimiter=",", quotechar='|')
    freq_counter, dmm, timestamps = [], [], []
    for row in data:
        freq_counter.extend([row[row_freq]])
        dmm.extend([row[row_dmm]])
        timestamps.extend([row[row_time]])
    freq_counter = freq_counter[1:]
    dmm = dmm[1:]
    timestamps = timestamps[1:]
    outfile.close()
    return freq_counter, dmm, timestamps

def convertTimestampstoInterval(timestamps):
    """
    Converts an array of timestamps to an array of time intervals. 

    Parameters
    ----------
    timestamps : [str]
        A string array of timestamps.  
    
    Returns
    -------
    delta_times : [float]
        A float array of time intervals.    
    """
    #convert strings to floats
    for i in range(0, len(timestamps)):
        timestamps[i] = float(timestamps[i])
    #convert to time from start
    delta_times = getTimeIntervals(timestamps)
    return delta_times

def convertKSFreqstoFloat(freqs):
    """
    Converts an array of frequencies stored as strings to an array of floats.

    Parameters
    ----------
    freqs : [str]
        A string array of frequencies.  
    
    Returns
    -------
    freq_nums : [float]
        A float array of frequencies.    
    """
    freq_nums = []
    for i in range(0,len(freqs)):
        freq_nums.append(float(freqs[i]))
    return freq_nums 

def adjustKSfromDMM(ks, dmm):
    """
    Converts an array of frequencies stored as strings to an array of floats.

    Parameters
    ----------
    ks : [float]
        A float array of frequencies as measured by the frequency counter. 
    dmm :  [float]
        A float array of frequencies as calculated from the voltages measured by the dmm. 
    
    Returns
    -------
    ks_adj : [float]
        A float array of frequencies adjusted based on the DMM readings.    
    """
    ks_adj = []
    for i in range(0, len(ks)):
        ks_adj.append(ks[i]-dmm[i])
    return ks_adj

def processAllData(filepath, metal, energy):
    """
    Takes a filepath, metal, and enegrgy and converts the data in that file into the proper format for analysis. 
    NOTE: this function is used by the BATCHED version of the data collection app

    Parameters
    ----------
    filepath : str
        A string representing the filepath to raw data csv. 
    metal :  str
        A string representing the alkali metal type used in the experiment.
    energy : str
        A string representing the appropriate energy level transition for the experiment.  
    
    Returns
    -------
    df : pandas.Dataframe
        A pandas dataframe object containing the following columns: Time (time intervals in seconds), 
        Keysight (keysight frequency readings in Hz), DMM (dmm readings converted to frequency in Hz), 
        and Adjusted Keysight Data (frequency calculated by Keysight[i]-DMM[i] in Hz) 
    """
    freq_c, dmm_v, tstamps = getRawDataFromCSV(filepath, 0, 1, 3)
    dmm_freqs = convertDMMData(dmm_v, metal, energy)
    t_ints = convertTimestampstoInterval(tstamps)
    freq_c = convertKSFreqstoFloat(freq_c)
    freq_c_adj = adjustKSfromDMM(freq_c, dmm_freqs)

    #make a data frame for these to live in
    df = pd.DataFrame({
        'Time': t_ints,
        'Keysight': freq_c,
        'DMM': dmm_freqs,
        'Adjusted Keysight Data': freq_c_adj
    })
    return df

def processAllData_rt(filepath, metal, energy):
    """
    Takes a filepath, metal, and enegrgy and converts the data in that file into the proper format for analysis. 
    NOTE: this function is used by the REALTIME version of the data collection app

    Parameters
    ----------
    filepath : str
        A string representing the filepath to raw data csv. 
    metal :  str
        A string representing the alkali metal type used in the experiment.
    energy : str
        A string representing the appropriate energy level transition for the experiment.  
    
    Returns
    -------
    df : pandas.Dataframe
        A pandas dataframe object containing the following columns: Time (time intervals in seconds), 
        Keysight (keysight frequency readings in Hz), DMM (dmm readings converted to frequency in Hz), 
        and Adjusted Keysight Data (frequency calculated by Keysight[i]-DMM[i] in Hz) 
    """
    freq_c, dmm_v, t_ints = getRawDataFromCSV(filepath, 0, 1, 2)
    dmm_freqs = convertDMMData(dmm_v, metal, energy)
    freq_c = convertKSFreqstoFloat(freq_c)
    freq_c_adj = adjustKSfromDMM(freq_c, dmm_freqs)

    #make a data frame for these to live in
    df = pd.DataFrame({
        'Time': t_ints,
        'Keysight': freq_c,
        'DMM': dmm_freqs,
        'Adjusted Keysight Data': freq_c_adj
    })
    return df


def createCSVProcessedData(fp, data):
    """
    Takes a dataframe and saves it to the specified file path. 

    Parameters
    ----------
    fp : str
        A string representing the filepath where the data is to be saved. 
    data :  pandas.Dataframe
       The data to save to the file. 
    
    Returns
    -------
    """
    outfile = open(fp, 'wb')
    data.to_csv(outfile, index=False, header=True)
    outfile.close()


def findOverflowVals(data, target_column):
    """
    Returns a list of rows where data exceeds a specific threshold. 

    Parameters
    ----------
    data : pandas.Dataframe
        A pandas Dataframe containing the data to be analyzed.  
    target_column :  str
       The name of the column to analyze. 
    
    Returns
    -------
    rows : list
        A list of rows containing data that exceed the threshold.
    """
    rows = data[data[target_column] > 100000000000].index.tolist()
    return rows

def removeDMMOverflowVals(fp):
    """
    Removes all rows from the rawdata in which the DMM reports an overflow value.  

    Parameters
    ----------
    fp : str
        A string representing the filepath to the raw data.    
    
    Returns
    -------
    clean_data : pandas.Dataframe
        A pandas Dataframe with all rows containing DMM overflow values removed.
    """
    data = pd.read_csv(fp)
    to_remove = findOverflowVals(data, 'Voltages')
    clean_data = data.drop(to_remove)
    return clean_data

def removeFreqCounterOverflowVals(fp):
    """
    Removes all rows from the rawdata in which the frequency counter reports an overflow value.  

    Parameters
    ----------
    fp : str
        A string representing the filepath to the raw data.    
    
    Returns
    -------
    clean_data : pandas.Dataframe
        A pandas Dataframe with all rows containing frequency counter overflow values removed.
    """
    data = pd.read_csv(fp)
    to_remove = findOverflowVals(data, 'Frequencies')
    clean_data = data.drop(to_remove)
    return clean_data

def removeAllOverflowVals(fp, list_cols):
    """
    Removes all rows from the rawdata in which the specified columns reports an overflow value.  

    Parameters
    ----------
    fp : str
        A string representing the filepath to the raw data.
    list_cols : [str]
        A string array of all columns to analyze.     
    
    Returns
    -------
    clean_data : pandas.Dataframe
        A pandas Dataframe with all rows containing overflow values in the specified columns removed.
    """
    data = pd.read_csv(fp)
    for col in list_cols:
        to_remove = findOverflowVals(data, col)
        data = data.drop(to_remove)
    return data

def getAvgAndStdDev(data_set):
    """
    Returns an array containing the average and standard deviation of the given data, in the form [average, standard_deviation].  

    Parameters
    ----------
    data_set : np.array()
        A numpy array to be analyzed.    
    
    Returns
    -------
    basic_stats : [float]
        A float array in the form [average, standard_deviation].
    """
    avg = np.average(data_set)
    std_dev = np.std(data_set)
    basic_stats = [avg, std_dev]
    return basic_stats