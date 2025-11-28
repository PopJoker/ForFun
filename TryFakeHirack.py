from pymodbus.client.sync import ModbusTcpClient

# ESP32 IP 與 Modbus 端口
IP = '10.141.14.207'
PORT = 502
client = ModbusTcpClient(IP, port=PORT)
client.connect()

# --- 讀取 Rack (0x0000 ~ 0x000A) ---
rack_addr = 0x0000
rack_count = 11  # 共 11 個暫存器
rack_result = client.read_holding_registers(rack_addr, rack_count, slave_id=1)
if not rack_result.isError():
    r = rack_result.registers
    rack_data = {
        'Voltage_mV': (r[0] << 16) + r[1],
        'Current_0.01A': (r[2] << 16) + r[3],
        'SOC_0.1%': r[4],
        'MaxCellV_mV': r[5],
        'MinCellV_mV': r[6],
        'MaxCellT_0.1C': r[7],
        'MinCellT_0.1C': r[8],
        'Status': (r[9] << 16) + r[10]
    }
    print("Rack:", rack_data)
else:
    print("Rack 讀取錯誤")

# --- 讀取 10 個 Pack ---
CELL_COUNT = 22
PACK_COUNT = 10
PACK_REG_BASE = 100
PACK_REG_SIZE = 4 + CELL_COUNT + 9  # PackVoltage/Max/Min/Delta + 22 Cells + 9 Temps

packs = []

for i in range(PACK_COUNT):
    addr = PACK_REG_BASE + i * PACK_REG_SIZE
    result = client.read_holding_registers(addr, PACK_REG_SIZE, slave_id=1)
    if not result.isError():
        regs = result.registers
        pack = {
            'PackVoltage': regs[0],
            'MaxCellVoltage': regs[1],
            'MinCellVoltage': regs[2],
            'CellVoltageDelta': regs[3],
            'CellVoltage': regs[4:4+CELL_COUNT],
            'A1Temp': regs[4+CELL_COUNT],
            'A2Temp': regs[5+CELL_COUNT],
            'B1Temp': regs[6+CELL_COUNT],
            'B2Temp': regs[7+CELL_COUNT],
            'C1Temp': regs[8+CELL_COUNT],
            'C2Temp': regs[9+CELL_COUNT],
            'EnvTemp': regs[10+CELL_COUNT],
            'BPTemp': regs[11+CELL_COUNT],
            'BMTemp': regs[12+CELL_COUNT]
        }
        packs.append(pack)
    else:
        print(f"Pack {i+1} 讀取錯誤")

for idx, p in enumerate(packs):
    print(f"Pack {idx+1}:", p)

client.close()
