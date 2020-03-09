import pmca
import threading
import queue
import numpy as np
from matplotlib import pyplot as plt
plt.switch_backend('TkAgg')


def measure(mca, n):
    plt.ion()
    fig, ax = plt.subplots(1, 1)
    x = np.arange(0, pmca.PMCA.CHANNELS)
    y = np.zeros(pmca.PMCA.CHANNELS, dtype=int)
    lines, = ax.plot(x, y)

    mca.command('Y', 0)
    mca.command('S', n)

    for i in range(n):
        print(i)
        type, data = mca.wait_data()
        if type != mca.TYPE_HISTOGRAM:
            print('other data was received')
            break
        data = np.array(data) - 1
        y += data
        lines.set_data(x, y)
        ax.relim()
        ax.autoscale_view()
        plt.pause(0.1)
        pass

    mca.stop_measurement()
    pmca.save_histogram_by_date(y)

    return y


def _oscilloscope(mca, mode, n):
    plt.ion()
    fig, ax = plt.subplots(1, 1)
    x = np.arange(0, pmca.PMCA.CHANNELS)
    y = np.zeros(pmca.PMCA.CHANNELS, dtype=int)
    lines, = ax.plot(x, y)

    mca.command('Y', mode)
    mca.command('S', n)

    for i in range(n):
        print(i)
        type, data = mca.wait_data()
        if type != mca.TYPE_HISTOGRAM:
            print('other data was received')
            break
        print('baseline [ch] = ' + str(mca.command_until('B')))
        print('offset [ch] = ' + str(mca.command_until('D')))
        y = data
        lines.set_data(x, y)
        ax.relim()
        ax.autoscale_view()
        plt.pause(0.1)
        pass

    mca.stop_measurement()

    return y

def osc_freerun(mca, n):
    return _oscilloscope(mca, 1, n)


def osc_single(mca):
    return _oscilloscope(mca, 2, 1)
