from tkinter import Tk, ttk, filedialog, Text

root = Tk()
frm = ttk.Frame(root, padding=10)
frm.grid()

ttk.Label(frm, text="Hello World!").grid(column=0, row=0)
Text(frm).grid(column=1, row=0)
filedialog.askopenfilename()
ttk.Button(frm, text="Quit", command=root.destroy).grid(column=1, row=0)
root.mainloop()
