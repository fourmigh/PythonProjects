
using System;
using System.Buffers.Binary;
using System.IO;
using System.Text;

namespace MxdLib
{

	internal sealed class TeanDecoder : MemoryStream
    {
        public TeanDecoder(Stream InStream, byte[] KeyCode, int Length = 0)
        {
            Buffer.BlockCopy(KeyCode, 0, m_Key, 0, 16);
            DecryptStream(InStream, Length);
        }

        public TeanDecoder(Stream InStream, string KeyCode, int Length = 0) : this(InStream, Encoding.ASCII.GetBytes(KeyCode), Length) { }

        public TeanDecoder(byte[] InData, byte[] KeyCode, int Length = 0) : this(new MemoryStream(InData), KeyCode, Length) { }

        public TeanDecoder(byte[] InData, string KeyCode, int Length = 0) : this(new MemoryStream(InData), KeyCode, Length) { }

        private MemoryStream DecryptStream(Stream Source, int length)
        {
            using BinaryReader BinSourceReader = new(Source);
            using BinaryWriter BinDestWriter = new(this, Encoding.Default, true);

            int Count = (length == 0) ? (int)Source.Length : length;

            byte[] buf = new byte[8];
            while (Count > 0)
            {
                int nToRead = Math.Min(Count, 8);

                int bytesRead = BinSourceReader.Read(buf, 0, nToRead);
                if (bytesRead == 0)
                    break;
                Count -= bytesRead;

                // pad end of buffer if needed, e.g. last block
                while (bytesRead < 8)
                    buf[bytesRead++] = 0x20;

                BinDestWriter.Write(Decipher(buf), 0, 8);
            }

            Seek(0, SeekOrigin.Begin);
            return this;
        }

        private byte[] Decipher(byte[] Data)
        {
            uint y = BinaryPrimitives.ReadUInt32LittleEndian(Data);
            uint z = BinaryPrimitives.ReadUInt32LittleEndian(Data.AsSpan(4));

            uint delta = 0x9E3779B9;
            uint n = 32;
            uint sum = delta * n;
            while (sum != 0)
            {
                z -= ((y << 4) ^ (y >> 5)) + (y ^ sum) + m_Key[sum >> 11 & 3];
                sum -= delta;
                y -= ((z << 4) ^ (z >> 5)) + (z ^ sum) + m_Key[sum & 3];
            }

            byte[] Result = new byte[8];
            BinaryPrimitives.WriteUInt32LittleEndian(Result, y);
            BinaryPrimitives.WriteUInt32LittleEndian(Result.AsSpan(4), z);

            return Result;
        }

        private readonly uint[] m_Key = new uint[4];
    }

    internal sealed class TeanEncoder : MemoryStream
    {
        public TeanEncoder(Stream InStream, byte[] KeyCode, int Length = 0)
        {
            Buffer.BlockCopy(KeyCode, 0, m_Key, 0, 16);
            EncryptStream(InStream, Length);
        }

        public TeanEncoder(Stream InStream, string KeyCode, int Length = 0) : this(InStream, Encoding.ASCII.GetBytes(KeyCode), Length) { }

        public TeanEncoder(byte[] InData, byte[] KeyCode, int Length = 0) : this(new MemoryStream(InData), KeyCode, Length) { }

        public TeanEncoder(byte[] InData, string KeyCode, int Length = 0) : this(new MemoryStream(InData), KeyCode, Length) { }

        private MemoryStream EncryptStream(Stream Source, int length)
        {
            using BinaryReader BinSourceReader = new(Source);
            using BinaryWriter BinDestWriter = new(this, Encoding.Default, true);

            int Count = (length == 0) ? (int)Source.Length : length;

            byte[] buf = new byte[8];
            while (Count > 0)
            {
                int nToRead = Math.Min(Count, 8);

                int bytesRead = BinSourceReader.Read(buf, 0, nToRead);
                if (bytesRead == 0)
                    break;
                Count -= bytesRead;

                // pad end of buffer if needed, e.g. last block
                while (bytesRead < 8)
                    buf[bytesRead++] = 0x20;

                BinDestWriter.Write(Encipher(buf), 0, 8);
            }

            Seek(0, SeekOrigin.Begin);
            return this;
        }
        
        private byte[] Encipher(byte[] Data)
        {
            uint y = BinaryPrimitives.ReadUInt32LittleEndian(Data);
            uint z = BinaryPrimitives.ReadUInt32LittleEndian(Data.AsSpan(4));

            uint delta = 0x9E3779B9;
            uint n = 32;
            uint sum = 0;
            while (sum != (delta * n))
            {
                y += ((z << 4) ^ (z >> 5)) + (z ^ sum) + m_Key[sum & 3];
                sum += delta;
                z += ((y << 4) ^ (y >> 5)) + (y ^ sum) + m_Key[sum >> 11 & 3];
            }

            byte[] Result = new byte[8];
            BinaryPrimitives.WriteUInt32LittleEndian(Result, y);
            BinaryPrimitives.WriteUInt32LittleEndian(Result.AsSpan(4), z);

            return Result;
        }

        private readonly uint[] m_Key = new uint[4];
    }
}
