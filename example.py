import serial
import serial.tools.list_ports
import pickle

import pmca
import threading
import queue
import numpy as np
import time
from datetime import datetime
from matplotlib import pyplot as plt
plt.switch_backend('TkAgg')

def measure(mca, n):
    #plt.ion()
    fig, ax = plt.subplots(1, 1)
    x = np.arange(0, pmca.PMCA.CHANNELS)
    y = np.zeros(pmca.PMCA.CHANNELS, dtype=int)
    lines, = ax.plot(x, y)

    mca.command('Y', 0)
    mca.command('S', n)

    for i in range(n):
        print(i)
        data = mca.wait_histogram()
        data = np.array(data) - 1
        print('count rate: ' + str(data.sum()) + ' [cps]')
        y += data
        lines.set_data(x, y)
        ax.relim()
        ax.autoscale_view()
        plt.pause(0.1)
        pass

    mca.stop_measurement()
    save_histogram_by_date(y)
    plt.show()

    return y


def _oscilloscope(mca, mode, n):
    #plt.ion()
    fig, ax = plt.subplots(1, 1)
    x = np.arange(0, pmca.PMCA.CHANNELS)
    y = np.zeros(pmca.PMCA.CHANNELS, dtype=int)
    lines, = ax.plot(x, y)

    mca.command('Y', mode)
    mca.command('S', n)

    statistics = []
    for i in range(n):
        print(i)
        data = mca.wait_histogram()
        data = np.array(data) - 1
        statistics = np.concatenate([statistics, data])
        print('baseline [ch] = ' + str(mca.command('B')))
        print('offset [ch] = ' + str(mca.command('D')))
        print('rms [ch] = ' + str(statistics.std()))
        print(len(statistics))
        y = data
        lines.set_data(x, y)
        ax.relim()
        ax.autoscale_view()
        plt.pause(0.1)
        pass

    mca.stop_measurement()
    plt.show()

    return y

def osc_freerun(mca, n):
    return _oscilloscope(mca, 1, n)


def osc_single(mca):
    return _oscilloscope(mca, 2, 1)


def save_histogram_by_date(histogram):
    filename = datetime.now().strftime('%Y%m%d%H%M%S.csv')
    with open(filename, 'w') as f:
        i = 0
        for y in histogram:
            f.write('%d, %d\n' % (i, y))
            i += 1
            pass
        pass
    pass

def main():
    comports = serial.tools.list_ports.comports()
    i = 0
    for i, port in enumerate(comports):
        print("%d: %s" % (i, port))
        pass

    i = input("enter port index: ")
    port = None
    try:
        port = comports[int(i)]
        pass
    except ValueError:
        print("invalid input")
        exit()

    with serial.Serial(port.device, 256000) as ser:
        try:
            mca = pmca.PMCA(ser, echo=False)
            print(mca.read_all())
            mca.stop_measurement()
            print(mca.startup())

            mca.set_lld(250)
            mca.command('X', 3)
            mca.command('G', 2)
            mca.command('I', 0)
            mca.command('F', 3)
            print(datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
            #osc_freerun(mca, 3)
            #osc_single(mca)
            histogram = measure(mca, 3)
        except pmca.CommandError as e:
            print(e)

        pass

if __name__ == '__main__':
    main()