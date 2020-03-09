import serial
import struct
import time, datetime


class PMCA:
    STX = b'\x02'
    ETX = b'\x03'
    UART_DELIMITER = b'\x0D' # CR
    UART_NEWLINE = b'\0A' # LF

    CHANNELS = 4096
    DATA_BYTE = 2

    TYPE_HISTOGRAM = b'\x00'
    TYPE_HARDWARE_INFO = b'\x01'
    TYPE_HV_MONITOR = b'\x02'

    COMMAND_ERROR = b'NG'
    COMMAND_HANDLED = b'OK'

    def __init__(self, ser, echo=False):
        self.ser = ser
        self.echo = echo
        pass

    def read_all(self):
        if self.ser.in_waiting:
            return self.ser.read(size=self.ser.in_waiting)
        return ""

    def _read_result(self, until=UART_DELIMITER):
        return self.ser.read_until(until)

    @staticmethod
    def _result_of(ret):
        return ret[-3:-1]

    def command(self, cmd, param):
        if isinstance(param, int):
            param = format(param, '04X')
            pass
        cmd = cmd + param + self.UART_DELIMITER.decode()
        if self.echo:
            print(cmd)
            pass
        self.ser.write(cmd.encode('UTF-8'))
        ret = self._read_result()
        if self._result_of(ret) != self.COMMAND_HANDLED:
            raise CommandError(ret)
        pass

    @staticmethod
    def _data_of(ret):
        return ret[:-3]

    def command_until(self, cmd, until=UART_DELIMITER):
        cmd =  cmd+ self.UART_DELIMITER.decode()
        if self.echo:
            print(cmd)
            pass
        self.ser.write(cmd.encode('UTF-8'))
        ret = self._read_result(until)
        if self._result_of(ret) != self.COMMAND_HANDLED:
            raise CommandError(ret)
        return self._data_of(ret)

    def _read_data(self):
        # waite STX
        while True:
            c = self.ser.read(1)
            #print(c)
            if c == self.STX:
                break
        # read type
        type = self.ser.read(1)
        #print('type = ' + str(type))
        # read data block
        data = self.ser.read(self.CHANNELS * self.DATA_BYTE)
        #print(len(data), data)
        # clear other data
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

        return type, data

    def wait_data(self):
        type, bytes = self._read_data()
        return type, struct.unpack('<'+str(self.CHANNELS)+'H', bytes)  # type, data

    def startup(self):
        return self.command_until('H')

    def stop_measurement(self):
        ret = self.command('E', 0)
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        return ret

    def set_lld(self, value):
        self.command('L', value)
        pass

    def set_uld(self, value):
        self.command('L', value + 0x4000)
        pass

    def set_time_lld(self, value):
        self.command('L', value + 0x8000)
        pass

    def set_time_uld(self, value):
        self.command('L', value + 0xC000)
        pass

    pass


class CommandError(Exception):
    """制御コマンドの返答がNGの時を表すエラー"""
    pass


def save_histogram_by_date(histogram):
    filename = datetime.datetime.fromtimestamp(time.time()).strftime('%Y%m%d%H%M%S.csv')
    with open(filename, 'w') as f:
        i = 0
        for y in histogram:
            f.write('%d, %d\n' % (i, y))
            i += 1
            pass
        pass
    pass
