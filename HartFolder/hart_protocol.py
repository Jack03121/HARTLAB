import struct


class HartProtocol:
    def __init__(self):
        self.requested_preambles = 5
        self.long_address = None

    def calculate_checksum(self, data):
        checksum = 0
        for byte in data:
            checksum ^= byte
        return checksum

    def verify_checksum(self, response):
        if len(response) < 2:
            return False

        received_checksum = response[-1]
        calculated_checksum = 0

        start_index = 0
        while start_index < len(response) and response[start_index] == 0xFF:
            start_index += 1

        for byte in response[start_index:-1]:
            calculated_checksum ^= byte

        return received_checksum == calculated_checksum

    def bytes_to_float(self, b):
        return struct.unpack(">f", b)[0]

    def make_frame(self, body):
        checksum = self.calculate_checksum(body)
        return bytes(([0xFF] * self.requested_preambles) + body + [checksum])

    def build_short_command(self, command):
        return self.make_frame([0x02, 0x80, command, 0x00])

    def build_long_command(self, command, address):
        return self.make_frame([0x82] + address + [command, 0x00])

    def parse_device_info_response(self, response):
        if not self.verify_checksum(response):
            raise ValueError("Invalid checksum")

        i = 0
        while response[i] == 0xFF:
            i += 1

        data_section = response[i + 4:-1]
        device_data = data_section[2:]

        expanded_device_type_lo = device_data[1]
        request_preambles = device_data[2]

        uid1 = device_data[9]
        uid2 = device_data[10]
        uid3 = device_data[11]

        self.requested_preambles = max(5, request_preambles)

        long_addr_byte1 = (expanded_device_type_lo & 0x3F) | 0x80
        self.long_address = [long_addr_byte1, request_preambles, uid1, uid2, uid3]

        return {
            "unique_id": ''.join(f'{b:02X}' for b in [uid1, uid2, uid3]),
            "long_address": self.long_address,
        }

    def parse_command3_response(self, response):
        if not self.verify_checksum(response):
            return None

        i = 0
        while response[i] == 0xFF:
            i += 1

        addr_len = 5
        data_start = i + 1 + addr_len + 2
        data = response[data_start:-1]

        if len(data) < 11:
            return None

        current = self.bytes_to_float(bytes(data[2:6]))
        unit_code = data[6]
        pv_value = self.bytes_to_float(bytes(data[7:11]))

        return {
            "current": current,
            "pv_value": pv_value,
            "unit_code": unit_code
        }
