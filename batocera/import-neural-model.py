#!/usr/bin/env python3
"""Extract only the verified 310.8.0 weights; never load or execute the NVIDIA DLL.

Mirrors src/video_core/neural_rendering/model.cpp. NVIDIA's newer Remix DLL also
contains the supported WEIGHTS_HT resource alongside an unrelated smaller model.
"""
from pathlib import Path
import hashlib
import json
import os
import struct
import sys

RESOURCE_SHA = '836f445d06ecd2e59bb9f17b84b91c143396fd76ccda1c9dc7fe81d5edd548f4'
PACKED_SHA = '37a293b5b781b9351a8b4b5fbeb2ff68fbd8a84891378950812ff3b99d161116'
TABLE_SHA = 'a2944b94ebdcfae9269a64e8a27d9f0ef373446c8f59bd64bf95d376b86c9319'
DLL_SHA = '2bc19bc09a7b89dd44f73e2ac0108fcc586e2154bdd0830f242f4f040e28789f'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def extract(dll):
    if digest(dll) != DLL_SHA:
        raise ValueError('Expected the verified NVIDIA RTX Remix 1.6.1 neural DLL')
    u16 = lambda data, off: struct.unpack_from('<H', data, off)[0]
    u32 = lambda data, off: struct.unpack_from('<I', data, off)[0]
    pe = u32(dll, 0x3c)
    assert dll[:2] == b'MZ' and dll[pe:pe+4] == b'PE\0\0'
    assert u16(dll, pe+4) == 0x8664
    optional = pe+24
    table = optional+u16(dll, pe+20)

    def rva(addr, size):
        for i in range(u16(dll, pe+6)):
            vaddr, rawsize, raw = struct.unpack_from('<III', dll, table+40*i+12)
            if addr >= vaddr and addr-vaddr+size <= rawsize:
                result = dll[raw+addr-vaddr:raw+addr-vaddr+size]
                assert len(result) == size
                return result
        raise ValueError('Resource RVA is outside the file')

    resource = rva(u32(dll, optional+128), u32(dll, optional+132))

    def entries(off):
        named, ids = struct.unpack_from('<HH', resource, off+12)
        return [struct.unpack_from('<II', resource, off+16+8*i)
                for i in range(named+ids)]

    models = []
    for typ, sub in entries(0):
        if typ != 10:
            continue
        for name, target in entries(sub & 0x7fffffff):
            if not name & 0x80000000:
                continue
            off = name & 0x7fffffff
            n = u16(resource, off)
            text = resource[off+2:off+2+2*n].decode('utf-16le')
            if text == 'WEIGHTS_HT':
                for _, dataoff in entries(target & 0x7fffffff):
                    models.append(rva(*struct.unpack_from('<II', resource, dataoff)))
    if len(models) != 1 or digest(models[0]) != RESOURCE_SHA:
        raise ValueError('The DLL does not contain the supported neural model')
    data = models[0]
    u64 = lambda data, off: struct.unpack_from('<Q', data, off)[0]
    assert u64(data, 0) == len(data)
    offset, tensors = 8, {}
    while offset < len(data):
        name_size = u64(data, offset)
        offset += 8
        name = data[offset:offset+name_size].decode('ascii')
        offset += name_size
        size = u64(data, offset)
        offset += 8
        record = data[offset:offset+size]
        offset += size
        assert u64(record, 0) == size and u32(record, 16) == 1
        payload_size = u64(record, 8)
        payload = record[20:20+payload_size]
        assert len(payload) == payload_size and name not in tensors
        tensors[name] = payload
    assert offset == len(data) and len(tensors) == 153
    packed, entries_out = bytearray(), []
    for name, payload in sorted(tensors.items()):
        block, layer, parameter = name.split('.')
        entries_out.append(dict(name=name, block=int(block[5:]), layer=int(layer[5:]),
                                parameter=parameter, stage='packed',
                                stageOffset=len(packed), byteLength=len(payload)))
        packed.extend(payload)
    table_json = json.dumps(entries_out, sort_keys=True, separators=(',', ':')).encode()
    if len(packed) != 147683778 or digest(packed) != PACKED_SHA or digest(table_json) != TABLE_SHA:
        raise ValueError('Extracted model/table differs from the native importer')
    manifest = dict(totals=dict(blockCount=71, tensorCount=153),
                    stages=[dict(id='packed', file='packed.bin',
                                 packedByteLength=len(packed), sha256=PACKED_SHA.upper())],
                    tensors=entries_out,
                    provenance=dict(model_version='310.8.0', resource_sha256=RESOURCE_SHA,
                                    source_sha256=DLL_SHA,
                                    source='NVIDIAGameWorks/rtx-remix remix-1.6.1'))
    return packed, manifest


def main():
    dll, destination = map(Path, sys.argv[1:3])
    packed, manifest = extract(dll.read_bytes())
    if destination.exists():
        raise RuntimeError('Destination already exists; keep the installed model intact')
    staging = destination.with_name(destination.name+'.importing')
    staging.mkdir(parents=True)
    (staging/'model').mkdir()
    (staging/'model/packed.bin').write_bytes(packed)
    (staging/'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
    os.replace(staging, destination)
    print('Verified 310.8.0 weights installed:', destination, flush=True)


if __name__ == '__main__':
    main()
