import tkinter as tk
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.figure import Figure

import pmca
import serial
import serial.tools.list_ports
import threading
import queue
import numpy as np
import csv

class Application(tk.Frame):
    def __init__(self, master, mca):
        super().__init__(master)
        self.master = master
        self.mca = mca

        self.master.title('Pocket MCA: ' + self.mca.ser.name)
        self.pack()
  
        self.create_widgets()
        self.start_up()

    def cleanup(self):
        self.queue_tx.put(None)

    def create_widgets(self):
        self.canvas_frame = tk.Frame(self.master)
        self.canvas_frame.pack(pady=10)
        self.buttons_frame = tk.Frame(self.master)
        self.buttons_frame.pack(pady=10)
        self.terminal_container = tk.Frame(self.master)
        self.terminal_container.pack(padx=10, pady=10)
        self.log_frame = tk.Frame(self.terminal_container)
        self.log_frame.pack(padx=10, pady=10)
        self.command_frame = tk.Frame(self.terminal_container)
        self.command_frame.pack(padx=10, pady=10)

        # for canvas
        self.fig = Figure(figsize=(5, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.lines, = self.ax.plot([], [])
        self.canvas = FigureCanvasTkAgg(self.fig, self.canvas_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack()

        self.toolbar = NavigationToolbar2Tk(self.canvas, self.canvas_frame)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack()

        # for button
        self.save_button = tk.Button(self.buttons_frame, text='Save to CSV file', command=self.onSaveButtonClicked)
        self.save_button.grid(row=0, column=0, padx=10)
        self.clear_button = tk.Button(self.buttons_frame, text='Clear data', command=self.onClearButtonClicked)
        self.clear_button.grid(row=0, column=1, padx=10)
        self.mode = tk.IntVar()
        self.mode_histogram = tk.Radiobutton(self.buttons_frame, text='Histogram', value=0, variable=self.mode, command=self.onModeChanged)
        self.mode_freerun = tk.Radiobutton(self.buttons_frame, text='Freerun', value=1, variable=self.mode, command=self.onModeChanged)
        self.mode_trigger = tk.Radiobutton(self.buttons_frame, text='Trigger', value=2, variable=self.mode, command=self.onModeChanged)
        self.mode_histogram.grid(row=0, column=2, padx=10)
        self.mode_freerun.grid(row=0, column=3, padx=10)
        self.mode_trigger.grid(row=0, column=4, padx=10)

        # for terminal
        h = 6
        self.log = tk.Text(self.log_frame, height=h)
        self.log.pack(side=tk.LEFT)
        self.log_scrollbar = tk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log.yview)
        self.log.yscrollcommand = self.log_scrollbar.set
        self.log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.command_var = tk.StringVar()
        self.command = tk.Entry(self.command_frame, textvariable=self.command_var)
        self.command.bind("<Return>", self.onCommandEnter)
        self.command.pack()
        self.command.focus()

        self.log.bind("<Configure>", lambda e: self.command.configure(width=int(self.log_frame.winfo_width()/h)))

    def start_up(self):
        self.onClearButtonClicked()

        self.queue_rx = queue.Queue()
        self.queue_tx = queue.Queue()

        self.thread_rx = threading.Thread(target=receiver, args=(self.mca, self.queue_rx,))
        self.thread_tx = threading.Thread(target=transfer, args=(self.mca, self.queue_tx,))
        self.thread_rx.setDaemon(True)
        self.thread_tx.setDaemon(True)
        self.thread_rx.start()
        self.thread_tx.start()

        self.update()
        self.onModeChanged()
        self.sendCommand('H')

    def update_graph(self):
        self.lines.set_data(self.graph_x, self.graph_y)
        self.ax.relim()
        self.ax.autoscale()
        self.canvas.draw()

    def update(self):
        while not self.queue_rx.empty():
            event = self.queue_rx.get()
            t = type(event)
            if t == EventHistogram:
                self.count += 1
                y = np.array(self.mca.bin2array(event.data)) - 1
                if self.mode.get() == 0:
                    self.fig.suptitle('Histogram %d: %d cps' % (self.count, y.sum()))
                    self.graph_y += y
                else:
                    self.fig.suptitle('Oscilloscope %d' % self.count)
                    self.graph_y = y
                self.update_graph()
            elif t == EventResponse:
                self.addLog(event.response)
            elif t == EventError:
                self.addLog(event.response)
            self.queue_rx.task_done()
        self.master.after(10, self.update)

    def onSaveButtonClicked(self):
        types = [('CSV file', '*.csv')]
        filename = tk.filedialog.asksaveasfilename(defaultextension='csv' , filetypes=types, title='Save graph data')
        if filename:
            with open(filename, 'w') as f:
                for i in range(len(self.graph_y)):
                    f.write('%d, %d\n' % (self.graph_x[i], self.graph_y[i]))

    def onClearButtonClicked(self):
        self.graph_x = np.arange(0, pmca.PMCA.CHANNELS)
        self.graph_y = np.zeros(pmca.PMCA.CHANNELS, dtype=int)
        self.count = 0
        self.fig.suptitle('')
        self.update_graph()

    def onModeChanged(self):
        self.sendCommand('Y' + str(self.mode.get()))

    def onCommandEnter(self, key):
        cmd = self.command_var.get()
        self.sendCommand(cmd)
        self.command.delete(0, tk.END)

    def sendCommand(self, cmd):
        self.queue_tx.put(cmd)
        self.addLog(cmd)

    def addLog(self, log):
        self.log.insert(tk.END, log + '\n')
        self.log.see(tk.END)

class EventHistogram():
    def __init__(self, data):
        self.data = data

class EventResponse():
    def __init__(self, response):
        self.response = response.decode('UTF-8', errors='ignore').replace('\r', '\n')

class EventError():
    def __init__(self, response):
        self.response = response.decode('UTF-8', errors='ignore').replace('\r', '\n')

def receiver(mca, queue):
    try:
        while True:
            res, data = mca.read()
            if res != mca.COMMAND_HANDLED:
                # error
                queue.put(EventError(data+res))
            else:
                if len(data) == mca.BYTES_OF_HISTOGRAM:
                    queue.put(EventHistogram(data))
                else:
                    queue.put(EventResponse(data+res))
    except Exception as e:
        # force stop by an exception
        #print(e)
        pass

def transfer(mca, queue):
    while True:
        command = queue.get()
        if command is None:
            break
        mca.write(command)
        queue.task_done()

class ComportDialog(tk.Frame):
    def __init__(self, master, result_list):
        super().__init__(master)
        self.master = master
        self.result_list = result_list

        self.master.title('Select COM port')
        #self.master.geometry('480x320')
        self.pack(padx=10, pady=10)

        self.create_widgets()

    def create_widgets(self):
        self.comports = serial.tools.list_ports.comports()

        self.ports_frame = tk.Frame(self.master)
        self.ports_frame.pack(padx=10, pady=10)
        self.buttons_frame = tk.Frame(self.master)
        self.buttons_frame.pack(padx=10, pady=10)

        # for comport list
        self.listbox = tk.Listbox(self.ports_frame, width=100, height=10)
        for port in self.comports:
            self.listbox.insert(tk.END, port)
        self.scrollbar_y = tk.Scrollbar(self.ports_frame, command=self.listbox.yview, orient=tk.VERTICAL)
        self.listbox.yscrollcommand = self.scrollbar_y.set
        self.scrollbar_x = tk.Scrollbar(self.ports_frame, command=self.listbox.xview, orient=tk.HORIZONTAL)
        self.listbox.xscrollcommand = self.scrollbar_x.set
        self.scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.pack(side=tk.LEFT)

        # for buttons
        self.connect_button = tk.Button(self.buttons_frame, text='Connect', command=self.onConnectClicked)
        self.connect_button.pack()

    def onConnectClicked(self):
        itemlist = self.listbox.curselection()
        if len(itemlist) == 1:
            self.result_list.append(self.comports[itemlist[0]])
            self.master.destroy()
        else:
            tk.messagebox.showerror("COM port error", "Select a COM port from list")

def main():
    root = tk.Tk()
    comport = []
    dialog = ComportDialog(master=root, result_list=comport)
    dialog.mainloop()
    if len(comport) == 1:
        with serial.Serial(comport[0].device, 256000) as ser:
            mca = pmca.PMCA(ser, echo=False)
            root = tk.Tk()
            app = Application(master=root, mca=mca)
            app.mainloop()
            app.cleanup()

if __name__ == "__main__":
    main()
