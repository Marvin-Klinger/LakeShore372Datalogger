from tkinter import Tk, ttk, filedialog, Text, Entry, Frame, messagebox, IntVar
from os import path
import json

root = Tk()
frm = ttk.Frame(root)
frm.grid()

filepath = "" #This is a dirpath
channels = []
for i in range(0,4):
    channels.append(IntVar())

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
    if(path.isfile(f"{dirpath}/settings.json")):
        importSettingsBtn.grid(column=2, row=3)
    else:
        importSettingsBtn.grid_forget()
    return True

def readSettings():
    myChannels = []
    for channel in channels:
        myChannels.append(channel.get())
    print(myChannels)
    if(messagebox.askyesno("Import Settings", "Your current selection will be overwritten")):
        return
    return

def writeSettings(dirpath):
    if(path.isfile(f"{dirpath}/settings.json")):
        if not messagebox.askokcancel(parent=frm, title="Solidcryo", message="You are about to overwrite your already existing Settingsfile and eventually datafiles.", detail="Proceed?", icon='warning'):
            return
    myChannels = []
    for channel in channels:
        myChannels.append(channel.get())
    with open(f"{dirpath}/settings.json", 'w') as settingsFile:
        json.dump({'filepath': filepath, 'Channels':list(filter(lambda x : x != 0, myChannels))}, settingsFile)
    with open(f"{dirpath}/settings.json", 'r') as settingsFile:
        settingsJSON = json.load(settingsFile)
        print(settingsJSON["Channels"])
       # os.system(f"python3 MultiChannelReaderProcess.py {dirpath}"
    return

ttk.Label(frm, text="Filepath").grid(column=0, row=2)
fileField = Entry(frm, validate='key', validatecommand=(frm.register(validateConfig), '%P'))
fileField.grid(column=1, row=2)
ttk.Button(frm, text="Explore", command=fileBrowsing).grid(column=2, row=2, sticky='w')
importSettingsBtn = ttk.Button(frm, text="Import settings", command=readSettings) 

#Create Checkboxes
ttk.Label(frm, text="Channels").grid(column=0, row=4)
checkBoxFrame = Frame(frm)
checkBoxFrame.grid(column=1, row=4, columnspan=3)

checkBox = ttk.Checkbutton(checkBoxFrame, text="Ch 1", variable=channels[0], onvalue=1)
checkBox.grid(column=0, row=4)

checkBox = ttk.Checkbutton(checkBoxFrame, text="Ch 2", variable=channels[1], onvalue=2)
checkBox.grid(column=1, row=4)


checkBox = ttk.Checkbutton(checkBoxFrame, text="Ch 3", variable=channels[2], onvalue=3)
checkBox.grid(column=2, row=4)

checkBox = ttk.Checkbutton(checkBoxFrame, text="Ch 4", variable=channels[3], onvalue=4)
checkBox.grid(column=3, row=4)

ttk.Button(frm, text="START", command=lambda:writeSettings(filepath)).grid(column=0, row=5, columnspan=4)

root.mainloop()
