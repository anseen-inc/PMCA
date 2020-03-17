import serial
import serial.tools.list_ports
import pickle

import pmca
import pmca.util

from time import sleep
from datetime import datetime

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

            mca.set_lld(7)
            mca.command('X', 3)
            mca.command('G', 2)
            mca.command('M', 0)
            mca.command('I', 0)
            mca.command('F', 3)
            print(datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
            #pmca.util.osc_freerun(mca, 3)
            #pmca.util.osc_single(mca)
            histogram = pmca.util.measure(mca, 3)
        except pmca.CommandError as e:
            print(e)

        pass

if __name__ == '__main__':
    main()