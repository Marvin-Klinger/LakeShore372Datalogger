from tkinter import Tk, ttk, filedialog, Text, Entry, Frame, messagebox, IntVar, StringVar
import os
import json
#from multiprocessing import Process, freeze_support
import multiprocessing
import time
import TemperatureCalibration
import MultiChannelReaderProcess
import numpy
import MultiPyVu as mpv

root = Tk()
frm = ttk.Frame(root)
frm.grid()

filepath = "" #This is a dirpath

#Needed to evaluate Checkbox-states
channels = []
for i in range(0,4):
    channels.append(IntVar())

debugState = IntVar()

calibrations = []
for i in range(0,4):
    calibrations.append(StringVar())

def fileBrowsing():       #Open filebrowser and set
    filepath = filedialog.askdirectory()
    fileField.delete(0, 'end')
    fileField.insert(0, filepath)
    fileField.configure(width=len(fileField.get()))
    return

#When user selected a directory, check if it already contains a settingfile
def validateConfig(dirpath):
    global filepath 
    filepath = dirpath
    #if(os.path.isfile(f"{dirpath}/settings.json")):
    #    importSettingsBtn.grid(column=2, row=3)
    #else:
    #    importSettingsBtn.grid_forget()
    return True

#TODO: Implement an actual import Settings logic
def readSettings():
    myChannels = []
    for channel in channels:
        myChannels.append(channel.get())
    if not(messagebox.askyesno(parent=frm, title="Import Settings", message="Your current selection will be overwritten", detail="Nothing will happen. Not implemented yet")):
        return
    return

def writeSettings():
    global filepath
    os.makedirs(filepath, exist_ok=True) #Tkinter askdir does not offer to create new Folder on Linuxplatforms
    if(os.path.isfile(f"{filepath}/settings.json")):
        if not messagebox.askokcancel(parent=frm, title="Information", message="You are about to overwrite your already existing Settingsfile and eventually datafiles.", detail="Proceed?", icon='warning'):
            return
    #Convert Tk-Integer to normal Integer
    myChannels = numpy.array([])
    for channel in channels:
        myChannels = numpy.append(myChannels, channel.get())
    myCalibrations = numpy.array([])
    for calibration in calibrations:
        myCalibrations = numpy.append(myCalibrations, calibration.get())
    #Write settings to json
    with open(f"{filepath}/settings.json", 'w') as settingsFile:
        json.dump({'filepath': filepath, 'Channels': myChannels[myChannels != 0].astype(int).tolist(), 'debug': bool(debugState.get()), "samplerate": int(sampleRateField.get()), "calibration": myCalibrations.tolist()}, settingsFile)

    DynaProcess = multiprocessing.Process(target=startProcessing, args=(filepath,))
    DynaProcess.start()

    startButton["state"] = "disabled"
    fileField["state"] = "disabled"
    startButton.configure(text="Running...", command=emptyFunction)
    while(DynaProcess.is_alive()):
        root.update()
        time.sleep(0.5)
    startButton.config(text="START", command=writeSettings)
    startButton["state"] = "enabled"
    fileField["state"] = "normal"
    return

def startProcessing(filepath):
    with mpv.Server():
        MultiChannelReaderProcess.main(filepath)
    return

def emptyFunction():
    return

if __name__ == "__main__":
    if os.name == 'nt': #First call is needed for releasing. Later one is needed to make it work on Posix systems. They don't work together
        multiprocessing.freeze_support()
    else:
        multiprocessing.set_start_method('spawn', force=True)
    
    ttk.Label(frm, text="Filepath").grid(column=0, row=2)
    fileField = Entry(frm, validate='key', validatecommand=(frm.register(validateConfig), '%P'))
    fileField.grid(column=1, row=2)
    ttk.Button(frm, text="Explore", command=fileBrowsing).grid(column=2, row=2, sticky='w')
    importSettingsBtn = ttk.Button(frm, text="Import settings", command=readSettings) 

    #Create Checkboxes
    ttk.Label(frm, text="Channels").grid(column=0, row=4)
    checkBoxFrame = Frame(frm)
    checkBoxFrame.grid(column=1, row=4, columnspan=4)

    excludedPolynomials = ['np', 'os', 'pd', 'plt', 'askdirectory', 'askopenfilename', 'calibrate_all_files_in_dir', 'show_plot']
    polynomials = [p for p in dir(TemperatureCalibration) if not(p.startswith('__') or (p in excludedPolynomials))]
    for i in range(0, 4):
        ttk.Checkbutton(checkBoxFrame, text=f"Ch {i+1}", variable=channels[i], onvalue=i+1).grid(column=i, row=4)
        ttk.OptionMenu(checkBoxFrame, calibrations[i], "None", "None", *polynomials).grid(column=i, row=5)

    ttk.Label(frm, text="Samplerate").grid(column=0, row=5)
    sampleRateField = Entry(frm, validate='key', validatecommand=(frm.register(lambda x: x.isdigit() or not x), '%P'), width=3)
    sampleRateField.grid(column=1, row=5, columnspan=1, sticky='w')
    sampleRateField.insert(0, "73")
    
    
    startButton = ttk.Button(frm, text="START", command=writeSettings)
    startButton.grid(column=0, row=6, columnspan=2)

    checkBox = ttk.Checkbutton(frm, text="Use fake data", variable=debugState, onvalue=1)
    checkBox.grid(column=0, row=7, columnspan=1)

    root.mainloop()
