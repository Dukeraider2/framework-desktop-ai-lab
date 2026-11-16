#!/usr/bin/env python3
"""Read GGUF v3 header/tensor metadata and summarize tensor types. Never loads weights."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

# GGUF metadata type sizes from the format specification.
SCALARS = {0:1, 1:1, 2:2, 3:2, 4:4, 5:4, 6:4, 7:1, 10:8, 11:8, 12:8}
# Known GGML quantization numeric IDs; this table is advisory and can evolve.
TYPES = {0:'F32',1:'F16',2:'Q4_0',3:'Q4_1',6:'Q5_0',7:'Q5_1',8:'Q8_0',9:'Q8_1',10:'Q2_K',11:'Q3_K',12:'Q4_K',13:'Q5_K',14:'Q6_K',15:'Q8_K',16:'IQ2_XXS',17:'IQ2_XS',18:'IQ3_XXS',19:'IQ1_S',20:'IQ4_NL',21:'IQ3_S',22:'IQ2_S',23:'IQ4_XS',24:'I8',25:'I16',26:'I32',27:'I64',28:'F64',29:'IQ1_M',30:'BF16'}
MAX_COUNT = 5_000_000
MAX_KEY = 50_000


class GGUFError(ValueError):
    pass


class Parser:
    def __init__(self, path: Path):
        self.path = path
        self.stream = path.open('rb')
        self.size = path.stat().st_size

    def close(self):
        self.stream.close()

    def read(self, n: int) -> bytes:
        if n < 0 or n > self.size - self.stream.tell():
            raise GGUFError('unexpected EOF or malformed GGUF length')
        data = self.stream.read(n)
        if len(data) != n:
            raise GGUFError('truncated file')
        return data

    def u32(self):
        return struct.unpack('<I', self.read(4))[0]

    def u64(self):
        return struct.unpack('<Q', self.read(8))[0]

    def string(self):
        n = self.u64()
        if n > MAX_KEY:
            raise GGUFError('key / tensor string too large')
        return self.read(n).decode('utf-8', errors='replace')

    def skip(self, n):
        if n < 0 or n > self.size - self.stream.tell():
            raise GGUFError('invalid metadata length')
        self.stream.seek(n, 1)

    def skip_value(self, kind: int):
        if kind in SCALARS:
            self.skip(SCALARS[kind])
        elif kind == 8:
            self.skip(self.u64())
        elif kind == 9:
            element = self.u32()
            count = self.u64()
            if count > MAX_COUNT:
                raise GGUFError('array too large')
            if element in SCALARS:
                self.skip(count * SCALARS[element])
            elif element == 8:
                for _ in range(count):
                    self.skip(self.u64())
            else:
                raise GGUFError(f'unsupported nested array type {element}')
        else:
            raise GGUFError(f'unknown GGUF metadata type {kind}')

    def parse(self):
        if self.read(4) != b'GGUF':
            raise GGUFError('missing GGUF header')
        version = self.u32()
        if version != 3:
            raise GGUFError(f'only GGUF version 3 supported in this prototype (got {version})')
        tensor_count = self.u64()
        metadata_count = self.u64()
        if max(tensor_count, metadata_count) > MAX_COUNT:
            raise GGUFError('declared item count too large')
        for _ in range(metadata_count):
            self.string()
            self.skip_value(self.u32())
        counter = Counter()
        expert_counter = Counter()
        for _ in range(tensor_count):
            name = self.string()
            dims = self.u32()
            if dims > 8:
                raise GGUFError('unreasonable tensor dimensionality')
            self.skip(8 * dims)
            qtype = self.u32()
            self.skip(8)  # offset in data segment
            label = TYPES.get(qtype, f'UNKNOWN_{qtype}')
            counter[label] += 1
            if 'expert' in name or 'exp' in name or 'ffn' in name:
                expert_counter[label] += 1
        return {'file': self.path.name, 'gguf_version': version, 'tensor_count': tensor_count,
                'metadata_count': metadata_count, 'size_bytes': self.size,
                'tensor_types': dict(counter.most_common()),
                'potential_expert_tensor_types': dict(expert_counter.most_common()),
                'note': 'Counts are tensor counts, not weight-byte proportions; expert-name heuristic is model-specific.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('gguf', type=Path)
    args = p.parse_args()
    parser = Parser(args.gguf)
    try:
        print(json.dumps(parser.parse(), indent=2))
    finally:
        parser.close()


if __name__ == '__main__':
    main()
