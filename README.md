# epr-frequency-shift
Codebase for tools used to measure EPR frequency shift of alkali metal in the presence of polarized noble gas

to create a stand alone app you need to run pyinstaller with the following insane settings:

pyinstaller --icon=epr_icon.png --windowed --copy-metadata nidaqmx --paths="C:\Users\Saam Group\Desktop\development\epr-frequency-shift\src\epr_data_collection_rt" kse_data_collection_realtime.py