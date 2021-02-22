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
from scipy.stats import norm
from scipy.optimize import curve_fit
import math

def measure(mca, n, plot=True, autosave=True):
    #plt.ion()
    fig, ax = plt.subplots(1, 1)
    x = np.arange(0, pmca.PMCA.CHANNELS)
    y = np.zeros(pmca.PMCA.CHANNELS, dtype=int)
    lines, = ax.plot(x, y)

    mca.command('Y', 0)
    mca.command('S', n)

    for i in range(n):
        #print(i)
        data = mca.wait_histogram()
        data = np.array(data) - 1
        print('count rate: ' + str(data.sum()) + ' [cps]')
        y += data
        if plot:
            lines.set_data(x, y)
            ax.relim()
            ax.autoscale_view()
            plt.pause(0.1)
        pass

    mca.stop_measurement()
    if autosave:
        save_histogram_by_date(y)
    if plot:
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


def fitting(hist):
    # Define model function to be used to fit to the data above:
    def gauss(x, *p):
        A, mu, sigma = p
        return A*np.exp(-(x-mu)**2/(2.*sigma**2))

    # p0 is the initial guess for the fitting coefficients (A, mu and sigma above)
    #print(max(hist), hist==max(hist))
    binMax = hist.argmax()
    p0 = [1., binMax, 1.]
    #print(p0)

    #
    xaxis = [i for i in range(len(hist))]
    xaxis10 = [i/10. for i in range(len(hist)*10)]
    #print xaxis

    coeff, var_matrix = curve_fit(gauss, xaxis, hist, p0=p0)
    #print coeff
    #coeff = np.array([0.007, 231.6, 1.2])

    # Get the fitted curve
    hist_fit = gauss(xaxis, *coeff)
    hist_fit10 = gauss(xaxis10, *coeff)
    #print len(hist_fit), hist_fit

    #plt.plot(xaxis, hist, label='Test data')
    #plt.plot(xaxis, hist_fit, label='Fitted data')
    #plt.plot(xaxis10, hist_fit10, label='Fitted data')
    #plt.show()

    # Finally, lets get the fitting parameters, i.e. the mean and standard deviation:
    #print('Fitted coeff =', coeff[0])
    mean = coeff[1]
    #print('Fitted mean = ', mean)
    stdev = coeff[2]
    #print('Fitted standard deviation = ', stdev)
    fwhw = stdev * 2 * math.sqrt(2*math.log(2))
    #print('Fitted FWHM = ', fwhw)

    return mean, stdev, fwhw


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

    hists = []
    with serial.Serial(port.device, 256000) as ser:
        try:
            mca = pmca.PMCA(ser, echo=False)
            print(mca.read_all())
            mca.stop_measurement()
            print(mca.startup())

            mca.set_lld(20) # 20 for x16
            for gain in range(2, 16+1):
                print('gain=', gain)
                mca.command('G', gain)
                print(datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
                histogram = measure(mca, 1, plot=False, autosave=False)
                hists.append(histogram)
        except pmca.CommandError as e:
            print(e)

        pass
    
    results = []
    graph = np.zeros(pmca.PMCA.CHANNELS, dtype=int)
    for hist in hists:
        mean, stdev, fwhm = fitting(hist)
        results.append((hist.sum(), fwhm, mean, stdev))
        graph += hist

    filename = datetime.now().strftime('%Y%m%d%H%M%S.png')
    plt.plot(graph)
    plt.savefig(filename)

    filename = datetime.now().strftime('%Y%m%d%H%M%S_graph.csv')
    with open(filename, 'w') as f:
        for y in graph:
            f.write('%d\n' % y)
        pass

    filename = datetime.now().strftime('%Y%m%d%H%M%S_result.csv')
    with open(filename, 'w') as f:
        gain = 2
        f.write('gain, cps, fwhm [ch], mean [ch], stdev [ch]\n')
        for result in results:
            f.write('%d, %f, %f, %f, %f\n' % (gain, result[0], result[1], result[2], result[3]))
            gain += 1
            pass
        pass


if __name__ == '__main__':
    main()