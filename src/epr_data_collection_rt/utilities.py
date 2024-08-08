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
    l = len(str_arry)
    num_arry = np.zeros(l)
    for i in range(0,l):
        num_arry[i] = float(str_arry[i])
    return num_arry
    

def stringToPandasSeries(strg, delimiter):
    #assumes a string where data can be broken up by a delimiter
    #check if there is a newline at the end of the string and remove if present
    strg = strg.replace('\n', '')
    arry = strg.split(delimiter)
    series = pd.Series(arry)
    return series

def dtStringForFilename():
    fn = str(datetime.datetime.today())
    fn = fn.replace(':', '_')
    fn = fn.replace(' ', '-')
    return fn

#takes a time stamp (float) and converts it into an array in the format [date, time]
def timestampToArray(ts):
    dt_obj = datetime.datetime.fromtimestamp(ts)
    dt_arry = str(dt_obj).split(' ')
    return dt_arry

#takes an array of timestamps and converts it to two arrays, one containing all the dates, the other containing all the times
def formatTimestampsForCSV(times):
    arry_0 = []
    arry_1 = []

    for x in times:
        temp = timestampToArray(x)
        arry_0.append(temp[0])
        arry_1.append(temp[1])
    
    return (arry_0, arry_1)

def get_connected_instruments(rm):
    instrments = []
    for r in rm.list_resources():
        instrments.append(r)
    return instrments

def get_daq_ao_channels(system):
    daq_channels = []
    for device in system.devices: 
        for channel in device.ao_physical_chans.channel_names:
            daq_channels.append(channel)
    return daq_channels

