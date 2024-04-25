from tkinter import Tk, ttk, filedialog, Text, Entry
from os import path

root = Tk()
frm = ttk.Frame(root, padding=10)
frm.grid()

def fileBrowsing(entryfield):       #Open filebrowser and set
    text = filedialog.askdirectory()
    entryfield.delete(0, 'end')
    entryfield.insert(0, text)
    entryfield.configure(width=len(entryfield.get()))
    return

def validateConfig(dirpath):           #When user selected a directory, check if it already contains a settingfile
    if(path.isfile(f"{dirpath}/settings.cnf")):
        importSettingsBtn.grid(column=2, row=3)
    else:
        importSettingsBtn.grid_forget()
    return True

def readSettings():
    print("I read Settings")

ttk.Label(frm, text="This won't create any directory").grid(column=0, row=0, columnspan=2, sticky='w')
ttk.Label(frm, text="Filepath").grid(column=0, row=2)
fileField = Entry(frm, validate='key', validatecommand=(frm.register(validateConfig), '%P'))
fileField.grid(column=1, row=2)
ttk.Button(frm, text="Explore", command=lambda:fileBrowsing(fileField)).grid(column=2, row=2, sticky='w')
importSettingsBtn = ttk.Button(frm, text="Import settings", command=readSettings) 

root.mainloop()

