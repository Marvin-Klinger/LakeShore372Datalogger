from tkinter import Tk, ttk, filedialog, Text, Entry, Frame, messagebox, IntVar
import os
import json
from multiprocessing import Process, freeze_support
import time

import MultiChannelReaderProcess

root = Tk()
frm = ttk.Frame(root)
frm.grid()

filepath = "" #This is a dirpath

#Needed to evaluate Checkbox-states
channels = []
for i in range(0,4):
    channels.append(IntVar())

debugState = IntVar()

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
    if(os.path.isfile(f"{dirpath}/settings.json")):
        importSettingsBtn.grid(column=2, row=3)
    else:
        importSettingsBtn.grid_forget()
    return True

#TODO: Implement an actual import Settings logic
def readSettings():
    myChannels = []
    for channel in channels:
        myChannels.append(channel.get())
    if not(messagebox.askyesno(parent=frm, title="Import Settings", message="Your current selection will be overwritten", detail="Nothing will happen. Not implemented yet")):
        return
    return

def writeSettings(dirpath):
    os.makedirs(dirpath, exist_ok=True) #Tkinter askdir does not offer to create new Folder on Linuxplatforms
    if(os.path.isfile(f"{dirpath}/settings.json")):
        if not messagebox.askokcancel(parent=frm, title="Solidcryo", message="You are about to overwrite your already existing Settingsfile and eventually datafiles.", detail="Proceed?", icon='warning'):
            return
    #Convert Tk-Integer to normal Integer
    myChannels = []
    for channel in channels:
        myChannels.append(channel.get())
    #Write settings to json
    with open(f"{dirpath}/settings.json", 'w') as settingsFile:
        json.dump({'filepath': filepath, 'Channels':list(filter(lambda x : x != 0, myChannels)), 'debug': bool(debugState.get()), "samplerate": int(sampleRateField.get())}, settingsFile)
    DynaProcess = Process(target=startProcessing, args=(dirpath, 0))
    DynaProcess.start()
    startButton["state"] = "disabled"
    startButton.configure(text="Running...", command=lambda:emptyFunction)
    while(DynaProcess.is_alive()):
        root.update()
        time.sleep(0.5)
    startButton.config(text="START", command=lambda:writeSettings(dirpath))
    startButton["state"] = "enabled"
    return

def startProcessing(dirpath, i):
    MultiChannelReaderProcess.main(dirpath)
    #os.system(f"../MultiChannelReaderProcess/MultiChannelReaderProcess.exe {dirpath}")
    return

def emptyFunction():
    return

if __name__ == "__main__":
    freeze_support()
    ttk.Label(frm, text="Filepath").grid(column=0, row=2)
    fileField = Entry(frm, validate='key', validatecommand=(frm.register(validateConfig), '%P'))
    fileField.grid(column=1, row=2)
    ttk.Button(frm, text="Explore", command=fileBrowsing).grid(column=2, row=2, sticky='w')
    importSettingsBtn = ttk.Button(frm, text="Import settings", command=readSettings) 

    #Create Checkboxes
    ttk.Label(frm, text="Channels").grid(column=0, row=4)
    checkBoxFrame = Frame(frm)
    checkBoxFrame.grid(column=1, row=4, columnspan=4)

    ttk.Checkbutton(checkBoxFrame, text="Ch 1", variable=channels[0], onvalue=1).grid(column=0, row=4)

    ttk.Checkbutton(checkBoxFrame, text="Ch 2", variable=channels[1], onvalue=2).grid(column=1, row=4)


    ttk.Checkbutton(checkBoxFrame, text="Ch 3", variable=channels[2], onvalue=3).grid(column=2, row=4)

    ttk.Checkbutton(checkBoxFrame, text="Ch 4", variable=channels[3], onvalue=4).grid(column=3, row=4)
    
    ttk.Label(frm, text="Samplerate").grid(column=0, row=5)
    sampleRateField = Entry(frm, validate='key', validatecommand=(frm.register(lambda x: x.isdigit() or not x), '%P'), width=3)
    sampleRateField.grid(column=1, row=5, columnspan=1, sticky='w')
    sampleRateField.insert(0, "73")
    
    
    startButton = ttk.Button(frm, text="START", command=lambda:writeSettings(filepath))
    startButton.grid(column=0, row=6, columnspan=4)

    checkBox = ttk.Checkbutton(frm, text="Use fake data", variable=debugState, onvalue=1)
    checkBox.grid(column=0, row=7, columnspan=1)

    root.mainloop()
