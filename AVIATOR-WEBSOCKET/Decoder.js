const zlib = require('zlib');

class DataStream {
  constructor(buffer, byteOffset = 0) {
    this.buffer = buffer;
    this.byteOffset = byteOffset;
    this.position = 0;
    this.byteLength = buffer.length;
  }

  seek(position) {
    this.position = Math.max(0, Math.min(this.byteLength, position));
  }

  isEof() {
    return this.position >= this.byteLength;
  }

  readInt8() {
    const value = this.buffer.readInt8(this.byteOffset + this.position);
    this.position += 1;
    return value;
  }

  readUInt8() {
    const value = this.buffer.readUInt8(this.byteOffset + this.position);
    this.position += 1;
    return value;
  }

  readInt16() {
    const value = this.buffer.readInt16BE(this.byteOffset + this.position);
    this.position += 2;
    return value;
  }

  readUInt16() {
    const value = this.buffer.readUInt16BE(this.byteOffset + this.position);
    this.position += 2;
    return value;
  }

  readInt32() {
    const value = this.buffer.readInt32BE(this.byteOffset + this.position);
    this.position += 4;
    return value;
  }

  readInt64() {
    const value = this.buffer.readBigInt64BE(this.byteOffset + this.position);
    this.position += 8;
    return Number(value);
  }

  readFloat32() {
    const value = this.buffer.readFloatBE(this.byteOffset + this.position);
    this.position += 4;
    return value;
  }

  readFloat64() {
    const value = this.buffer.readDoubleBE(this.byteOffset + this.position);
    this.position += 8;
    return value;
  }

  readUtf8String(length) {
    const end = this.position + length;
    const stringBytes = this.buffer.slice(this.byteOffset + this.position, this.byteOffset + end);
    this.position = end;
    try {
      return stringBytes.toString('utf8');
    } catch (e) {
      console.error(`Error decoding UTF-8 string: ${e.message}`);
      return stringBytes.toString('hex');
    }
  }

  readByteArray(length) {
    const end = this.position + length;
    const byteArray = this.buffer.slice(this.byteOffset + this.position, this.byteOffset + end);
    this.position = end;
    return Array.from(byteArray);
  }
}

class DataStreamWriter {
  constructor() {
    this.buffers = [];
    this.length = 0;
  }

  writeInt8(value) {
    const buffer = Buffer.alloc(1);
    buffer.writeInt8(value, 0);
    this.buffers.push(buffer);
    this.length += 1;
  }

  writeUInt8(value) {
    const buffer = Buffer.alloc(1);
    buffer.writeUInt8(value, 0);
    this.buffers.push(buffer);
    this.length += 1;
  }

  writeInt16(value) {
    const buffer = Buffer.alloc(2);
    buffer.writeInt16BE(value, 0);
    this.buffers.push(buffer);
    this.length += 2;
  }

  writeUInt16(value) {
    const buffer = Buffer.alloc(2);
    buffer.writeUInt16BE(value, 0);
    this.buffers.push(buffer);
    this.length += 2;
  }

  writeInt32(value) {
    const buffer = Buffer.alloc(4);
    buffer.writeInt32BE(value, 0);
    this.buffers.push(buffer);
    this.length += 4;
  }

  writeInt64(value) {
    const buffer = Buffer.alloc(8);
    buffer.writeBigInt64BE(BigInt(value), 0);
    this.buffers.push(buffer);
    this.length += 8;
  }

  writeFloat32(value) {
    const buffer = Buffer.alloc(4);
    buffer.writeFloatBE(value, 0);
    this.buffers.push(buffer);
    this.length += 4;
  }

  writeFloat64(value) {
    const buffer = Buffer.alloc(8);
    buffer.writeDoubleBE(value, 0);
    this.buffers.push(buffer);
    this.length += 8;
  }

  writeUtf8String(value) {
    const stringBuffer = Buffer.from(value, 'utf8');
    this.writeUInt16(stringBuffer.length);
    this.buffers.push(stringBuffer);
    this.length += stringBuffer.length;
  }

  writeByteArray(array) {
    const buffer = Buffer.from(array);
    this.writeUInt16(buffer.length);
    this.buffers.push(buffer);
    this.length += buffer.length;
  }

  toBuffer() {
    return Buffer.concat(this.buffers, this.length);
  }
}

const SFS_DATA_TYPES = {
  NULL: 0x00,
  BOOL: 0x01,
  BYTE: 0x02,
  SHORT: 0x03,
  INT: 0x04,
  LONG: 0x05,
  FLOAT: 0x06,
  DOUBLE: 0x07,
  UTF_STRING: 0x08,
  BOOL_ARRAY: 0x09,
  BYTE_ARRAY: 0x0A,
  SHORT_ARRAY: 0x0B,
  INT_ARRAY: 0x0C,
  LONG_ARRAY: 0x0D,
  FLOAT_ARRAY: 0x0E,
  DOUBLE_ARRAY: 0x0F,
  UTF_STRING_ARRAY: 0x10,
  SFS_ARRAY: 0x11,
  SFS_OBJECT: 0x12,
};

function decodeSfsObject(ds) {
  const result = {};
  const numElements = ds.readUInt16();

  for (let i = 0; i < numElements; i++) {
    const keyLength = ds.readUInt16();
    const key = ds.readUtf8String(keyLength);
    const valueType = ds.readUInt8();
    const value = decodeValue(ds, valueType);
    result[key] = value;
  }
  return result;
}

function decodeSfsArray(ds) {
  const result = [];
  const numElements = ds.readUInt16();

  for (let i = 0; i < numElements; i++) {
    const valueType = ds.readUInt8();
    const value = decodeValue(ds, valueType);
    result.push(value);
  }
  return result;
}

function decodeValue(ds, valueType) {
  switch (valueType) {
    case SFS_DATA_TYPES.NULL: return null;
    case SFS_DATA_TYPES.BOOL: return !!ds.readUInt8();
    case SFS_DATA_TYPES.BYTE: return ds.readInt8();
    case SFS_DATA_TYPES.SHORT: return ds.readInt16();
    case SFS_DATA_TYPES.INT: return ds.readInt32();
    case SFS_DATA_TYPES.LONG: return ds.readInt64();
    case SFS_DATA_TYPES.FLOAT: return ds.readFloat32();
    case SFS_DATA_TYPES.DOUBLE: return ds.readFloat64();
    case SFS_DATA_TYPES.UTF_STRING: {
      const strLength = ds.readUInt16();
      return ds.readUtf8String(strLength);
    }
    case SFS_DATA_TYPES.BOOL_ARRAY: {
      const boolLength = ds.readUInt16();
      return Array.from({ length: boolLength }, () => !!ds.readUInt8());
    }
    case SFS_DATA_TYPES.BYTE_ARRAY: {
      const byteLength = ds.readUInt16();
      return ds.readByteArray(byteLength);
    }
    case SFS_DATA_TYPES.SHORT_ARRAY: {
      const shortLength = ds.readUInt16();
      return Array.from({ length: shortLength }, () => ds.readInt16());
    }
    case SFS_DATA_TYPES.INT_ARRAY: {
      const intLength = ds.readUInt16();
      return Array.from({ length: intLength }, () => ds.readInt32());
    }
    case SFS_DATA_TYPES.LONG_ARRAY: {
      const longLength = ds.readUInt16();
      return Array.from({ length: longLength }, () => ds.readInt64());
    }
    case SFS_DATA_TYPES.FLOAT_ARRAY: {
      const floatLength = ds.readUInt16();
      return Array.from({ length: floatLength }, () => ds.readFloat32());
    }
    case SFS_DATA_TYPES.DOUBLE_ARRAY: {
      const doubleLength = ds.readUInt16();
      return Array.from({ length: doubleLength }, () => ds.readFloat64());
    }
    case SFS_DATA_TYPES.UTF_STRING_ARRAY: {
      const stringLength = ds.readUInt16();
      return Array.from({ length: stringLength }, () => {
        const len = ds.readUInt16();
        return ds.readUtf8String(len);
      });
    }
    case SFS_DATA_TYPES.SFS_ARRAY: return decodeSfsArray(ds);
    case SFS_DATA_TYPES.SFS_OBJECT: return decodeSfsObject(ds);
    default: throw new Error(`Unsupported data type: 0x${valueType.toString(16)}`);
  }
}

function decodeMessage(binaryData) {
  const ds = new DataStream(binaryData);
  const header = ds.readUInt8();

  if ((header & 0x80) !== 0x80) {
    console.error('Invalid header. Expected binary message (bit 7 = 1).');
    return null;
  }

  const messageLength = ds.readUInt16();
  let bodyData = binaryData.slice(ds.position);
  let decompressedData = bodyData;

  if (bodyData.length > 1 && bodyData.readUInt8(0) === 0x78 && bodyData.readUInt8(1) === 0x9c) {
    try {
      decompressedData = zlib.inflateSync(bodyData);
    } catch (e) {
      console.error('Error decompressing data with zlib:', e.message);
      return null;
    }
  }

  const bodyDs = new DataStream(decompressedData);
  const dataType = bodyDs.readUInt8();

  try {
    let decoded;
    if (dataType === SFS_DATA_TYPES.SFS_OBJECT) {
      decoded = decodeSfsObject(bodyDs);
    } else if (dataType === SFS_DATA_TYPES.SFS_ARRAY) {
      decoded = decodeSfsArray(bodyDs);
    } else {
      console.error(`Unsupported root data type: 0x${dataType.toString(16)}`);
      return null;
    }
    console.log('[Decoder] Decoded message:', JSON.stringify(decoded, null, 2));
    return decoded;
  } catch (e) {
    console.error('Error decoding body:', e.message);
    return null;
  }
}

function encodeSfsObject(writer, obj) {
  const keys = Object.keys(obj);
  writer.writeUInt16(keys.length); // Número de elementos

  for (const key of keys) {
    const value = obj[key];
    writer.writeUtf8String(key); // Escribir clave
    encodeValue(writer, value); // Escribir valor
  }
}

function encodeSfsArray(writer, arr) {
  writer.writeUInt16(arr.length); // Número de elementos
  for (const value of arr) {
    encodeValue(writer, value);
  }
}

function encodeValue(writer, value) {
  if (value === null) {
    writer.writeUInt8(SFS_DATA_TYPES.NULL);
  } else if (typeof value === 'boolean') {
    writer.writeUInt8(SFS_DATA_TYPES.BOOL);
    writer.writeUInt8(value ? 1 : 0);
  } else if (Number.isInteger(value) && value >= -128 && value <= 127) {
    writer.writeUInt8(SFS_DATA_TYPES.BYTE);
    writer.writeInt8(value);
  } else if (Number.isInteger(value) && value >= -32768 && value <= 32767) {
    writer.writeUInt8(SFS_DATA_TYPES.SHORT);
    writer.writeInt16(value);
  } else if (Number.isInteger(value) && value >= -2147483648 && value <= 2147483647) {
    writer.writeUInt8(SFS_DATA_TYPES.INT);
    writer.writeInt32(value);
  } else if (Number.isInteger(value)) {
    writer.writeUInt8(SFS_DATA_TYPES.LONG);
    writer.writeInt64(value);
  } else if (typeof value === 'number') {
    writer.writeUInt8(SFS_DATA_TYPES.DOUBLE);
    writer.writeFloat64(value);
  } else if (typeof value === 'string') {
    writer.writeUInt8(SFS_DATA_TYPES.UTF_STRING);
    writer.writeUtf8String(value);
  } else if (Array.isArray(value)) {
    writer.writeUInt8(SFS_DATA_TYPES.SFS_ARRAY);
    encodeSfsArray(writer, value);
  } else if (typeof value === 'object') {
    writer.writeUInt8(SFS_DATA_TYPES.SFS_OBJECT);
    encodeSfsObject(writer, value);
  } else {
    throw new Error(`Unsupported value type: ${typeof value}`);
  }
}

function encodeMessage(obj) {
  const writer = new DataStreamWriter();

  // Escribir el cuerpo (sin comprimir por ahora)
  writer.writeUInt8(SFS_DATA_TYPES.SFS_OBJECT); // Tipo SFS_OBJECT
  encodeSfsObject(writer, obj);

  const body = writer.toBuffer();

  // Comprimir con zlib
  const compressedBody = zlib.deflateSync(body);

  // Construir el encabezado
  const headerWriter = new DataStreamWriter();
  headerWriter.writeUInt8(0x80); // Bit 7 = 1
  headerWriter.writeUInt16(compressedBody.length); // Longitud del cuerpo

  // Combinar encabezado y cuerpo comprimido
  return Buffer.concat([headerWriter.toBuffer(), compressedBody]);
}

module.exports = { decodeMessage, encodeMessage };