import serial
import struct
import time, datetime


class PMCA:
    UART_DELIMITER_RX = b'\x00\x00\x00\x00' # 4bytes NULL
    UART_DELIMITER_TX = b'\x0D' # CR

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

    def _read_result(self, until=UART_DELIMITER_RX):
        #while True:
        #    print(self.ser.read())
        ret = self.ser.read_until(until)
        data = self._data_of(ret)
        if self._result_of(ret) != self.COMMAND_HANDLED:
            raise CommandError(data)
        return data

    @staticmethod
    def _result_of(ret):
        return ret[-7:-5]

    def command(self, cmd, param):
        if isinstance(param, int):
            param = format(param, '04X')
            pass
        cmd = cmd + param + self.UART_DELIMITER_TX.decode()
        if self.echo:
            print(cmd)
            pass
        self.ser.write(cmd.encode('UTF-8'))
        self._read_result()
        pass

    @staticmethod
    def _data_of(ret):
        return ret[:-7]

    def command_until(self, cmd, until=UART_DELIMITER_RX):
        cmd = cmd + self.UART_DELIMITER_TX.decode()
        if self.echo:
            print(cmd)
            pass
        self.ser.write(cmd.encode('UTF-8'))
        return self._read_result(until)

    def wait_histogram(self):
        data = self._read_result()
        return struct.unpack('<'+str(self.CHANNELS)+'H', data)

    def startup(self):
        return self.command_until('H')

    def stop_measurement(self):
        self.command('E', 0)
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        pass

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
