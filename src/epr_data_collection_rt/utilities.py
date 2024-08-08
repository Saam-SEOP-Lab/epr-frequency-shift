import datetime
import numpy as np
import csv
import pandas as pd

from os import path
from datetime import date


def formatter(n, p):
    """
    Rounds to the specified number of decimal places and formats the number into scientific notation.

    Parameters
    ----------
    n : float
        Value to be formatted.
    p : int
        Number of decimal places to round the specified value to.

    Returns
    -------
    num : float
        Specified value rounded to specified precision.  
    """
    precision = p
    num = f"{n:.{precision}e}"
    return num
    
def getDateString():
    """
    Outputs the current date as a string in the form mmddyyyy.
    
    Parameters
    ----------

    Returns
    -------
    datestring : string
        The current date, formatted as MMDDYYYY.   
    """
    today = date.today()
    datestring = today.strftime("%m%d%Y")
    return datestring

def percent_error(measurement, error_val):
    """
    Calculates the percent error from a specified measurement and error value.  Uses formula 100*error_val/measurement

    Parameters
    ----------
    measurement : float
        measurement with which to calculate percent error
    error_val : float
        error in measurement value.

    Returns
    -------
    percent_e : float
        the percent error value.
    """
     
    ratio = error_val/measurement
    percent_e = np.abs(ratio*100)
    return percent_e

def estimateStandardDev(range):
    """
    Uses the "Range Rule" to approximate standard deviation from the range of a data set. 
    The Range Rule is an approximation of standard deviation where std_dev = range/4. N
    Note that range rule assumes that the data is varying randomly and not systematically
    
    Parameters
    ----------
    range : float
        the range of the data for which the standard deviation is to be estimated. 

    Returns
    -------
    approx_sdev : float
        the standard deviation from the mean, as approximated by the range rule.
    """
    approx_sdev = range/4
    return approx_sdev


def exportToCSV(fp, fields, formatted_data):
    """
    Exports the provided data to a csv file. 
    
    Parameters
    ----------
    fp : string
        location to save the data to, as a string.
    fields : array of strings
        the headers for the csv as an array. 
    formatted_data : 2D array 
        the data to save to the csv file as two dimensional array. 
    """

    filename = str(fp)
    #first check that no files with the same name exist
    with open(filename, 'w') as csvfile:
        # creating a csv writer object
        csvwriter = csv.writer(csvfile)
        # writing the fields
        csvwriter.writerow(fields)
        # writing the data rows
        csvwriter.writerows(formatted_data)   


def stringArraytoFloatArray(str_arry):
    """
    Takes an array of numbers that are formatted as strings and returns the same array but with all the elements converted to floats.
    
    Parameters
    ----------
    str_ary : [str]
        The array of strings to be converted to floats.

    Returns
    -------
    num_arry : [float]
        An array containing the same values as str_arry, but now represented as floats.
    """
    l = len(str_arry)
    num_arry = np.zeros(l)
    for i in range(0,l):
        num_arry[i] = float(str_arry[i])
    return num_arry
    

def stringToPandasSeries(strg, delimiter):
    """
    Using the specified delimiter, converts a string into a pandas series. 
    
    Parameters
    ----------
    strg : str
        The string to be converted to a pandas series.
    delimiter : str
        The character on which to split the string. 

    Returns
    -------
    series : pandas.Series
        A pandas series containing the data from the string after splitting it on the specified delimiter.
    """
    #assumes a string where data can be broken up by a delimiter
    strg = strg.replace('\n', '')#check if there is a newline at the end of the string and remove if present
    arry = strg.split(delimiter)
    series = pd.Series(arry)
    return series

def dtStringForFilename():
    """
    Returns the current datetime as a string, formatted for use in a filename.  
    
    Parameters
    ---------- 

    Returns
    -------
    fn : str
        A string representing the current datatime with ':' replaced with '_' and ' ' relaced with '.'.
    """
    fn = str(datetime.datetime.today())
    fn = fn.replace(':', '_')
    fn = fn.replace(' ', '-')
    return fn

def timestampToArray(ts):
    """
    Takes a time stamp and converts it into an array in the format [date, time]. 
    
    Parameters
    ---------- 
    ts: float
        A float representing the timestamp. 

    Returns
    -------
    dt_arry : [str]
        A string array of the form [date, time].
    """
    dt_obj = datetime.datetime.fromtimestamp(ts)
    dt_arry = str(dt_obj).split(' ')
    return dt_arry

def formatTimestampsForCSV(times):
    """
    Takes an array of timestamps and converts it to two arrays, one containing all the dates, the other containing all the times, to be used in data collection files. 
    
    Parameters
    ---------- 
    times: [float]
        An array of floats representing timestamps. 

    Returns
    -------
    arry_0 : [str]
        A string array containing the collection dates.
    arry_1: [str]
        A string array containing the collection times.

    """
    arry_0 = []
    arry_1 = []
    for x in times:
        temp = timestampToArray(x)
        arry_0.append(temp[0])
        arry_1.append(temp[1])
    return (arry_0, arry_1)

def get_connected_instruments(rm):
    """
    Gets a list of all instruments connected to the computer via NiVisa. 
    
    Parameters
    ---------- 
    rm: visa.ResourceManager
        A resource manager object for NI devices.  

    Returns
    -------
    instrments : [str]
        A string array containing the addresses of each instrument connected to the computer.
    """
    instrments = []
    for r in rm.list_resources():
        instrments.append(r)
    return instrments

def get_daq_ao_channels(system):
    """
    Gets a list of all available DAQ analog output channels.  
    
    Parameters
    ---------- 
    system: sys.System
        A system object representing the local system.  

    Returns
    -------
    daq_channels : [str]
        A string array of the available analog output channels from any DAQ device connected to the computer. Note that this includes both virtual and physical DAQs.
    """
    daq_channels = []
    for device in system.devices: 
        for channel in device.ao_physical_chans.channel_names:
            daq_channels.append(channel)
    return daq_channels

