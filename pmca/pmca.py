import serial
import struct


class PMCA:
    UART_DELIMITER_RX = b'\x00\x00\x00\x00' # 4bytes NULL
    UART_DELIMITER_TX = b'\x0D' # CR

    CHANNELS = 4096
    DATA_BYTE = 2
    BYTES_OF_HISTOGRAM = CHANNELS * DATA_BYTE

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

    def _result_of(self, ret):
        ret = ret[:-len(self.UART_DELIMITER_RX)-1]
        return ret[-len(self.COMMAND_ERROR):]

    def _data_of(self, ret):
        return ret[:-len(self.UART_DELIMITER_RX)-len(self.COMMAND_ERROR)-1]

    def write(self, cmd):
        cmd += self.UART_DELIMITER_TX.decode()
        if self.echo:
            print(cmd)
            pass
        self.ser.write(cmd.encode('UTF-8'))
        pass

    def read(self, until=UART_DELIMITER_RX):
        ret = self.ser.read_until(until)
        return self._result_of(ret), self._data_of(ret)

    def _read_data(self, until=UART_DELIMITER_RX):
        #while True:
        #    print(self.ser.read())
        res, data = self.read(until)
        if res != self.COMMAND_HANDLED:
            raise CommandError(data)
        return data

    def command(self, cmd, param=None):
        if param is not None:
            if isinstance(param, int):
                param = format(param, '04X')
                pass
            cmd += param
            pass
        self.write(cmd)
        return self._read_data()

    def bin2array(self, bin):
        return struct.unpack('<'+str(self.CHANNELS)+'H', bin)

    def wait_histogram(self):
        data = self._read_data()
        return self.bin2array(data)

    def startup(self):
        return self.command('H')

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
