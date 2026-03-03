import modbus_tk.modbus_tcp as modbus_tcp
import modbus_tk.defines as cst
import time
import json
import threading

# ======== 設備參數 ========
DEVICES = [
    {"barcode": "Rack001", "ip": "192.168.1.103", "port": 502, "unit_id": 1, "enabled": True},
]

POLLING_INTERVAL = 5  # 秒
RACK_START_ADDR = 0
RACK_REG_COUNT = 22
PACK_START_ADDR_BASE = 100
PACK_REG_COUNT = 46
TOTAL_PACKS = 10
# ==========================

def format_rack_data(registers):
    def u16(addr): return registers[addr]
    def i16(addr): return registers[addr] if registers[addr] < 0x8000 else registers[addr]-0x10000
    def u32Swap(addr): return (u16(addr+1) << 16) | u16(addr)
    def i32Swap(addr): return (i16(addr+1) << 16) | u16(addr)
    
    rack = {
        "RackVoltage": u32Swap(0),
        "RackCurrent": i32Swap(2),
        "RackSOC": u16(4),
        "MaxCellVoltage": u16(5),
        "MinCellVoltage": u16(6),
        "MaxCellTemperature": i16(7),
        "MinCellTemperature": i16(8),
        "RackSoH": u16(9),
        "RackStatus": u32Swap(10),
        "RACK_P_Plus_Temp": i16(12),
        "RACK_P_Minus_Temp": i16(13),
        "RACK_B_Plus_Temp": i16(14),
        "RACK_B_Minus_Temp": i16(15),
        "RACK_R_Plus_Temp": i16(16),
        "RACK_R_Minus_Temp": i16(17),
        "RACK_PreRT_Temp": i16(18),
        "RACK_RT_Temp": i16(19),
        "PackActiveBalance": i16(20),
        "PackPassiveBalance": i16(21)
    }
    return rack

def format_pack_data(registers):
    def u16(addr): return registers[addr]
    def i16(addr): return registers[addr] if registers[addr] < 0x8000 else registers[addr]-0x10000
    def u32Swap(addr): return (u16(addr+1) << 16) | u16(addr)

    pack = {
        "PackVoltage": u16(0),
        "MaxCellVoltage": u16(1),
        "MinCellVoltage": u16(2),
        "CellVoltageDelta": u16(3)
    }
    for i in range(24):
        pack[f"CellVoltage{i+1}"] = u16(4+i)
    pack.update({
        "LowCellTemp1": i16(28),
        "LowCellTemp2": i16(29),
        "LowCellTemp3": i16(30),
        "HiCellTemp5": i16(31),
        "HiCellTemp6": i16(32),
        "HiCellTemp7": i16(33),
        "EnvironmentTemp": i16(34),
        "BPlusTemp": i16(35),
        "BMinusTemp": i16(36),
        "Cell4Temp": i16(37),
        "FuseTemp": i16(38),
        "BoardTypeID": u16(40),
        "PassiveBalanceStatus": u16(41),
        "CellBalanceStatus": u32Swap(42),
        "MaxCellTemp": i16(44),
        "MinCellTemp": i16(45)
    })
    return pack

def poll_device(device):
    if not device.get("enabled"): return
    try:
        master = modbus_tcp.TcpMaster(host=device["ip"], port=device["port"])
        master.set_timeout(5.0)

        # --- Rack ---
        rack_regs = master.execute(device["unit_id"], cst.READ_HOLDING_REGISTERS, RACK_START_ADDR, RACK_REG_COUNT)
        rack_data = format_rack_data(rack_regs)
        print(f"[{device['barcode']}] Rack Data:")
        print(json.dumps(rack_data, indent=2))

        time.sleep(0.05)

        # --- Pack ---
        packs_data = {}
        for i in range(1, TOTAL_PACKS+1):
            start_addr = i * PACK_START_ADDR_BASE - 1
            try:
                pack_regs = master.execute(device["unit_id"], cst.READ_HOLDING_REGISTERS, start_addr, PACK_REG_COUNT)
                packs_data[f"ID{i}"] = format_pack_data(pack_regs)
            except Exception as e:
                packs_data[f"ID{i}"] = {"error": str(e)}
            time.sleep(0.05)
        print(f"[{device['barcode']}] Packs Data:")
        print(json.dumps(packs_data, indent=2))

    except Exception as e:
        print(f"[{device['barcode']}] Poll Error:", e)

def main_loop():
    while True:
        threads = []
        for dev in DEVICES:
            t = threading.Thread(target=poll_device, args=(dev,))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        time.sleep(POLLING_INTERVAL)

if __name__ == "__main__":
    print("=== Modbus Python Polling Service ===")
    main_loop()